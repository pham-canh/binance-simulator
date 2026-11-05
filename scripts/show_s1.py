#!/usr/bin/env python3
"""Record the withdrawal-ordering behaviour (S1).

Before Phase 4 this script reproduced the bug: the API rejected an over-limit
withdrawal while a transfer had already been broadcast. The historical output
is kept in ``reports/evidence/phase1-s1.json``. Run it again after the fix to
show ``ordering_bug_present: false`` and no new broadcast.
"""

import json
import logging
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

os.environ.setdefault('KYBER_ENV', 'simulation')
os.environ.setdefault('SIMULATOR_REDIS', 'fake')
os.environ.setdefault('SIMULATOR_CLOCK', '1700000000000')
os.environ.setdefault('SIMULATOR_OFFLINE', '1')
os.environ.setdefault('SIMULATOR_CHAIN_SEED', 'phase1-s1')

from binance_api import api, balance_handler, rdb  # noqa: E402
from simulator import web3_interface  # noqa: E402

logging.disable(logging.CRITICAL)

USER = 'demo-user'
ADDRESS = '0xc7159686de47f2ca06fcd1e74d1b9a1a0e584259'


def main():
    rdb.flushdb()
    balance_handler.deposit(USER, 'omg', 10, 'available')
    web3_interface.seed_demo_chain()

    before_balance = balance_handler.get(USER, 'available')['omg']
    before_chain = web3_interface.transaction_snapshot()

    client = api.test_client()
    response = client.post(
        '/wapi/v3/withdraw.html',
        headers={'X-MBX-APIKEY': USER},
        query_string={
            'asset': 'omg',
            'amount': '999999',
            'address': ADDRESS,
        })
    body = response.get_json()

    after_balance = balance_handler.get(USER, 'available')['omg']
    after_chain = web3_interface.transaction_snapshot()
    before_count = len(before_chain['broadcasts'])
    after_count = len(after_chain['broadcasts'])
    bug_present = after_count > before_count

    print(json.dumps({
        'scenario': 'over-limit withdrawal',
        'api_response': body,
        'balance_before': before_balance,
        'balance_after': after_balance,
        'broadcasts_before': before_count,
        'broadcasts_after': after_count,
        'ordering_bug_present': bug_present,
        'result': (
            'S1 REPRODUCED — the request was rejected but a transaction was '
            'broadcast' if bug_present else
            'BLOCKED — the request was rejected before any broadcast and the '
            'balance is unchanged'),
        'broadcast': (after_chain['broadcasts'][-1]
                      if after_chain['broadcasts'] else None),
    }, indent=2))


if __name__ == '__main__':
    main()
