#!/usr/bin/env python3
"""Start the simulator, exercise the real HTTP API, and print evidence.

Every check is an assertion against a live process. The server is terminated
in ``finally`` so the script leaves no listener behind.
"""

import json
import os
import subprocess
import sys
import time

import requests

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PORT = int(os.environ.get('SIMULATOR_PORT', '5100'))
BASE = 'http://127.0.0.1:{}'.format(PORT)
HEADERS = {'X-MBX-APIKEY': 'demo-user'}
EVIDENCE = os.path.join(ROOT, 'reports', 'evidence')
SERVER_LOG = os.path.join(EVIDENCE, 'phase1-server.log')


def wait_for_ping(timeout=15.0):
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            if requests.get(BASE + '/ping', timeout=1).text == 'pong':
                return
        except requests.RequestException:
            pass
        time.sleep(0.2)
    raise RuntimeError('server did not answer /ping')


def get_json(path, **kwargs):
    response = requests.get(BASE + path, timeout=3, **kwargs)
    response.raise_for_status()
    return response.json()


def post_json(path, **kwargs):
    response = requests.post(BASE + path, timeout=3, **kwargs)
    response.raise_for_status()
    return response.json()


def delete_json(path, **kwargs):
    response = requests.delete(BASE + path, timeout=3, **kwargs)
    response.raise_for_status()
    return response.json()


def main():
    os.makedirs(EVIDENCE, exist_ok=True)
    env = os.environ.copy()
    env.setdefault('SIMULATOR_PORT', str(PORT))
    env.setdefault('SIMULATOR_OFFLINE', '1')

    with open(SERVER_LOG, 'w') as log:
        server = subprocess.Popen(
            [sys.executable, 'scripts/run_demo_server.py'],
            cwd=ROOT, env=env, stdout=log, stderr=subprocess.STDOUT)
        try:
            wait_for_ping()

            checks = []

            ping = requests.get(BASE + '/ping', timeout=3).text
            assert ping == 'pong', ping
            checks.append({'check': 'ping', 'result': ping})

            info = get_json('/api/v1/exchangeInfo')
            assert info['timezone'] == 'UTC'
            assert len(info['symbols']) == 236
            checks.append({
                'check': 'exchangeInfo',
                'symbols': len(info['symbols']),
            })

            account = get_json('/api/v3/account', headers=HEADERS)
            assert account['canWithdraw'] is True
            assert len(account['balances']) == 13
            omg = [b for b in account['balances'] if b['asset'] == 'OMG'][0]
            assert omg['free'] == '1000.0'
            checks.append({
                'check': 'account',
                'canWithdraw': account['canWithdraw'],
                'assets': len(account['balances']),
                'OMG_free': omg['free'],
            })

            depth = get_json('/api/v1/depth?symbol=OMGETH')
            assert depth['asks'] and depth['bids']
            checks.append({
                'check': 'depth',
                'asks': depth['asks'],
                'bids': depth['bids'],
            })

            order = post_json(
                '/api/v3/order', headers=HEADERS,
                params={'symbol': 'OMGETH', 'quantity': '10',
                        'price': '0.004', 'side': 'SELL'})
            assert 'orderId' in order
            order_id = order['orderId']
            checks.append({'check': 'place_resting_order',
                           'orderId': order_id})

            open_orders = get_json(
                '/api/v3/openOrders?symbol=OMGETH', headers=HEADERS)
            assert any(str(o['orderId']) == str(order_id)
                       for o in open_orders)
            checks.append({'check': 'open_orders',
                           'count': len(open_orders)})

            canceled = delete_json(
                '/api/v3/order', headers=HEADERS,
                params={'symbol': 'OMGETH', 'orderId': order_id})
            assert str(canceled['orderId']) == str(order_id)
            checks.append({'check': 'cancel_order',
                           'orderId': canceled['orderId']})

            filled = post_json(
                '/api/v3/order', headers=HEADERS,
                params={'symbol': 'OMGETH', 'quantity': '10',
                        'price': '0.003', 'side': 'SELL'})
            assert 'orderId' in filled
            checks.append({'check': 'marketable_order',
                           'orderId': filled['orderId']})

            withdrawal = post_json(
                '/wapi/v3/withdraw.html', headers=HEADERS,
                params={'asset': 'omg', 'amount': '1',
                        'address': '0xc7159686de47f2ca06fcd1e74d1b9a1a0e584259'})
            assert withdrawal['success'] is True
            checks.append({'check': 'withdraw',
                           'id': withdrawal['id']})

            history = get_json(
                '/wapi/v3/withdrawHistory.html', headers=HEADERS)
            assert len(history['withdrawList']) == 1
            checks.append({
                'check': 'withdraw_history',
                'count': len(history['withdrawList']),
                'txId': history['withdrawList'][0]['txId'],
            })

            print(json.dumps({
                'base': BASE,
                'checks': checks,
                'status': 'ok',
            }, indent=2))
        finally:
            server.terminate()
            try:
                server.wait(timeout=5)
            except subprocess.TimeoutExpired:
                server.kill()


if __name__ == '__main__':
    main()
