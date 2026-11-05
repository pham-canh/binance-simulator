#!/usr/bin/env python3
"""Run every local gate and write reports/TEST_RESULTS.json.

The file contains only observed output. If a gate fails, the script still
writes the evidence and exits non-zero.
"""

import json
import os
import re
import subprocess
import sys
from datetime import datetime, timezone

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)
EVIDENCE = os.path.join(ROOT, 'reports', 'evidence')
AUDIT_LOG = os.path.join(ROOT, 'reports', 'AUDIT_LOG.jsonl')
SUMMARY = re.compile(
    r'(\d+) passed(?:, (\d+) skipped)?(?:, (\d+) xfailed)?')


def env():
    result = os.environ.copy()
    result.setdefault('KYBER_ENV', 'simulation')
    result.setdefault('SIMULATOR_REDIS', 'fake')
    result.setdefault('SIMULATOR_OFFLINE', '1')
    result.setdefault('SIMULATOR_CLOCK', '1700000000000')
    result.setdefault('SIMULATOR_CHAIN_SEED', 'binance-incident-demo')
    result.setdefault('SIMULATOR_DELAY_MS',
                      str(10 * 365 * 24 * 3600 * 1000))
    result.setdefault('PYTEST_DISABLE_PLUGIN_AUTOLOAD', '1')
    return result


def run(args):
    process = subprocess.run(
        [sys.executable] + args, cwd=ROOT, env=env(),
        capture_output=True, text=True)
    return process


def json_blob(text):
    start = text.find('{')
    if start < 0:
        raise ValueError('no JSON object in output:\n' + text)
    return json.loads(text[start:])


def main():
    os.makedirs(EVIDENCE, exist_ok=True)
    gates = []

    tests = run(['-m', 'pytest', '-o', 'addopts=', '-q'])
    match = SUMMARY.search(tests.stdout)
    counts = {
        'passed': int(match.group(1)) if match else 0,
        'skipped': int(match.group(2) or 0) if match else 0,
        'xfailed': int(match.group(3) or 0) if match else 0,
    }
    with open(os.path.join(EVIDENCE, 'phase5-pytest.txt'), 'w') as handle:
        handle.write(tests.stdout + tests.stderr)
    gates.append({
        'name': 'pytest',
        'ok': tests.returncode == 0,
        'counts': counts,
        'command': 'PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 .venv/bin/python '
                   '-m pytest -o addopts=\'\' -q',
    })

    api = run(['scripts/verify_phase1.py'])
    api_result = json_blob(api.stdout) if api.returncode == 0 else None
    with open(os.path.join(EVIDENCE, 'phase1-api.json'), 'w') as handle:
        json.dump(api_result, handle, indent=2)
    gates.append({
        'name': 'live-api',
        'ok': api.returncode == 0 and api_result.get('status') == 'ok',
        'checks': len(api_result['checks']) if api_result else 0,
        'command': '.venv/bin/python scripts/verify_phase1.py',
    })

    replay = run(['scripts/replay_incident.py'])
    replay_result = json_blob(replay.stdout) if replay.returncode == 0 else None
    gates.append({
        'name': 'incident-replay',
        'ok': replay.returncode == 0,
        'summary': replay_result,
        'command': '.venv/bin/python scripts/replay_incident.py',
    })

    audit_ok = False
    audit_count = 0
    if os.path.exists(AUDIT_LOG):
        from simulator import security
        records = security.WithdrawalGuard.read_audit_file(AUDIT_LOG)
        audit_count = len(records)
        audit_ok = security.WithdrawalGuard().verify_audit_chain(records)
    gates.append({
        'name': 'audit-file-chain',
        'ok': audit_ok,
        'records': audit_count,
        'file': 'reports/AUDIT_LOG.jsonl',
    })

    s1 = run(['scripts/show_s1.py'])
    s1_result = json_blob(s1.stdout) if s1.returncode == 0 else None
    gates.append({
        'name': 'withdrawal-ordering',
        'ok': bool(s1_result
                   and s1_result.get('ordering_bug_present') is False
                   and s1_result.get('broadcasts_after')
                   == s1_result.get('broadcasts_before')),
        'result': s1_result,
        'command': '.venv/bin/python scripts/show_s1.py',
    })

    dashboard = run(['scripts/check_dashboard.py'])
    dashboard_result = (json_blob(dashboard.stdout)
                        if dashboard.returncode == 0 else None)
    gates.append({
        'name': 'dashboard',
        'ok': dashboard.returncode == 0,
        'result': dashboard_result,
        'command': '.venv/bin/python scripts/check_dashboard.py',
    })

    result = {
        'generated_at': datetime.now(timezone.utc).isoformat(),
        'synthetic': True,
        'overall': 'ok' if all(gate['ok'] for gate in gates) else 'failed',
        'gates': gates,
    }
    with open(os.path.join(ROOT, 'reports', 'TEST_RESULTS.json'), 'w') as f:
        json.dump(result, f, indent=2)

    print(json.dumps({
        'overall': result['overall'],
        'gates': {gate['name']: gate['ok'] for gate in gates},
    }, indent=2))
    return 0 if result['overall'] == 'ok' else 1


if __name__ == '__main__':
    sys.exit(main())
