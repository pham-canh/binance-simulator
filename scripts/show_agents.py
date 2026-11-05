#!/usr/bin/env python3
"""Terminal board for the four video lanes."""

LANES = [
    ('1', 'chatgpt', 'build threat model and red test',
     'tests/test_withdraw_atomicity.py', 'RED  0 != 1'),
    ('2', 'gemini', 'independent security review',
     'reports/SECURITY_REPORT.md', '4 findings fixed'),
    ('3', 'claude-class', 'fix withdraw ordering',
     'simulator/exchange/exchange.py', 'FIXED  no broadcast'),
    ('4', 'deepseek', 'replay and full gate',
     'reports/TEST_RESULTS.json', '56 passed / 10 API'),
]


def main():
    print('AGENT LANES  -  one model, one job')
    print('=' * 78)
    print('{:<3} {:<22} {:<34} {}'.format('#', 'LANE', 'TASK', 'RESULT'))
    print('-' * 78)
    for number, lane, task, artifact, result in LANES:
        print('{:<3} {:<22} {:<34} {}'.format(number, lane, task, result))
        print('    artifact: {}'.format(artifact))
    print('=' * 78)
    print('Gate: every lane artifact is checked by the take before the next lane.')


if __name__ == '__main__':
    main()
