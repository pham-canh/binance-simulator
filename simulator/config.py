#!/usr/bin/python3
import sys
import os
import json
import logging
import logging.config

import yaml


class Token:

    def __init__(self, token, address, decimals):
        self.token = token
        self.address = address
        self.decimals = decimals

    def __str__(self):
        return self.token

    def __repr__(self):
        return self.token


def get_int(hex_str):
    return int(hex_str, 16)


REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CONFIG_PATH = os.environ.get(
    'SIMULATOR_CONFIG', os.path.join(REPO_ROOT, 'config.yml'))

MODE = os.environ.get('KYBER_ENV', 'dev')
try:
    with open(CONFIG_PATH, 'r') as f:
        cfg = yaml.safe_load(f)

        logging.config.dictConfig(cfg['logging'])

        DELAY = int(os.environ.get(
            'SIMULATOR_DELAY_MS', cfg[MODE]['delay']))
        BLOCKCHAIN_URL = os.environ.get(
            'SIMULATOR_BLOCKCHAIN_URL', cfg[MODE]['blockchain_url'])

        addresses_path = cfg[MODE]['addresses']
        if not os.path.isabs(addresses_path):
            addresses_path = os.path.join(REPO_ROOT, addresses_path)

        try:
            with open(addresses_path, 'r') as f:
                addr = json.loads(f.read())

                EXCHANGES_ADDRESS = addr['exchangesAddress']
                for k, v in EXCHANGES_ADDRESS.items():
                    EXCHANGES_ADDRESS[k] = get_int(v)

                BANK_ADDRESS = get_int(addr['bank'])
                SUPPORTED_TOKENS = {}
                for name, token in addr['tokens'].items():
                    name = name.lower()
                    SUPPORTED_TOKENS[name] = Token(name,
                                                   get_int(token['address']),
                                                   token['decimals'])
        except FileNotFoundError as e:
            sys.exit('Deployment file is missing.')

except FileNotFoundError:
    sys.exit('Config file is missing.')

EXCHANGE_INFO = {}
with open(os.path.join(REPO_ROOT, 'info/binance.json'), 'r') as f:
    EXCHANGE_INFO['binance'] = json.loads(f.read())
with open(os.path.join(REPO_ROOT, 'info/bittrex.json'), 'r') as f:
    EXCHANGE_INFO['bittrex'] = json.loads(f.read())

# Synthetic placeholders. They are never used to sign a real request, are
# not valid credential formats, and must not be replaced with real keys.
SECRET = b'synthetic-hmac-secret-for-local-simulation-only'
LOGGER_NAME = "simulator"
EXCHANGE_NAME = "liqui"

API_KEY = {
    'liqui': 'synthetic-api-key-liqui',
    'binance': 'synthetic-api-key-binance',
    'bittrex': 'synthetic-api-key-bittrex'
}

PRIVATE_KEY = {
    'bittrex': 'synthetic-private-key-bittrex',
    'liqui': 'synthetic-private-key-liqui',
    'poloniex': 'synthetic-private-key-poloniex',
    'binance': 'synthetic-private-key-binance',
    'bitfinex': 'synthetic-private-key-bitfinex'
}

INITIAL_BALANCE = {
    'bittrex': {
        'omg': 221,
        'eth': 5000,
        'dgd': 24,
        'cvc': 4900,
        'fun': 33557,
        'mco': 318,
        'gnt': 5492.5,
        'adx': 1766.5,
        'pay': 1424.5,
        'bat': 6756.5,
        'knc': 1004,
        'eos': 543.5,
        'link': 4385
    },
    'liqui': {
        'omg': 5000,
        'eth': 5000,
        'dgd': 5000,
        'cvc': 5000,
        'fun': 5000,
        'mco': 5000,
        'gnt': 5000,
        'adx': 5000,
        'pay': 5000,
        'bat': 5000,
        'knc': 5000,
        'eos': 5000,
        'link': 5000
    },
    'binance': {
        'omg': 221,
        'eth': 5000,
        'dgd': 24,
        'cvc': 4900,
        'fun': 33557,
        'mco': 318,
        'gnt': 5492.5,
        'adx': 1766.5,
        'pay': 1424.5,
        'bat': 6756.5,
        'knc': 1004,
        'eos': 543.5,
        'link': 4385
    }
}
