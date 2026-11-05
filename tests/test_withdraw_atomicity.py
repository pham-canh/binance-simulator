"""Regression tests for the pre-broadcast withdrawal ordering (S1).

The red test is intentionally written before the Phase 4 fix. On the original
engine the balance debit fails *after* the simulated chain transfer has already
been broadcast, so this test must fail until the ordering is corrected.
"""

import unittest

from simulator import config, fake_chain, security, utils
from simulator.balance_handler import BalanceHandler
from simulator.exchange import Exchange
from simulator.order_handler import CoreOrder

USER = 'security-red-user'
ADDRESS = '0xc7159686de47f2ca06fcd1e74d1b9a1a0e584259'


class WithdrawAtomicityTest(unittest.TestCase):

    def setUp(self):
        self.rdb = utils.get_redis_db()
        self.rdb.delete('balance_{}_available'.format(USER),
                        'balance_{}_lock'.format(USER))
        security.reset_guard()
        self.chain = fake_chain.reset_chain('withdraw-atomicity')
        self.chain.seed_hot_wallet(
            config.EXCHANGES_ADDRESS['binance'],
            list(config.SUPPORTED_TOKENS.values()))
        self.balance = BalanceHandler(
            self.rdb, config.SUPPORTED_TOKENS.keys())
        self.exchange = Exchange(
            'binance',
            'synthetic-private-key',
            list(config.SUPPORTED_TOKENS.values()),
            self.rdb,
            CoreOrder(),
            self.balance,
            config.EXCHANGES_ADDRESS['binance'],
            config.EXCHANGE_INFO['binance'])

    def test_withdraw_over_limit_must_not_broadcast(self):
        self.balance.deposit(USER, 'omg', 10.0, 'available')
        before_balance = self.balance.get(USER, 'available')['omg']
        before_broadcasts = self.chain.broadcast_count()

        with self.assertRaises(ValueError):
            self.exchange.withdraw(USER, 'omg', ADDRESS, 999999)

        after_balance = self.balance.get(USER, 'available')['omg']
        after_broadcasts = self.chain.broadcast_count()

        self.assertEqual(before_balance, after_balance)
        self.assertEqual(before_broadcasts, after_broadcasts)

    def test_insufficient_balance_must_not_broadcast(self):
        # 100 OMG is inside the policy limits, so only the debit can reject
        # it. This is the test that would still fail if the engine broadcast
        # before checking the balance.
        self.balance.deposit(USER, 'omg', 10.0, 'available')
        before = self.chain.snapshot()['transaction_count']

        with self.assertRaises(ValueError):
            self.exchange.withdraw(USER, 'omg', ADDRESS, 100)

        after = self.chain.snapshot()
        self.assertEqual(before, after['transaction_count'])
        self.assertEqual([], after['broadcasts'])
