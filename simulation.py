"""DynamicSpeed custom SUMO runner.

Reference: DynamicSpeed_12_WeatherAware_Full.ipynb, cells 2–8.
Synthetic 6 km 3->1->3 corridor; e1/e2 controlled, e3 sensor.
Weather parameters are assumptions, NOT calibrated rain measurements.
"""
from __future__ import annotations
from pathlib import Path
import math
import os
import subprocess
import xml.etree.ElementTree as ET
import json
import gc
from typing import Callable

WEATHER = {
    'dry': {'tau': 1.1, 'decel': 4.5, 'accel': 2.6, 'speedFactor': 1.0, 'cap': 100, 'label': 'Kuru yol'},
    'light_rain': {'tau': 1.4, 'decel': 3.8, 'accel': 2.4, 'speedFactor': .95, 'cap': 90, 'label': 'Hafif yağmur'},
    'heavy_rain': {'tau': 1.8, 'decel': 3.0, 'accel': 2.2, 'speedFactor': .85, 'cap': 80, 'label': 'Şiddetli yağmur'},
}
POLICIES = ('static', 'rule', 'mpc', 'weather_rule')
LABELS = {'static':'Sabit 100', 'rule':'Rule-Based', 'mpc':'Original MPC', 'weather_rule':'Weather-Aware'}
BASE_SPEED = 100
CONTROL_EDGES = ('e1','e2')
SENSOR = 'e3'

def next_step(current: int, target: int) -> int:
    return int(max(current - 10, min(current + 10, target)))

def next_rule(current: int, observed: float) -> int:
    if not math.isfinite(observed):
        return current
    target = 70 if observed < 40 else (80 if observed < 65 else 100)
    return next_step(current, target)

def next_weather_rule(current: int, observed: float, weather: str) -> int:
    if not math.isfinite(observed):
        target = WEATHER[weather]['cap']
    else:
        target = 70 if observed < 40 else (80 if observed < 65 else 100)
        target = min(target, WEATHER[weather]['cap'])
    return next_step(current, target)

def predict_rollout(obs: dict, current: int, target: int, horizon: int=5):
    """Identical simplified, uncalibrated two-reservoir MPC to DS12 notebook."""
    up=max(0.,obs['n_up']); down=max(0.,obs['n_down'])
    arrival=max(0.,min(95.,obs['arrival_per_min']))
    observed_v=obs['downstream_speed_kmh']
    v_down=max(10.,min(100.,observed_v if math.isfinite(observed_v) else 60.))
    curr=int(current); cost=0.; first=None
    for _ in range(horizon):
        new_limit=next_step(curr,target)
        if first is None: first=new_limit
        send=min(up,up*(new_limit/2.)/60.,80.)
        cap=max(17.,29.-.08*max(0.,down-42.))
        discharge=min(down,down*(v_down/1.)/60.,cap)
        new_up=max(0.,up+arrival-send)
        new_down=max(0.,down+send-discharge)
        cost+=new_up+new_down+2.*max(0.,new_down-45.)+.8*max(0.,send-cap)**2
        cost+=.5*abs(new_limit-curr)/10.
        up,down,curr=new_up,new_down,new_limit
    return cost,first

def next_mpc(current: int, obs: dict) -> int:
    candidates=[(predict_rollout(obs,current,target)[0], -target, predict_rollout(obs,current,target)[1])
                 for target in (70,80,90,100)]
    return min(candidates)[2]

def create_network(folder: Path, lanes_mid: int=1) -> Path:
    folder.mkdir(parents=True,exist_ok=True)
    nodes=ET.Element('nodes')
    for i in range(7):
        attrs={'id':f'n{i}','x':str(i*1000),'y':'0'}
        if i==4:attrs['type']='zipper'
        ET.SubElement(nodes,'node',attrs)
    ET.ElementTree(nodes).write(folder/'road.nod.xml',encoding='utf-8',xml_declaration=True)
    edges=ET.Element('edges')
    for i in range(6):
        ET.SubElement(edges,'edge',{'id':f'e{i}', 'from':f'n{i}', 'to':f'n{i+1}',
              'numLanes':str(lanes_mid if i==4 else 3), 'speed':f'{BASE_SPEED/3.6:.6f}', 'priority':'1'})
    ET.ElementTree(edges).write(folder/'road.edg.xml',encoding='utf-8',xml_declaration=True)
    dest=folder/'road.net.xml'
    cp=subprocess.run(['netconvert','--node-files',str(folder/'road.nod.xml'),
                        '--edge-files',str(folder/'road.edg.xml'),'--output-file',str(dest),
                        '--no-turnarounds','true'],capture_output=True,text=True,timeout=60)
    if cp.returncode:raise RuntimeError('netconvert: '+cp.stderr[-1500:])
    return dest

def write_routes(path: Path,demand: int,weather: str,demand_end_s: int):
    p=WEATHER[weather]
    root=ET.Element('routes')
    ET.SubElement(root,'vType',{'id':'car','vClass':'passenger','accel':str(p['accel']),
      'decel':str(p['decel']),'sigma':'0.5','tau':str(p['tau']), 'length':'5', 'minGap':'2.5',
      'maxSpeed':f'{BASE_SPEED/3.6:.6f}', 'speedFactor':str(p['speedFactor']), 'speedDev':'0.0'})
    ET.SubElement(root,'route',{'id':'main','edges':' '.join(f'e{i}' for i in range(6))})
    ET.SubElement(root,'flow',{'id':'flow','type':'car','route':'main','begin':'0',
      'end':str(demand_end_s),'vehsPerHour':str(demand),'departLane':'random','departSpeed':'max'})
    ET.ElementTree(root).write(path,encoding='utf-8',xml_declaration=True)

def run_policy(folder: Path, net: Path, route: Path, *, demand: int, weather: str,
               seed: int, duration_s: int, injection_end_s: int, policy: str,
               report: Callable[[float],None] | None=None) -> dict:
    if policy not in POLICIES: raise ValueError('unknown policy')
    import traci
    folder.mkdir(exist_ok=True,parents=True)
    summ=folder/'summary.xml'
    cmd=['sumo','-n',str(net),'-r',str(route),'--summary',str(summ),
         '--no-step-log','true','--duration-log.disable','true','--seed',str(seed),
         '--end',str(duration_s)]
    # Small/free-instance configuration: teleport extremely stalled cars to avoid
    # unbounded queue accumulation; this CHANGES model semantics vs research runs.
    cmd += ['--time-to-teleport', '300']
    # Fail with SUMO stderr, not a generic connection-refused loop, where possible.
    traci.start(cmd, port=None, numRetries=3)
    current_limit=100; changes=0.; decisions=[]; frames=[]; timeline=[]
    accum={f'e{i}':0. for i in range(4)}
    speed_n=0.; speed_weight=0.
    try:
        for step in range(1,duration_s+1):
            traci.simulationStep()
            counts={e:traci.edge.getLastStepVehicleNumber(e) for e in accum}
            for e,num in counts.items():accum[e]+=num
            n=counts[SENSOR]
            if n>0:
                speed=traci.edge.getLastStepMeanSpeed(SENSOR)*3.6
                if math.isfinite(speed) and speed >= 0:
                    speed_n+=n;speed_weight+=n*speed
            if step%60==0 or step==1:
                # Each observed car is in a SUMO lane, not a fabricated visual distribution.
                vehicles=[]; speeds=[]; slow=0
                for i in range(6):
                    edge=f'e{i}'
                    for vid in traci.edge.getLastStepVehicleIDs(edge):
                        try:
                            x=i*1000+traci.vehicle.getLanePosition(vid)
                            lane=traci.vehicle.getLaneIndex(vid)
                            kmh=traci.vehicle.getSpeed(vid)*3.6
                        except traci.TraCIException:
                            continue
                        if len(vehicles) < 400:
                            vehicles.append([round(x,1),int(lane),round(kmh,1)])
                        speeds.append(kmh)
                        if kmh<20:slow+=1
                frames.append({'time_s':step,'limit_kmh':current_limit,'vehicles':vehicles,
                  'count':len(vehicles),'mean_speed_kmh':round(sum(speeds)/len(speeds),2) if speeds else None,
                  'slow_pct':round(slow/len(speeds)*100,1) if speeds else None})
            if step%60==0:
                means={e:accum[e]/60. for e in accum}
                observed=speed_weight/speed_n if speed_n else float('nan')
                v0=traci.edge.getLastStepMeanSpeed('e0')*3.6 if counts['e0']>0 else 0.
                obs={'n_up':means['e1']+means['e2'], 'n_down':means['e3'],
                     'arrival_per_min':means['e0']*max(0.,v0)/60., 'downstream_speed_kmh':observed}
                previous=current_limit
                if policy=='rule':current_limit=next_rule(current_limit,observed)
                elif policy=='weather_rule':current_limit=next_weather_rule(current_limit,observed,weather)
                elif policy=='mpc':current_limit=next_mpc(current_limit,obs)
                if policy!='static':
                    for edge in CONTROL_EDGES:traci.edge.setMaxSpeed(edge,current_limit/3.6)
                changes+=abs(current_limit-previous)/10.
                decisions.append({'time_s':step,'limit_kmh':current_limit,
                                  'sensor_speed_kmh':round(observed,1) if math.isfinite(observed) else None})
                timeline.append({'minute':step//60,'limit_kmh':current_limit,
                                 'sensor_speed_kmh':round(observed,1) if math.isfinite(observed) else None})
                accum={e:0. for e in accum};speed_n=0.;speed_weight=0.
                if report:report(step/duration_s)
    finally:
        try: traci.close()
        except Exception: pass
        gc.collect()
    # Keep runner's vehicle-hour definition identical to notebook 12.
    hours=0.; final=None
    for _, elem in ET.iterparse(summ,events=('end',)):
        if elem.tag=='step':
            a=elem.attrib
            hours+=(float(a['running'])+float(a['waiting']))/3600.
            final=a.copy()
        elem.clear()
    if final is None:raise RuntimeError('SUMO summary has no steps')
    completed=int(float(final['ended']));loaded=int(float(final['loaded']))
    unfinished=max(0,loaded-completed)
    J=hours+.25*unfinished+.03*changes
    return {'policy':policy,'name':LABELS[policy],'metrics':{
       'objective_vehicle_hour_equiv':round(J,3), 'vehicle_hours':round(hours,3),
       'unfinished':unfinished,'completed':completed,'loaded':loaded,'control_change_units':changes},
       'timeline':timeline,'frames':frames}

def execute_job(workdir: Path, params:dict, progress:Callable[[float,str],None]) -> dict:
    workdir.mkdir(parents=True,exist_ok=True)
    net=create_network(workdir/'network')
    duration_s=params['duration_minutes']*60
    # Demand lasts first 2/3 of run; give the system time to drain.
    injection_end_s=int(duration_s*2/3)
    route=workdir/'routes.xml'
    write_routes(route,params['demand'],params['weather'],injection_end_s)
    outcomes=[]; policies=params['policies']
    for idx,policy in enumerate(policies):
        progress(idx/len(policies),f'{LABELS[policy]} simülasyonu çalışıyor')
        result=run_policy(workdir/policy,net,route,demand=params['demand'],
               weather=params['weather'],seed=params['seed'],duration_s=duration_s,
               injection_end_s=injection_end_s,policy=policy,
               report=lambda fraction,idx=idx:progress((idx+fraction)/len(policies),f'{LABELS[policy]} çalışıyor'))
        outcomes.append(result)
    progress(1.,'Tamamlandı')
    return {'config':params,'metadata':{
      'synthetic_network':'6 km, 3→1→3 şerit','demand_injection_end_minutes':injection_end_s/60.,
      'sample_interval_seconds':60,'control_interval_seconds':60,
      'scope':'Synthetic low-memory demonstration. 300s teleport enabled; results are NOT directly comparable to previous no-teleport research runs. Not road-calibrated.'},
      'runs':outcomes}
