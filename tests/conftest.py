"""Test defaults for the local, credential-free simulator.

Set these before any test imports ``simulator.config`` so the suite never
depends on Docker, a real Redis, a scheduler, a core service or a chain node.
"""

import os

os.environ.setdefault('KYBER_ENV', 'simulation')
os.environ.setdefault('SIMULATOR_REDIS', 'fake')
os.environ.setdefault('SIMULATOR_OFFLINE', '1')
os.environ.setdefault('SIMULATOR_CLOCK', '1700000000000')
# Ten years, so a balance read does not trigger the deposit sweep.
os.environ.setdefault('SIMULATOR_DELAY_MS', str(10 * 365 * 24 * 3600 * 1000))
os.environ.setdefault('SIMULATOR_CHAIN_SEED', 'pytest')
