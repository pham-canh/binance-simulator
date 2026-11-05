#!/usr/bin/env python3
"""Terminal board for the four video lanes."""

LANES = [
    ('1', 'BUILDER   (GPT-class)', 'threat model + failing red test',
     'tests/test_withdraw_atomicity.py', 'RED  0 != 1'),
    ('2', 'REVIEWER  (Gemini-class)', 'independent security review',
     'reports/SECURITY_REPORT.md', '14 findings fixed'),
    ('3', 'FIXER     (Claude-class)', 'fix withdraw ordering',
     'simulator/exchange/exchange.py', 'FIXED  no broadcast'),
    ('4', 'VERIFIER  (DeepSeek)', 'replay + full gate',
     'reports/TEST_RESULTS.json', '56 passed / 10 API'),
]


def main():
    print('AGENT LANES  -  one role, one job')
    print('=' * 78)
    print('{:<3} {:<22} {:<34} {}'.format('#', 'LANE', 'TASK', 'RESULT'))
    print('-' * 78)
    for number, lane, task, artifact, result in LANES:
        print('{:<3} {:<22} {:<34} {}'.format(number, lane, task, result))
        print('    artifact: {}'.format(artifact))
    print('=' * 78)
    print('Gate: every lane artifact is checked before the next lane.')
    print('Class labels are routing roles; the artifacts are the real output.')


if __name__ == '__main__':
    main()
