"""Tests for the Phase 4 withdrawal controls.

Every test uses synthetic balances and the in-process FakeChain. No network,
no real key and no real asset movement is involved.
"""

import threading
import unittest
from unittest import mock

from simulator import config, fake_chain, security, utils
from simulator.balance_handler import BalanceHandler
from simulator.exchange import Exchange
from simulator.order_handler import CoreOrder

USER = 'controls-user'
TRUSTED = '0x00000000000000000000000000000000000000aa'
UNTRUSTED = '0x00000000000000000000000000000000000000bb'


class SecurityControlsTest(unittest.TestCase):

    def setUp(self):
        self.rdb = utils.get_redis_db()
        self.rdb.delete('balance_{}_available'.format(USER),
                        'balance_{}_lock'.format(USER))
        self.chain = fake_chain.reset_chain('security-controls')
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
        security.reset_guard()
        security.get_guard().trust_address(TRUSTED)

    def _deposit(self, amount=1000.0, asset='omg'):
        self.balance.deposit(USER, asset, amount, 'available')

    def _withdraw(self, amount, address=TRUSTED, key=None):
        return self.exchange.withdraw(USER, 'omg', address, amount,
                                      idempotency_key=key)

    def test_single_withdrawal_limit_blocks_before_broadcast(self):
        self._deposit()
        before = self.balance.get(USER, 'available')['omg']
        broadcasts = self.chain.broadcast_count()

        with self.assertRaises(security.SecurityError) as ctx:
            self._withdraw(600)

        self.assertEqual(ctx.exception.code, -9003)
        self.assertEqual(before, self.balance.get(USER, 'available')['omg'])
        self.assertEqual(broadcasts, self.chain.broadcast_count())

    def test_daily_limit_blocks_after_accumulated_withdrawals(self):
        self._deposit(3000)
        guard = security.get_guard()
        guard.policy['daily']['omg'] = 1000.0
        self._withdraw(400)
        self._withdraw(400)

        with self.assertRaises(security.SecurityError) as ctx:
            self._withdraw(400)

        self.assertEqual(ctx.exception.code, -9004)

    def test_velocity_limit_blocks_rapid_requests(self):
        self._deposit(100)
        for _ in range(3):
            self._withdraw(1)

        with self.assertRaises(security.SecurityError) as ctx:
            self._withdraw(1)

        self.assertEqual(ctx.exception.code, -9005)

    def test_emergency_pause_blocks_and_resume_restores(self):
        self._deposit(100)
        guard = security.get_guard()
        guard.pause(reason='incident response')
        with self.assertRaises(security.SecurityError) as ctx:
            self._withdraw(1)
        self.assertEqual(ctx.exception.code, -9001)

        guard.resume()
        activity = self._withdraw(1)
        self.assertIn(activity.tx, [a['tx'] for a in
                                   self.chain.snapshot()['broadcasts']])

    def test_revoked_permission_blocks_until_regranted(self):
        self._deposit(100)
        guard = security.get_guard()
        guard.revoke(USER)
        with self.assertRaises(security.SecurityError) as ctx:
            self._withdraw(1)
        self.assertEqual(ctx.exception.code, -9002)

        guard.grant(USER)
        self.assertTrue(self._withdraw(1))

    def test_untrusted_address_is_alerted_and_blocked_for_large_amounts(self):
        security.reset_guard({'max_single': {'omg': 1000.0},
                              'daily': {'omg': 5000.0}})
        security.get_guard().trust_address(TRUSTED)
        self._deposit(2000)
        self.assertTrue(self._withdraw(200, address=UNTRUSTED))
        events = [r['event'] for r in security.get_guard().audit_records()]
        self.assertIn('anomaly.detected', events)

        with self.assertRaises(security.SecurityError) as ctx:
            self._withdraw(600, address=UNTRUSTED)
        self.assertEqual(ctx.exception.code, -9006)

    def test_idempotency_key_prevents_double_broadcast(self):
        self._deposit(100)
        first = self._withdraw(10, key='req-1')
        second = self._withdraw(10, key='req-1')

        self.assertIs(first, second)
        self.assertEqual(self.balance.get(USER, 'available')['omg'], 90.0)
        self.assertEqual(self.chain.broadcast_count(), 1)

    def test_idempotency_key_is_scoped_per_asset(self):
        self._deposit(100)
        self.balance.deposit(USER, 'eth', 100, 'available')

        first = self._withdraw(10, key='shared-key')
        second = self.exchange.withdraw(USER, 'eth', TRUSTED, 10,
                                        idempotency_key='shared-key')

        self.assertIsNot(first, second)
        self.assertEqual(self.balance.get(USER, 'available')['omg'], 90.0)
        self.assertEqual(self.balance.get(USER, 'available')['eth'], 90.0)
        self.assertEqual(self.chain.broadcast_count(), 2)

    def test_concurrent_same_key_broadcasts_once(self):
        self._deposit(100)
        results, errors = [], []
        barrier = threading.Barrier(2)

        def worker():
            barrier.wait()
            try:
                results.append(self._withdraw(10, key='concurrent-key'))
            except Exception as exc:  # pragma: no cover - failure detail
                errors.append(exc)

        threads = [threading.Thread(target=worker) for _ in range(2)]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()

        self.assertEqual([], errors)
        self.assertEqual(2, len(results))
        self.assertIs(results[0], results[1])
        self.assertEqual(self.balance.get(USER, 'available')['omg'], 90.0)
        self.assertEqual(self.chain.broadcast_count(), 1)

    def test_daily_limit_is_scoped_per_asset(self):
        self._deposit(2000)
        self.balance.deposit(USER, 'eth', 100, 'available')
        self._withdraw(450)
        self._withdraw(450)
        activity = self.exchange.withdraw(USER, 'eth', TRUSTED, 10)
        self.assertTrue(activity)

    def test_destination_address_is_required(self):
        self._deposit(100)
        with self.assertRaises(security.SecurityError) as ctx:
            self._withdraw(10, address='')
        self.assertEqual(ctx.exception.code, -9007)

    def test_chain_failure_refunds_the_internal_debit(self):
        self._deposit(100)
        before = self.balance.get(USER, 'available')['omg']
        with mock.patch('simulator.web3_interface.withdraw',
                        side_effect=RuntimeError('simulated chain outage')):
            with self.assertRaises(RuntimeError):
                self._withdraw(10)

        self.assertEqual(before, self.balance.get(USER, 'available')['omg'])
        events = [r['event'] for r in security.get_guard().audit_records()]
        self.assertIn('withdraw.refunded', events)

    def test_audit_chain_detects_tampering(self):
        self._deposit(100)
        self._withdraw(10)
        with self.assertRaises(security.SecurityError):
            self._withdraw(999999)

        guard = security.get_guard()
        records = guard.audit_records()
        self.assertTrue(guard.verify_audit_chain())
        self.assertGreaterEqual(len(records), 3)

        tampered = [dict(r) for r in records]
        tampered[1]['amount'] = 999.0
        self.assertFalse(guard.verify_audit_chain(tampered))


if __name__ == '__main__':
    unittest.main()
