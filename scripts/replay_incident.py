#!/usr/bin/env python3
"""Run the deterministic incident replay and save its evidence."""

import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

os.environ.setdefault('KYBER_ENV', 'simulation')
os.environ.setdefault('SIMULATOR_REDIS', 'fake')
os.environ.setdefault('SIMULATOR_OFFLINE', '1')
os.environ.setdefault('SIMULATOR_CLOCK', '1700000000000')
os.environ.setdefault('SIMULATOR_CHAIN_SEED', 'binance-incident-demo')
os.environ.setdefault('SIMULATOR_DELAY_MS', str(10 * 365 * 24 * 3600 * 1000))

from simulator.incident import run_replay  # noqa: E402


def main():
    evidence_dir = os.path.join(ROOT, 'reports', 'evidence')
    os.makedirs(evidence_dir, exist_ok=True)
    audit_path = os.path.join(ROOT, 'reports', 'AUDIT_LOG.jsonl')
    result = run_replay(audit_path=audit_path)

    output_path = os.path.join(evidence_dir, 'phase3-replay.json')
    with open(output_path, 'w', encoding='utf-8') as handle:
        json.dump(result, handle, indent=2)

    summary = {
        'events': len(result['events']),
        'public_facts': len(result['public_facts']),
        'operator_balance_omg': result['final']['operator_balance_omg'],
        'broadcasts': result['final']['chain_broadcasts'],
        'audit_valid': result['final']['guard']['audit_chain_valid'],
        'audit_records': result['final']['guard']['audit_records'],
        'evidence': os.path.relpath(output_path, ROOT),
        'audit_log': os.path.relpath(audit_path, ROOT),
    }
    print(json.dumps(summary, indent=2))


if __name__ == '__main__':
    main()
