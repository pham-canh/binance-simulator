#!/usr/bin/env python3
"""Small terminal title/end cards used by the demo recording."""

import sys

TITLE = r"""
  ___  _                            _   ____  _                 _
 | __ )(_)_ __   __ _ _ __   ___ ___ / |/ ___|(_)_ __ ___  _   _| | __ _| |_ ___
 |  _ \| | '_ \ / _` | '_ \ / __/ _ \| |\___ \| | '_ ` _ \| | | | |/ _` | __/ _ \
 | |_) | | | | | (_| | | | | (_|  __/| | ___) | | | | | | | |_| | | (_| | ||  __/
 |____/|_|_| |_|\__,_|_| |_|\___\___||_||____/|_|_| |_| |_|\__,_|_|\__,_|\__\___|
"""

DISCLAIMER = (
    'INDEPENDENT EDUCATIONAL SIMULATOR - NOT BINANCE. '
    'Synthetic data, synthetic accounts, in-process fake chain. '
    'No real funds, wallets, keys or blockchain calls.')

END = """
  RESULT
  ------
  56 passed, 14 skipped, 5 xfailed
  10/10 live API checks
  14 findings fixed, each with a regression test
  rejected withdrawal: 0 broadcasts, balance unchanged
  audit chain: valid

  BINANCE SIMULATOR - Educational Demo
  INDEPENDENT. SYNTHETIC. LOCAL. NOT BINANCE.
"""


def main():
    if '--end' in sys.argv:
        print(END)
        return
    print(TITLE)
    print('  SECURITY INCIDENT SIMULATOR - EDUCATIONAL DEMO')
    print('  ' + '-' * 76)
    print('  ' + DISCLAIMER)
    print()
    print('  PUBLIC FACT  2026-10-29  hot wallets compromised, ~$6.3B affected')
    print('  PUBLIC FACT  2026-11-03  internal signing service + EIP-7702,')
    print('                          $6.34B impacted, $2.85B frozen')
    print()
    print('  SCENARIO     withdrawal-control analogue, not the real intrusion')


if __name__ == '__main__':
    main()
