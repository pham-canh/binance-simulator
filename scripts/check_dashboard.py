#!/usr/bin/env python3
"""Smoke-check the dashboard and status route with Flask's test client."""

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

from binance_api import api  # noqa: E402

MARKERS = [
    'BINANCE SIMULATOR',
    'INDEPENDENT EDUCATIONAL SIMULATOR',
    'NOT BINANCE',
    'SYNTHETIC ENVIRONMENT',
]


def main():
    client = api.test_client()
    page = client.get('/')
    body = page.get_data(as_text=True)
    assert page.status_code == 200, page.status_code
    for marker in MARKERS:
        assert marker in body, 'missing marker: {}'.format(marker)

    status = client.get('/api/v1/simulator/status').get_json()
    assert status['synthetic'] is True
    assert status['display_name'] == 'BINANCE SIMULATOR'
    assert status['guard']['audit_chain_valid'] is True

    print(json.dumps({
        'page_status': page.status_code,
        'page_bytes': len(body),
        'markers': MARKERS,
        'display_name': status['display_name'],
        'synthetic': status['synthetic'],
        'audit_chain_valid': status['guard']['audit_chain_valid'],
    }, indent=2))


if __name__ == '__main__':
    main()
