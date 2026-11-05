#!/usr/bin/env python3
"""Compact review findings for the video."""

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
    print('Source: reports/SECURITY_REPORT.md section 4')


if __name__ == '__main__':
    main()
