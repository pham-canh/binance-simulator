#!/usr/bin/env python3
"""Print the saved incident replay as a compact terminal timeline."""

import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from simulator import security  # noqa: E402

EVIDENCE = os.path.join(ROOT, 'reports', 'evidence', 'phase3-replay.json')
AUDIT = os.path.join(ROOT, 'reports', 'AUDIT_LOG.jsonl')


def main():
    with open(EVIDENCE, 'r', encoding='utf-8') as handle:
        data = json.load(handle)

    print('INCIDENT REPLAY  seed={}'.format(data['seed']))
    print('-' * 78)
    for event in data['events']:
        label = event['classification']
        name = event['event']
        line = '{:>2}. {:<11} {}'.format(event['seq'], label, name)
        print(line)
        if name == 'over-limit-withdrawal-rejected':
            print('    requested={} error={} balance={} -> {} '
                  'broadcasts={} -> {}'.format(
                      event['requested'], event['error']['code'],
                      event['balance_before'], event['balance_after'],
                      event['broadcasts_before'],
                      event['broadcasts_after']))
        elif name == 'paused-withdrawal-rejected':
            print('    requested={} error={} broadcasts={} -> {}'.format(
                event['requested'], event['error']['code'],
                event['broadcasts_before'], event['broadcasts_after']))
        elif name == 'revoked-withdrawal-rejected':
            print('    requested={} error={}'.format(
                event['requested'], event['error']['code']))
        elif name == 'suspicious-withdrawal-allowed-with-alert':
            print('    amount={} tx={} broadcast_count={}'.format(
                event['amount'], event['tx'][:18] + '...',
                event['broadcast_count']))

    records = security.WithdrawalGuard.read_audit_file(AUDIT)
    valid = security.WithdrawalGuard().verify_audit_chain(records)
    final = data['final']
    print('-' * 78)
    print('final balance={} OMG  broadcasts={}  audit records={}  valid={}'
          .format(final['operator_balance_omg'],
                  final['chain_broadcasts'],
                  len(records), valid))
    if not valid:
        raise SystemExit('audit chain is not valid')
    print(data['claim_boundary'])


if __name__ == '__main__':
    main()
