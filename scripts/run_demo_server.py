#!/usr/bin/env python3
"""Run the Binance-compatible simulator with synthetic data only.

No Docker, no real Redis, no scheduler, no core service, no chain node and no
credentials. The process uses fakeredis and the in-process FakeChain.

Examples:
    .venv/bin/python scripts/run_demo_server.py
    SIMULATOR_PORT=5101 .venv/bin/python scripts/run_demo_server.py
"""

import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

# Fixed clock keeps order-book lookups and the incident replay deterministic.
os.environ.setdefault('KYBER_ENV', 'simulation')
os.environ.setdefault('SIMULATOR_REDIS', 'fake')
os.environ.setdefault('SIMULATOR_OFFLINE', '1')
os.environ.setdefault('SIMULATOR_CLOCK', '1700000000000')
os.environ.setdefault('SIMULATOR_CHAIN_SEED', 'binance-demo-phase1')
os.environ.setdefault('SIMULATOR_DELAY_MS', str(10 * 365 * 24 * 3600 * 1000))

from setup_data import init_balance  # noqa: E402
from simulator import config, utils, web3_interface  # noqa: E402
from simulator.balance_handler import BalanceHandler  # noqa: E402


def seed_order_book(rdb, pair='omg_eth', rate=0.003, quantity=1000):
    timestamp = utils.normalize_timestamp(utils.get_timestamp())
    key = '_'.join(['binance', pair, str(timestamp)])
    book = {
        'Asks': [{'Rate': rate, 'Quantity': quantity}],
        'Bids': [{'Rate': rate, 'Quantity': quantity}],
    }
    rdb.set(key, json.dumps(book))
    return key


def seed_demo_account(rdb, user='demo-user', amount=1000):
    balance = BalanceHandler(rdb, config.SUPPORTED_TOKENS.keys())
    for token in config.SUPPORTED_TOKENS:
        balance.deposit(user, token, amount, 'available')


def main():
    rdb = utils.get_redis_db()
    init_balance()
    seed_demo_account(rdb)
    seed_order_book(rdb)
    web3_interface.seed_demo_chain()

    from binance_api import api, binance  # noqa: E402

    host = os.environ.get('SIMULATOR_HOST', '127.0.0.1')
    port = int(os.environ.get('SIMULATOR_PORT', '5100'))
    logger = utils.get_logger()
    logger.info(
        'demo server: mode=%s redis=fake clock=%s seed=%s host=%s port=%s',
        config.MODE, os.environ.get('SIMULATOR_CLOCK'),
        os.environ.get('SIMULATOR_CHAIN_SEED'), host, port)
    logger.info('demo account: X-MBX-APIKEY=demo-user')
    logger.info('hot wallet: %s', binance.deposit_address)
    api.run(host=host, port=port, debug=False, use_reloader=False)


if __name__ == '__main__':
    main()
