#!/usr/bin/env python3
"""Compact review findings for the video.

The four critical rows are the headline; the total comes from the report,
so the video cannot understate how many findings were fixed.
"""

import os
from collections import Counter

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REPORT = os.path.join(ROOT, 'reports', 'SECURITY_REPORT.md')

FINDINGS = [
    ('BLOCKER', 'concurrent same-key both broadcast', 'per-user lock'),
    ('HIGH', 'idempotency key not asset-scoped', 'key = (user, asset, key)'),
    ('HIGH', 'audit verifier accepted empty lists', 'seq + read-back gate'),
    ('HIGH', 'any API key selected new identity', 'synthetic allowlist'),
]


def main():
    print('INDEPENDENT REVIEW  -  findings and disposition')
    print('=' * 78)
    print('{:<9} {:<46} {}'.format('SEVERITY', 'FINDING', 'FIX'))
    print('-' * 78)
    for severity, finding, fix in FINDINGS:
        print('{:<9} {:<46} {}'.format(severity, finding, fix))
    print('=' * 78)
    total = Counter()
    with open(REPORT, 'r', encoding='utf-8') as handle:
        section = handle.read().split('## 4. Independent review')[1]
        section = section.split('## 5.')[0]
        for line in section.splitlines():
            if not line.startswith('|'):
                continue
            cells = [cell.strip() for cell in line.split('|')]
            if len(cells) > 1 and cells[1] in {
                    'BLOCKER', 'HIGH', 'MEDIUM', 'LOW'}:
                total[cells[1]] += 1
    print('Total fixed: {} (1 blocker, {} high, {} medium, {} low)'.format(
        sum(total.values()), total['HIGH'], total['MEDIUM'], total['LOW']))
    print('Source: reports/SECURITY_REPORT.md section 4')


if __name__ == '__main__':
    main()
