"""Chain shim for the educational simulator.

The original module signed Ethereum transactions with pycoin/ethereum and spoke
JSON-RPC to a node. That stack is not installable on modern Python and would
require a real node. This shim keeps the same function names but delegates to
``simulator.fake_chain.FakeChain``: a deterministic, in-process ledger.

There are no private keys, no network calls, and no real asset movements here.
"""

from . import config
from . import fake_chain
from . import utils as simulation_utils

logger = simulation_utils.get_logger()


def get_balances(exchange_address, tokens):
    """Return pending deposits for each token, in base units."""
    return fake_chain.get_chain().get_balances(exchange_address, tokens)


def clear_deposits(key, exchange_address, token_array, amounts):
    """Clear the synthetic pending deposits and return a fake tx hash."""
    return fake_chain.get_chain().clear_deposits(
        key, exchange_address, token_array, amounts)


def withdraw(key, exchange_address, token, amount, destination):
    """Debit the simulated hot wallet and return a fake tx hash."""
    return fake_chain.get_chain().withdraw(
        key, exchange_address, token, amount, destination)


def is_tx_confirmed(tx_hash):
    return fake_chain.get_chain().is_tx_confirmed(tx_hash)


def wait_for_tx_confirmation(tx_hash):
    return fake_chain.get_chain().wait_for_tx_confirmation(tx_hash)


def to_hex_address(integer):
    return '%040x' % integer


def get_test_private_key(index):
    """Kept for API compatibility; never used to sign anything."""
    return 'synthetic-key-{}'.format(index)


def post():
    """The original delay switch has no meaning for the in-process ledger."""
    return None


def seed_demo_chain():
    return fake_chain.seed_demo_chain()


def simulate_deposit(exchange_address, token_name, amount):
    return fake_chain.simulate_deposit(exchange_address, token_name, amount)


def transaction_snapshot():
    return fake_chain.get_chain().snapshot()
