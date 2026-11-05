"""Withdrawal authorization, limits and tamper-evident audit records.

Everything here is synthetic and in-process. The guard is deliberately small:
it demonstrates the defensive controls the incident replay needs, without
pretending to be a production risk engine.

Controls:
    * per-asset single-withdrawal and daily limits;
    * velocity limiting inside a fixed window;
    * emergency pause (global or per user);
    * permission revocation;
    * untrusted-address anomaly alerts and hard blocks;
    * idempotency keys;
    * a SHA-256 hash-chained audit trail.
"""

import hashlib
import json
import math
import os
import threading

from . import utils


class SecurityError(ValueError):
    def __init__(self, code, message):
        super().__init__(message)
        self.code = code


DEFAULT_POLICY = {
    'max_single_default': 1000.0,
    'max_single': {'omg': 500.0, 'eth': 10.0},
    'daily_default': 2000.0,
    'daily': {'omg': 1000.0, 'eth': 20.0},
    'velocity_count': 3,
    'velocity_window_ms': 60 * 1000,
    'untrusted_alert': 100.0,
    'untrusted_block': 500.0,
}

GENESIS = '0' * 64
WINDOW_MS = 24 * 60 * 60 * 1000


def _day(timestamp):
    return int(timestamp) // WINDOW_MS


class WithdrawalGuard:

    def __init__(self, policy=None):
        self.policy = dict(DEFAULT_POLICY)
        if policy:
            for key, value in policy.items():
                if isinstance(value, dict) and isinstance(
                        self.policy.get(key), dict):
                    self.policy[key] = dict(self.policy[key], **value)
                else:
                    self.policy[key] = value
        self._lock = threading.RLock()
        self._user_locks = {}
        self._paused = False
        self._pause_reason = None
        self._paused_users = {}
        self._revoked = set()
        self._known_addresses = set()
        self._attempts = {}
        self._daily = {}
        self._idempotent = {}
        self._audit = []
        self._last_hash = GENESIS
        self._seq = 0

    # -- policy helpers -------------------------------------------------
    def _max_single(self, asset):
        return float(self.policy['max_single'].get(
            asset, self.policy['max_single_default']))

    def _daily_limit(self, asset):
        return float(self.policy['daily'].get(
            asset, self.policy['daily_default']))

    def trust_address(self, address):
        with self._lock:
            self._known_addresses.add(str(address).strip().lower())

    def withdrawal_lock(self, user):
        """Serialize one user's withdraw flow, including in-flight broadcast.

        The guard-level lock protects the shared dicts; this per-user lock keeps
        an idempotency key from being committed twice by two concurrent
        requests. Different users still run concurrently.
        """
        with self._lock:
            if user not in self._user_locks:
                self._user_locks[user] = threading.RLock()
            return self._user_locks[user]

    # -- state changes --------------------------------------------------
    def pause(self, user=None, reason='emergency withdrawal pause'):
        with self._lock:
            if user:
                self._paused_users[user] = reason
                self._log('withdraw.paused', user=user, reason=reason)
            else:
                self._paused = True
                self._pause_reason = reason
                self._log('withdraw.paused', user=None, reason=reason)

    def resume(self, user=None):
        with self._lock:
            if user:
                self._paused_users.pop(user, None)
                self._log('withdraw.resumed', user=user)
            else:
                self._paused = False
                self._pause_reason = None
                self._log('withdraw.resumed', user=None)

    def revoke(self, user, reason='withdrawal permission revoked'):
        with self._lock:
            self._revoked.add(user)
            self._log('permission.revoked', user=user, reason=reason)

    def grant(self, user):
        with self._lock:
            self._revoked.discard(user)
            self._log('permission.granted', user=user)

    def can_withdraw(self, user):
        with self._lock:
            return (not self._paused
                    and user not in self._paused_users
                    and user not in self._revoked)

    # -- checks ---------------------------------------------------------
    def lookup(self, user, asset, idempotency_key):
        if not idempotency_key:
            return None
        with self._lock:
            return self._idempotent.get(
                (user, asset.lower(), str(idempotency_key)))

    def authorize(self, user, asset, amount, address):
        amount = float(amount)
        asset = asset.lower()
        address = str(address).strip() if address is not None else ''
        with self._lock:
            if not math.isfinite(amount) or amount <= 0:
                self._deny('withdraw.denied', user, asset, amount, address,
                           -9000, 'withdrawal amount must be finite and '
                           'positive')
            if not address:
                self._deny('withdraw.denied', user, asset, amount, address,
                           -9007, 'withdrawal destination address is required')
            if self._paused:
                self._deny('withdraw.denied', user, asset, amount, address,
                           -9001, 'withdrawals are paused: {}'.format(
                               self._pause_reason))
            if user in self._paused_users:
                self._deny('withdraw.denied', user, asset, amount, address,
                           -9001, 'user withdrawals are paused: {}'.format(
                               self._paused_users[user]))
            if user in self._revoked:
                self._deny('withdraw.denied', user, asset, amount, address,
                           -9002, 'withdraw permission has been revoked')

            max_single = self._max_single(asset)
            if amount > max_single:
                self._deny('withdraw.denied', user, asset, amount, address,
                           -9003,
                           'amount {} exceeds single-withdrawal limit {} for '
                           '{}'.format(amount, max_single, asset.upper()))

            now = utils.get_timestamp()
            spent = self._daily.get((user, asset, _day(now)), 0.0)
            daily_limit = self._daily_limit(asset)
            if spent + amount > daily_limit:
                self._deny('withdraw.denied', user, asset, amount, address,
                           -9004,
                           'daily limit {} {} would be exceeded'.format(
                               daily_limit, asset.upper()))

            window = int(self.policy['velocity_window_ms'])
            recent = [
                stamp for stamp in self._attempts.get(user, [])
                if now - stamp <= window
            ]
            if len(recent) >= int(self.policy['velocity_count']):
                self._deny('withdraw.denied', user, asset, amount, address,
                           -9005, 'withdrawal velocity limit reached')

            normalized_address = address.lower()
            if normalized_address not in self._known_addresses:
                if amount >= float(self.policy['untrusted_block']):
                    self._deny(
                        'withdraw.denied', user, asset, amount, address,
                        -9006,
                        'untrusted withdrawal address blocked for amount '
                        '{}'.format(amount))
                if amount >= float(self.policy['untrusted_alert']):
                    self._log('anomaly.detected', user=user, asset=asset,
                              amount=amount, address=address,
                              reason='untrusted withdrawal address')

            self._log('withdraw.authorized', user=user, asset=asset,
                      amount=amount, address=address)
            return True

    def _deny(self, event, user, asset, amount, address, code, reason):
        self._log(event, user=user, asset=asset, amount=amount,
                  address=address, code=code, reason=reason)
        raise SecurityError(code, reason)

    def commit(self, user, asset, amount, address, idempotency_key=None,
               activity=None, tx=None):
        asset = asset.lower()
        with self._lock:
            now = utils.get_timestamp()
            key = (user, asset, _day(now))
            self._daily[key] = self._daily.get(key, 0.0) + float(amount)
            self._attempts.setdefault(user, []).append(now)
            if idempotency_key:
                self._idempotent[(user, asset, str(idempotency_key))] = activity
            self._log('withdraw.settled', user=user, asset=asset,
                      amount=float(amount), address=str(address), tx=tx,
                      activity_id=getattr(activity, 'id', None))

    def record(self, event, **fields):
        with self._lock:
            return self._log(event, **fields)

    # -- audit ----------------------------------------------------------
    def _log(self, event, **fields):
        self._seq += 1
        record = {
            'seq': self._seq,
            'ts': utils.get_timestamp(),
            'event': event,
        }
        record.update(fields)
        record['prev'] = self._last_hash
        digest = self._digest(record)
        record['hash'] = digest
        self._last_hash = digest
        self._audit.append(record)
        self._append_file(record)
        return record

    @staticmethod
    def _digest(record):
        body = {key: value for key, value in record.items()
                if key != 'hash'}
        canonical = json.dumps(body, sort_keys=True, default=str)
        return hashlib.sha256(canonical.encode('utf-8')).hexdigest()

    @staticmethod
    def _append_file(record):
        path = os.environ.get('SIMULATOR_AUDIT_LOG')
        if not path:
            return
        directory = os.path.dirname(os.path.abspath(path))
        try:
            os.makedirs(directory, exist_ok=True)
            with open(path, 'a', encoding='utf-8') as handle:
                handle.write(json.dumps(record, sort_keys=True) + '\n')
        except OSError:
            # The in-memory hash chain remains the source of truth. A demo
            # must not report a rejected withdrawal as failed just because
            # the optional evidence file is unwritable.
            pass

    def audit_records(self):
        with self._lock:
            return list(self._audit)

    def verify_audit_chain(self, records=None, expected_count=None,
                           expected_head=None):
        records = self._audit if records is None else records
        if expected_count is not None and len(records) != expected_count:
            return False
        if expected_head is not None:
            if not records or records[-1].get('hash') != expected_head:
                return False
        previous = GENESIS
        for index, record in enumerate(records, start=1):
            if record.get('seq') != index:
                return False
            if record.get('prev') != previous:
                return False
            if self._digest(record) != record.get('hash'):
                return False
            previous = record['hash']
        return True

    @staticmethod
    def read_audit_file(path):
        records = []
        with open(path, 'r', encoding='utf-8') as handle:
            for line in handle:
                line = line.strip()
                if line:
                    records.append(json.loads(line))
        return records

    def snapshot(self):
        with self._lock:
            return {
                'paused': self._paused,
                'pause_reason': self._pause_reason,
                'paused_users': dict(self._paused_users),
                'revoked': sorted(self._revoked),
                'audit_records': len(self._audit),
                'audit_chain_valid': self.verify_audit_chain(),
            }


_guards = {}
_guards_lock = threading.Lock()


def get_guard():
    pid = os.getpid()
    with _guards_lock:
        if pid not in _guards:
            _guards[pid] = WithdrawalGuard()
        return _guards[pid]


def reset_guard(policy=None):
    pid = os.getpid()
    with _guards_lock:
        _guards[pid] = WithdrawalGuard(policy)
        return _guards[pid]
