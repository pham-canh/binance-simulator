from functools import wraps
import os
import traceback

from flask import Flask, request, jsonify

from simulator import config, utils, security, web3_interface
from simulator.dashboard import DISPLAY_NAME, DISCLAIMER, render_dashboard
from simulator.order_handler import CoreOrder, SimulationOrder
from simulator.balance_handler import BalanceHandler
from simulator.exchange import Binance

api = Flask(__name__)

logger = utils.get_logger()

MISSING_ERROR = {
    'symbol': {
        'code': -1102,
        'msg': "Mandatory parameter 'symbol' was not sent, "
        "was empty/null, or malformed."
    },
    'api_key': {
        'code': -2015,
        'msg': 'Invalid read-key, API-key, and/or IP.'
    }
}

# Synthetic tenants. These are not Binance keys and are never sent anywhere.
ALLOWED_API_KEYS = {
    key.strip().lower()
    for key in os.environ.get(
        'SIMULATOR_API_KEYS', 'demo-user,ops-demo,api_key'
    ).split(',')
    if key.strip()
}


def _missing(name):
    if name in MISSING_ERROR:
        return MISSING_ERROR[name]
    return {
        'code': -1102,
        'msg': "Mandatory parameter '{}' was not sent, "
               "was empty/null, or malformed.".format(name)
    }


def validate_params(expected_params):
    for p in expected_params:
        if not request.args.get(p):
            return _missing(p)


def action(expected_params=[], public=False):
    def decorator(func):
        @wraps(func)
        def wrapper():
            error = validate_params(expected_params)
            if error:
                return str(error)

            params = request.args.to_dict()
            logger.debug('Original params: {}'.format(params))
            if not public:
                api_key = request.headers.get('X-MBX-APIKEY')
                if not api_key or api_key.lower() not in ALLOWED_API_KEYS:
                    return str(MISSING_ERROR['api_key'])
                else:
                    params['api_key'] = api_key.lower()

            params['timestamp'] = utils.get_timestamp(request.args.to_dict())

            logger.debug('Params: {}'.format(params))
            try:
                result = func(params)
            except Exception as e:
                # traceback.print_exc()
                logger.error('Error Output: {}'.format(str(e)))
                return jsonify({'code': -1, 'msg': str(e)})

            logger.debug('Output: {}'.format(result))

            return jsonify(result)
        return wrapper
    return decorator


@api.route('/api/v1/exchangeInfo', methods=['GET'])
@action(public=True)
def exchange_info(params):
    return binance.get_info_api()


@api.route('/api/v1/depth', methods=['GET'])
@action(expected_params=['symbol'], public=True)
def order_book(params):
    return binance.get_order_book_api(**params)


@api.route('/api/v3/account', methods=['GET'])
@action(public=False)
def account(params):
    return binance.get_account_api(**params)


@api.route('/api/v3/order', methods=['POST'])
@action(public=False)
def create_order(params):
    return binance.trade_api(**params)


@api.route('/api/v3/order', methods=['GET'])
@action(public=False)
def get_order(params):
    return binance.get_order_api(**params)


@api.route('/api/v3/allOrders', methods=['GET'])
@action(public=False)
def get_all_orders(params):
    return binance.get_all_orders_api(**params)


@api.route('/api/v3/openOrders', methods=['GET'])
@action(public=False)
def get_open_orders(params):
    return binance.get_open_orders_api(**params)


@api.route('/api/v3/order', methods=['DELETE'])
@action(public=False)
def cancel_order(params):
    return binance.cancel_order_api(**params)


@api.route('/wapi/v3/withdraw.html', methods=['POST'])
@action(expected_params=['asset', 'amount', 'address'], public=False)
def withdraw(params):
    return binance.withdraw_api(**params)


@api.route('/wapi/v3/withdrawHistory.html', methods=['GET'])
@action(public=False)
def withdraw_history(params):
    return binance.withdraw_history_api(**params)


@api.route('/wapi/v3/depositHistory.html', methods=['GET'])
@action(public=False)
def deposit_history(params):
    return binance.deposit_history_api(**params)


@api.route('/ping')
def ping():
    return 'pong'


@api.route('/')
def dashboard():
    return render_dashboard()


@api.route('/api/v1/simulator/status', methods=['GET'])
def simulator_status():
    guard = security.get_guard()
    chain = web3_interface.transaction_snapshot()
    return jsonify({
        'display_name': DISPLAY_NAME,
        'disclaimer': DISCLAIMER,
        'synthetic': True,
        'guard': guard.snapshot(),
        'chain': {
            'seed': chain['seed'],
            'broadcasts': len(chain['broadcasts']),
            'transactions': chain['transaction_count'],
            'hot_wallet_buckets': len(chain['hot_wallet']),
        },
    })


rdb = utils.get_redis_db()
if config.MODE == 'simulation':
    order_handler = SimulationOrder(rdb)
else:
    order_handler = CoreOrder()

supported_tokens = config.SUPPORTED_TOKENS
balance_handler = BalanceHandler(rdb, supported_tokens.keys())


binance = Binance(
    'binance',
    config.PRIVATE_KEY['binance'],
    list(supported_tokens.values()),
    rdb,
    order_handler,
    balance_handler,
    config.EXCHANGES_ADDRESS['binance'],
    config.EXCHANGE_INFO['binance']
)

if __name__ == '__main__':
    logger.info("Running in {} mode".format(config.MODE))
    api.run(host='127.0.0.1', port=5100, debug=False)
