"""DynamicSpeed API and web app. Deploy with Docker; GitHub Pages cannot execute SUMO."""
from __future__ import annotations
import json
import os
import threading
import uuid
import time
import logging
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Literal
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse, JSONResponse
from pydantic import BaseModel, Field, field_validator, model_validator
from .simulation import POLICIES, WEATHER, execute_job, container_memory

ROOT=Path(__file__).resolve().parent.parent
HTML=ROOT/'index.html'
OUTPUT=Path(os.environ.get('DS_OUTPUT_DIR','/tmp/dynamicspeed_jobs'))
OUTPUT.mkdir(parents=True,exist_ok=True)
MAX_ACTIVE=int(os.environ.get('DS_MAX_QUEUED','3'))
MAX_HISTORY=int(os.environ.get('DS_MAX_HISTORY','12'))
MAX_REQUESTS_PER_HOUR=int(os.environ.get('DS_MAX_REQUESTS_PER_HOUR','3'))
executor=ThreadPoolExecutor(max_workers=1)
logger=logging.getLogger("dynamicspeed")
jobs:dict[str,dict]={}
requests:dict[str,list[float]]={}
lock=threading.Lock()
app=FastAPI(title='DynamicSpeed Live SUMO API',version='43.0')

class SimulationRequest(BaseModel):
    demand:int=Field(default=600,ge=400,le=1800,multiple_of=100)
    weather:Literal['dry','light_rain','heavy_rain']='dry'
    duration_minutes:Literal[10,15,30]=10
    seed:int=Field(default=314,ge=1,le=999999)
    policies:list[Literal['static','rule','mpc','weather_rule']]=Field(default_factory=lambda:['static','rule'])
    @model_validator(mode='after')
    def validate_policies(self):
        allowed=int(os.environ.get('DS_MAX_DURATION_MINUTES','15'))
        if self.duration_minutes>allowed:
            raise ValueError(f'Bu ücretsiz sunucuda en fazla {allowed} dakikalık deney destekleniyor. Daha uzun koşular için yüksek RAM gerekir.')
        if not 2<=len(self.policies)<=2 or len(self.policies)!=len(set(self.policies)):
            raise ValueError('2 veya 3 farklı kontrolcü seçilmelidir')
        return self

@app.get('/',response_class=HTMLResponse)
def index():
    return HTMLResponse(HTML.read_text(encoding='utf-8'),headers={'Cache-Control':'no-store'})

@app.get('/api/health')
def health():
    import shutil
    used, maximum = container_memory()
    return {
        'ok': True,
        'sumo': bool(shutil.which('sumo')),
        'netconvert': bool(shutil.which('netconvert')),
        'queued_or_running': sum(j['status'] in ('queued', 'running') for j in jobs.values()),
        'memory_used_mb': round(used / 1024**2) if used is not None else None,
        'memory_limit_mb': round(maximum / 1024**2) if maximum is not None else None,
        'max_duration_minutes': int(os.environ.get('DS_MAX_DURATION_MINUTES', '15')),
    }

def safe_job_id(job_id:str):
    try: return str(uuid.UUID(job_id))
    except (ValueError,AttributeError):raise HTTPException(404,'Job not found')

def ensure_job(job_id:str):
    job_id=safe_job_id(job_id)
    with lock:
        data=jobs.get(job_id)
        if not data:raise HTTPException(404,'Job not found')
        return data.copy()

def worker(job_id:str,params:dict):
    def progress(frac:float,msg:str):
        with lock:
            jobs[job_id].update({'status':'running','progress':round(frac*100,1),'message':msg})
    try:
        result=execute_job(OUTPUT/job_id,params,progress)
        result_path=OUTPUT/job_id/'result.json'
        result_path.write_text(json.dumps(result,ensure_ascii=False,separators=(',',':')),encoding='utf-8')
        with lock:jobs[job_id].update({'status':'completed','progress':100,'message':'Simülasyon tamamlandı'})
    except Exception as exc:
        logger.exception('Simulation failed, job=%s',job_id)
        with lock:jobs[job_id].update({'status':'error','message':str(exc)[:350]})

@app.post('/api/simulations',status_code=202)
def create_simulation(body:SimulationRequest,request:Request):
    import shutil
    if not shutil.which('sumo') or not shutil.which('netconvert'):
        raise HTTPException(503,'SUMO/netconvert kurulu değil. Docker sürümünü çalıştırın.')
    # Basic abuse protection, not a replacement for authentication or a managed API gateway.
    client=request.client.host if request.client else 'unknown'
    now=time.monotonic()
    with lock:
        recent=[t for t in requests.get(client,[]) if now-t<3600]
        if len(recent)>=MAX_REQUESTS_PER_HOUR:raise HTTPException(429,'Saatlik deneme sınırına ulaşıldı')
        pending=sum(j['status'] in ('queued','running') for j in jobs.values())
        if pending>=MAX_ACTIVE:raise HTTPException(503,'Sunucu yoğun. Daha sonra tekrar deneyin.')
        if len(jobs)>=MAX_HISTORY:
            # Prune old metadata; result files may be periodically purged by host.
            finished=[k for k,j in jobs.items() if j['status'] in ('completed','error')]
            for k in finished[:max(1,len(jobs)-MAX_HISTORY+1)]:jobs.pop(k,None)
        job_id=str(uuid.uuid4())
        jobs[job_id]={'id':job_id,'status':'queued','progress':0.,'message':'Kuyrukta','params':body.model_dump()}
        requests[client]=recent+[now]
    executor.submit(worker,job_id,body.model_dump())
    return {'id':job_id,'status':'queued'}

@app.get('/api/simulations/{job_id}')
def get_simulation(job_id:str):
    data=ensure_job(job_id)
    # Expose metadata only; large result downloaded separately.
    return data

@app.get('/api/simulations/{job_id}/result')
def get_result(job_id:str):
    data=ensure_job(job_id)
    if data['status']!='completed':raise HTTPException(409,'Simulation not complete')
    file=OUTPUT/safe_job_id(job_id)/'result.json'
    if not file.is_file():raise HTTPException(410,'Result expired')
    return JSONResponse(json.loads(file.read_text(encoding='utf-8')))

@app.get('/simulator',response_class=HTMLResponse)
def simulator():
    return HTMLResponse((ROOT/'simulator.html').read_text(encoding='utf-8'),headers={'Cache-Control':'no-store'})
