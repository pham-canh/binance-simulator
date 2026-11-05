"""Deterministic in-process ledger for the educational simulator.

This module never opens a socket, never signs a real transaction and never
touches a wallet. It exists so the original exchange engine can be exercised
and recorded without Docker, Redis, an Ethereum node or credentials.

The ledger has two buckets per address:

``hot_wallet``
    Funds available to the simulated exchange for withdrawals.

``pending_deposits``
    Funds the simulated chain reports as waiting to be credited. The original
    ``Exchange.check_deposits`` treats this as the deposit contract balance and
    clears it after crediting the user.
"""

import hashlib
import os
import threading


class FakeChain:
    def __init__(self, seed=None):
        self.seed = str(seed or os.environ.get(
            'SIMULATOR_CHAIN_SEED', 'binance-demo'))
        self._lock = threading.RLock()
        self._hot_wallet = {}
        self._pending_deposits = {}
        self._transactions = {}
        self._broadcasts = []
        self._nonce = 0

    def _key(self, value):
        if isinstance(value, int):
            return value
        if isinstance(value, str):
            text = value.strip()
            try:
                return int(text, 16)
            except ValueError:
                return text
        return value

    def _token_key(self, token):
        return self._key(getattr(token, 'address', token))

    def _bucket(self, store, address):
        return store.setdefault(self._key(address), {})

    def seed_hot_wallet(self, address, tokens):
        """Give the simulated exchange enough funds to honour withdrawals."""
        bucket = self._bucket(self._hot_wallet, address)
        for token in tokens:
            if hasattr(token, 'address'):
                token_address = token.address
                decimals = token.decimals
            else:
                token_address, decimals = token[0], token[1]
            bucket[self._token_key(token_address)] = 10 ** (decimals + 12)
        return self.snapshot()

    def credit_pending(self, address, token, amount):
        """Synthetic deposit before it is credited by ``check_deposits``."""
        amount = int(amount)
        if amount <= 0:
            raise ValueError('Deposit amount must be positive')
        bucket = self._bucket(self._pending_deposits, address)
        token_key = self._token_key(token)
        bucket[token_key] = bucket.get(token_key, 0) + amount
        return self.snapshot()

    def get_balances(self, address, tokens):
        bucket = self._pending_deposits.get(self._key(address), {})
        return [int(bucket.get(self._token_key(token), 0)) for token in tokens]

    def clear_deposits(self, private_key, address, token_array, amounts):
        with self._lock:
            bucket = self._bucket(self._pending_deposits, address)
            for token, amount in zip(token_array, amounts):
                token_key = self._token_key(token)
                current = bucket.get(token_key, 0)
                bucket[token_key] = current - min(int(amount), current)
            token = token_array[0] if token_array else 0
            return self._record(address, token, 0, address, 'clear_deposits')

    def withdraw(self, private_key, exchange_address, token, amount,
                 destination):
        amount = int(amount)
        if amount <= 0:
            raise ValueError('Withdrawal amount must be positive')

        with self._lock:
            bucket = self._bucket(self._hot_wallet, exchange_address)
            token_key = self._token_key(token)
            current = bucket.get(token_key, 0)
            if amount > current:
                raise ValueError(
                    'simulated hot wallet has insufficient token balance')
            bucket[token_key] = current - amount
            return self._record(
                exchange_address, token_key, amount, destination, 'withdraw')

    def _record(self, source, token, amount, destination, kind):
        self._nonce += 1
        raw = '{}:{}:{}:{}:{}:{}'.format(
            self.seed, self._nonce, source, token, amount, destination)
        tx_hash = '0x' + hashlib.sha256(raw.encode()).hexdigest()
        record = {
            'kind': kind,
            'source': str(source),
            'token': str(token),
            'amount': amount,
            'destination': str(destination),
            'status': 'confirmed',
        }
        self._transactions[tx_hash] = record
        if kind == 'withdraw':
            self._broadcasts.append({'tx': tx_hash, **record})
        return tx_hash

    def is_tx_confirmed(self, tx_hash):
        return str(tx_hash) in self._transactions

    def wait_for_tx_confirmation(self, tx_hash):
        return self.is_tx_confirmed(tx_hash)

    def broadcast_count(self):
        return len(self._broadcasts)

    def snapshot(self):
        def plain(store):
            return {
                str(address): {
                    str(token): int(amount)
                    for token, amount in bucket.items()
                }
                for address, bucket in store.items()
            }

        return {
            'seed': self.seed,
            'hot_wallet': plain(self._hot_wallet),
            'pending_deposits': plain(self._pending_deposits),
            'broadcasts': list(self._broadcasts),
            'transaction_count': len(self._transactions),
        }


_chains = {}


def get_chain():
    pid = os.getpid()
    if pid not in _chains:
        _chains[pid] = FakeChain()
    return _chains[pid]


def reset_chain(seed=None):
    _chains[os.getpid()] = FakeChain(seed)
    return _chains[os.getpid()]


def seed_demo_chain():
    """Seed every simulated exchange hot wallet with synthetic funds."""
    from . import config

    chain = get_chain()
    tokens = list(config.SUPPORTED_TOKENS.values())
    for address in config.EXCHANGES_ADDRESS.values():
        chain.seed_hot_wallet(address, tokens)
    return chain.snapshot()


def simulate_deposit(exchange_address, token_name, amount):
    """Add a synthetic deposit in whole tokens for demo/testing."""
    from . import config

    token = config.SUPPORTED_TOKENS[token_name.lower()]
    base_units = int(round(float(amount) * (10 ** token.decimals)))
    return get_chain().credit_pending(exchange_address, token, base_units)
