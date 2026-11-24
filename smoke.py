"""Run `python -m app.smoke` inside Docker to validate SUMO/netconvert/TraCI end-to-end."""
from pathlib import Path
import json, tempfile
from .simulation import execute_job

def main():
    params={'demand':1800,'weather':'dry','seed':314,'duration_minutes':5,'policies':['static','rule']}
    with tempfile.TemporaryDirectory(prefix='ds_smoke_') as tmp:
        result=execute_job(Path(tmp),params,lambda frac,msg:None)
    assert len(result['runs'])==2
    for run in result['runs']:
        assert run['frames'] and run['metrics']['loaded']>=run['metrics']['completed']
        assert run['metrics']['objective_vehicle_hour_equiv']>=0
    print('SUMO smoke test passed:',json.dumps([{'policy':r['policy'],**r['metrics']} for r in result['runs']],ensure_ascii=False))
if __name__=='__main__':main()
