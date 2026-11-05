"""Deterministic educational replay of a withdrawal-control incident.

PUBLIC FACT entries are copied from the public reporting summarised in
``reports/PROJECT_ANALYSIS.md``. SCENARIO and CONTROL entries are synthetic
and exist only inside this simulator. The replay never contacts a network and
never signs a real transaction.
"""

import os

from . import config, fake_chain, security, utils
from .balance_handler import BalanceHandler
from .exchange import Exchange
from .order_handler import CoreOrder

OPERATOR = 'ops-demo'
TRUSTED = '0x00000000000000000000000000000000000000aa'
UNTRUSTED = '0x00000000000000000000000000000000000000bb'

PUBLIC_FACTS = [
    {
        'date': '2026-10-29 20:05 UTC',
        'fact': 'Binance hot wallets were compromised; approximately '
                '$6.3B of token assets were affected.',
        'source': 'Binance Support, Security Incident Update #2 (2026-10-30)',
    },
    {
        'date': '2026-10-30',
        'fact': 'Withdrawals were suspended; roughly $3B was frozen on-chain; '
                'Binance said it found no evidence that wallet private keys '
                'were leaked.',
        'source': 'Binance Support, Security Incident Update #2 (2026-10-30)',
    },
    {
        'date': '2026-11-03',
        'fact': 'Initial findings pointed to unauthorized access to an '
                'internal wallet signing service and malicious EIP-7702 '
                'authorizations; $6.34B impacted and $2.85B frozen.',
        'source': 'Binance, 29 October 2026 Incident: Initial Findings',
    },
    {
        'date': '2026-10-29 23:56 UTC',
        'fact': 'The final unauthorized transfer of 2,961.9 ETH was '
                'finalized on-chain.',
        'source': 'Binance, 29 October 2026 Incident: Initial Findings',
    },
    {
        'date': '2026-10-30 00:10 UTC',
        'fact': 'Binance cleared the EIP-7702 delegation code from the '
                'Binance14 hot wallet.',
        'source': 'Binance, 29 October 2026 Incident: Initial Findings',
    },
]


def _network_summary(seed):
    tokens = list(config.SUPPORTED_TOKENS.values())
    summary = {}
    for name in ('ethereum', 'bsc', 'tron'):
        chain = fake_chain.FakeChain('{}-{}'.format(seed, name))
        chain.seed_hot_wallet(config.EXCHANGES_ADDRESS['binance'], tokens)
        snapshot = chain.snapshot()
        summary[name] = {
            'simulated': True,
            'hot_wallet_buckets': len(snapshot['hot_wallet']),
            'token_buckets': sum(len(bucket) for bucket in
                                 snapshot['hot_wallet'].values()),
            'broadcasts': len(snapshot['broadcasts']),
        }
    return summary


def run_replay(seed='binance-incident-demo', audit_path=None):
    """Run the fixed scenario and return an evidence dictionary."""
    if audit_path:
        os.environ['SIMULATOR_AUDIT_LOG'] = audit_path
        if os.path.exists(audit_path):
            os.remove(audit_path)

    rdb = utils.get_redis_db()
    rdb.delete('balance_{}_available'.format(OPERATOR),
               'balance_{}_lock'.format(OPERATOR))

    chain = fake_chain.reset_chain(seed)
    tokens = list(config.SUPPORTED_TOKENS.values())
    chain.seed_hot_wallet(config.EXCHANGES_ADDRESS['binance'], tokens)

    balance = BalanceHandler(rdb, config.SUPPORTED_TOKENS.keys())
    exchange = Exchange(
        'binance',
        'synthetic-private-key',
        tokens,
        rdb,
        CoreOrder(),
        balance,
        config.EXCHANGES_ADDRESS['binance'],
        config.EXCHANGE_INFO['binance'])

    guard = security.reset_guard()
    guard.trust_address(TRUSTED)
    guard.trust_address(config.EXCHANGES_ADDRESS['binance'])

    events = []

    def add(classification, event, **fields):
        record = {
            'seq': len(events) + 1,
            'classification': classification,
            'event': event,
        }
        record.update(fields)
        events.append(record)
        return record

    for fact in PUBLIC_FACTS:
        add('PUBLIC FACT', 'reported-incident', **fact)

    networks = _network_summary(seed)
    add('SCENARIO', 'synthetic-network-topology',
        detail='Three deterministic in-process ledgers are seeded; no chain '
               'node or wallet is involved.',
        networks=networks)

    balance.deposit(OPERATOR, 'omg', 1000.0, 'available')
    add('SCENARIO', 'synthetic-operator-balance',
        user=OPERATOR, asset='OMG', available=1000.0,
        detail='Synthetic operations account with withdrawal permission.')

    add('SCENARIO', 'compromised-authorization-grant',
        user=OPERATOR, scope='withdraw',
        detail='A stolen synthetic API key is used. The replay models only '
               'the authorization boundary; it does not model phishing, '
               'endpoint compromise, or the real signing service.')

    # Attempt 1: the anomalous amount is rejected before any broadcast.
    before_balance = balance.get(OPERATOR, 'available')['omg']
    before_broadcasts = chain.broadcast_count()
    error = None
    try:
        exchange.withdraw(OPERATOR, 'omg', UNTRUSTED, 999999)
    except Exception as exc:  # SecurityError is a ValueError
        error = {'type': type(exc).__name__,
                 'code': getattr(exc, 'code', None),
                 'message': str(exc)}
    after_balance = balance.get(OPERATOR, 'available')['omg']
    after_broadcasts = chain.broadcast_count()
    add('CONTROL', 'over-limit-withdrawal-rejected',
        asset='OMG', requested=999999.0, address=UNTRUSTED,
        error=error,
        balance_before=before_balance, balance_after=after_balance,
        broadcasts_before=before_broadcasts,
        broadcasts_after=after_broadcasts,
        detail='The API rejects the request, the balance is unchanged, and '
               'the simulated chain receives no transaction.')

    # Attempt 2: below the hard block, above the anomaly threshold. The
    # request is allowed once, but an alert is recorded.
    activity = exchange.withdraw(OPERATOR, 'omg', UNTRUSTED, 400)
    add('SCENARIO', 'suspicious-withdrawal-allowed-with-alert',
        asset='OMG', amount=400.0, address=UNTRUSTED,
        tx=activity.tx, broadcast_count=chain.broadcast_count(),
        detail='New address above the alert threshold raises an anomaly but '
               'stays below the hard block threshold.')

    # Attempt 3: incident response pauses withdrawals.
    guard.pause(reason='suspicious withdrawal to a new address')
    events.append({
        'seq': len(events) + 1,
        'classification': 'CONTROL',
        'event': 'emergency-withdrawal-pause',
        'reason': 'suspicious withdrawal to a new address',
    })
    before_broadcasts = chain.broadcast_count()
    error = None
    try:
        exchange.withdraw(OPERATOR, 'omg', UNTRUSTED, 400)
    except Exception as exc:
        error = {'type': type(exc).__name__,
                 'code': getattr(exc, 'code', None),
                 'message': str(exc)}
    add('CONTROL', 'paused-withdrawal-rejected',
        asset='OMG', requested=400.0, address=UNTRUSTED, error=error,
        broadcasts_before=before_broadcasts,
        broadcasts_after=chain.broadcast_count(),
        detail='The pause blocks further movement while the responder '
               'investigates.')

    # Attempt 4: revoke the synthetic operator permission after the pause is
    # lifted, so the rejection is attributable to revocation (-9002).
    guard.resume()
    guard.revoke(OPERATOR, reason='compromised credential')
    events.append({
        'seq': len(events) + 1,
        'classification': 'CONTROL',
        'event': 'permission-revoked',
        'user': OPERATOR,
        'reason': 'compromised credential',
    })
    error = None
    try:
        exchange.withdraw(OPERATOR, 'omg', TRUSTED, 1)
    except Exception as exc:
        error = {'type': type(exc).__name__,
                 'code': getattr(exc, 'code', None),
                 'message': str(exc)}
    add('CONTROL', 'revoked-withdrawal-rejected',
        asset='OMG', requested=1.0, address=TRUSTED, error=error,
        detail='Even a small withdrawal to a trusted address is rejected '
               'while the permission is revoked.')

    guard.resume()
    guard.grant(OPERATOR)
    add('CONTROL', 'operator-restored',
        user=OPERATOR,
        detail='The synthetic permission is restored after the drill.')

    audit = guard.audit_records()
    add('EVIDENCE', 'audit-chain',
        records=len(audit),
        valid=guard.verify_audit_chain(),
        head=audit[-1]['hash'] if audit else None,
        detail='SHA-256 hash-chained audit records cover every allow/deny '
               'decision.')

    final = {
        'operator_balance_omg': balance.get(OPERATOR, 'available')['omg'],
        'chain_broadcasts': chain.broadcast_count(),
        'sandbox_chain': chain.snapshot(),
        'guard': guard.snapshot(),
    }

    return {
        'title': 'Binance Security Incident Simulator — Educational Replay',
        'claim_boundary': (
            'Independent educational simulator. Synthetic data only. Not '
            'affiliated with Binance. The scenario is an analogue at the '
            'withdrawal-control boundary, not a reproduction of the real '
            'intrusion chain.'),
        'seed': seed,
        'public_facts': PUBLIC_FACTS,
        'events': events,
        'final': final,
    }
