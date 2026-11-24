#!/usr/bin/env python3
"""Run existing DynamicSpeed SUMO simulation.py using a GitHub Actions runner.

No web API needed: simulation runs in Actions and writes downloadable results.
"""
from __future__ import annotations
import argparse
import csv
import json
import os
from pathlib import Path
import shutil
import sys
import traceback
from datetime import datetime, timezone

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="DynamicSpeed independent SUMO experiment")
    p.add_argument('--demand', type=int, default=2600)
    p.add_argument('--duration', type=int, default=30)
    p.add_argument('--weather', choices=['dry', 'light_rain', 'heavy_rain'], default='dry')
    p.add_argument('--seed', type=int, default=314)
    p.add_argument('--policy-a', choices=['static', 'rule', 'mpc', 'weather_rule'], default='static')
    p.add_argument('--policy-b', choices=['static', 'rule', 'mpc', 'weather_rule'], default='rule')
    p.add_argument('--output', default='actions_results')
    return p.parse_args()


def validate(a: argparse.Namespace) -> None:
    if a.demand < 400 or a.demand > 5500 or a.demand % 100:
        raise ValueError('Trafik talebi 400–5500 ve 100 araç/saatin katı olmalı')
    if a.duration not in (10, 30, 60, 90):
        raise ValueError('Süre 10, 30, 60 veya 90 dakika olmalı')
    if not 1 <= a.seed <= 999999:
        raise ValueError('Tohum 1–999999 aralığında olmalı')
    if a.policy_a == a.policy_b:
        raise ValueError('Karşılaştırma için farklı iki kontrolcü seçin')
    for binary in ('sumo', 'netconvert'):
        if shutil.which(binary) is None:
            raise RuntimeError(f'{binary} bulunamadı. GitHub Actions kurulum adımını kontrol edin.')


def main() -> int:
    args = parse_args()
    out = (ROOT / args.output).resolve()
    out.mkdir(parents=True, exist_ok=True)
    params = dict(demand=args.demand, duration_minutes=args.duration,
                  weather=args.weather, seed=args.seed,
                  policies=[args.policy_a, args.policy_b])
    manifest = {
        'started_utc': datetime.now(timezone.utc).isoformat(),
        'params': params,
        'source_commit': os.environ.get('GITHUB_SHA', 'local'),
        'runner': os.environ.get('RUNNER_NAME', 'local'),
        'simulation_code': 'simulation.py in checked-out repository',
        'status': 'running',
        'note': 'Synthetic model. This is NOT a live road traffic forecast.'
    }
    (out / 'run_manifest.json').write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding='utf-8')

    try:
        # Keep existing research algorithm and source unchanged.
        import simulation
        def report(frac, message):
            percent = round(frac * 100, 1)
            print(f'[{percent:5.1f}%] {message}', flush=True)

        result = simulation.execute_job(out / 'work', params, report)
        (out / 'result.json').write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding='utf-8')
        with (out / 'summary.csv').open('w', encoding='utf-8-sig', newline='') as fh:
            writer = csv.writer(fh)
            writer.writerow(['policy', 'name', 'J', 'vehicle_hours', 'completed', 'unfinished', 'loaded', 'control_change_units'])
            for row in result['runs']:
                m = row['metrics']
                writer.writerow([row['policy'], row['name'], m['objective_vehicle_hour_equiv'],
                                 m['vehicle_hours'], m['completed'], m['unfinished'],
                                 m['loaded'], m['control_change_units']])
        manifest['status'] = 'completed'
        print('\n=== RESULTS ===', flush=True)
        print((out / 'summary.csv').read_text(encoding='utf-8-sig'), flush=True)
        return 0
    except BaseException as exc:
        manifest['status'] = 'failed'
        manifest['error'] = str(exc)
        (out / 'error.txt').write_text(traceback.format_exc(), encoding='utf-8')
        traceback.print_exc()
        return 1
    finally:
        manifest['finished_utc'] = datetime.now(timezone.utc).isoformat()
        (out / 'run_manifest.json').write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding='utf-8')


if __name__ == '__main__':
    sys.exit(main())
