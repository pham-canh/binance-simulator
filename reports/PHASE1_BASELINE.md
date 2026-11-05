# Phase 1 Baseline — Local Fake-Data Environment

- **Date:** 2026-11-05
- **Branch:** `demo/binance-incident`
- **Base:** `073d7dc` (`KyberNetwork/exchange-simulator`)
- **Decision:** Option B — keep the original domain engine, port the integration
  shims to Python 3.12, and run with fakeredis + an in-process `FakeChain`.
- **Result:** **41 passed, 14 skipped, 5 xfailed**; live HTTP API verification
  **10/10 checks ok**.

This phase does not fix the security defect (S1). It creates a reproducible,
credential-free baseline so the red regression test in Phase 4 is meaningful.

> **Historical note (Phase 4):** S1 is now fixed. The pre-fix evidence in
> Section 5 is kept unchanged; the post-fix proof is
> `reports/evidence/phase4-s1-fixed.json` and the current gate is
> `.venv/bin/python scripts/verify_all.py`. See `reports/SECURITY_REPORT.md`.

---

## 1. Environment

| Item | Value |
|---|---|
| Python | 3.12.4 (`.venv`) |
| Flask | 3.1.3 |
| redis-py | 5.3.1 |
| fakeredis | 2.40.0 |
| PyYAML | 6.x |
| pytest | 8.4.2 |
| requests | 2.31+ |
| Docker / real Redis / uwsgi | not required for this baseline |
| Chain | `simulator/fake_chain.py` (in-process, deterministic) |

Bootstrap:

```sh
cd /Users/admin/harness/binance-simulator
bash scripts/bootstrap.sh
```

`scripts/bootstrap.sh` creates `.venv` and installs
`requirements-local.txt`. The legacy `requirements.txt` is untouched so the
2018 Docker path remains available for reference.

---

## 2. Changes in this phase

| File | Change | Why |
|---|---|---|
| `simulator/config.py` | `yaml.safe_load`; repo-relative config/address paths; env overrides for delay and chain URL | PyYAML >= 6 compatibility; run from any CWD |
| `simulator/utils.py` | Redis handle from `SIMULATOR_REDIS` / `REDIS_HOST`; `fakeredis` support; fixed clock; offline pending-tx switch; HTTP timeouts | Remove Docker DNS assumptions; deterministic tests |
| `simulator/web3_interface.py` | Delegates to `FakeChain`; same function names | Remove uninstallable pycoin/ethereum and real RPC |
| `simulator/fake_chain.py` | New deterministic ledger: hot wallet, pending deposits, tx hashes, broadcast count | Credential-free chain for tests and demo |
| `simulator/order_handler.py` | 2 s timeout on the core call | No indefinite hangs |
| `setup_data.py` | Redis flag written as `'1'` | redis-py 5 rejects `bool` |
| `tests/conftest.py` | Sets `simulation`, fake Redis, fixed clock, offline flags | Tests never touch the network |
| `pytest.ini` | `testpaths = tests` | Exclude the unrelated order-book generator test |
| `tests/data/*.json` | Deterministic mocked order books | The original tests referenced missing files |
| `tests/test_simulator/test_exchange.py` | Correct constructor args + fixture path | The original used a non-existent `config.LIQUI_ADDRESS` |
| `tests/test_binance_api.py`, `tests/test_bittrex_api.py` | Enough synthetic balance; withdraw mock returns an object | The original tests could not pass in sequence |
| `requirements-local.txt`, `scripts/` | Reproducible local stack and checks | Phase 1 deliverable |

No change was made to `Exchange.withdraw`, `BalanceHandler.withdraw`, the
Binance route contract, or the order/trade semantics.

---

## 3. Test evidence

Command:

```sh
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 .venv/bin/python -m pytest -o addopts='' -q
```

Actual output (saved in `reports/evidence/phase1-pytest.txt`):

```text
...................................sssssssssssssxxxx......xs             [100%]
41 passed, 14 skipped, 5 xfailed in 0.64s
```

Notes:

- The 14 skips are the original upstream `@unittest.skip` tests
  (`test_exchange.py`, `test_liqui_api.py`, `test_web3_interface.py`). They are
  recorded as skips, not silently deleted.
- The 5 xfails are the original `@unittest.expectedFailure` cases in
  `tests/test_simulator/test_exchange.py`.
- `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1` protects against a broken global `web3`
  pytest plugin; inside `.venv` it is not required but is safe.

Before this phase the same repository produced **6 collection errors and ran 0
tests** (see `PROJECT_ANALYSIS.md` §5.1). The baseline is now real.

---

## 4. Live HTTP API evidence

Command:

```sh
.venv/bin/python scripts/verify_phase1.py
```

The script starts `scripts/run_demo_server.py`, waits for `/ping`, exercises the
real endpoints, and terminates the server. Actual output is saved in
`reports/evidence/phase1-api.json`; the server log is
`reports/evidence/phase1-server.log`.

| Check | Observed |
|---|---|
| `GET /ping` | `pong` |
| `GET /api/v1/exchangeInfo` | timezone `UTC`, **236 symbols** |
| `GET /api/v3/account` | `canWithdraw: true`, **13 assets**, OMG free `1000.0` |
| `GET /api/v1/depth?symbol=OMGETH` | one ask and one bid at `0.003 x 1000` |
| `POST /api/v3/order` (resting sell) | order accepted with `orderId` |
| `GET /api/v3/openOrders` | 1 open order |
| `DELETE /api/v3/order` | canceled with the same `orderId` |
| `POST /api/v3/order` (marketable sell) | order accepted and filled |
| `POST /wapi/v3/withdraw.html` | `success: true`, activity `id` returned |
| `GET /wapi/v3/withdrawHistory.html` | 1 withdrawal with a fake `txId` |

The fake transaction hash is deterministic for the fixed seed, which is what the
incident replay needs.

Run the server manually:

```sh
.venv/bin/python scripts/run_demo_server.py
# then:
curl -s http://127.0.0.1:5100/ping
curl -s -H 'X-MBX-APIKEY: demo-user' http://127.0.0.1:5100/api/v3/account
```

The demo account is synthetic: `X-MBX-APIKEY: demo-user`. The server prints the
synthetic hot-wallet address on startup. No real key, wallet, or endpoint is
used.

---

## 5. Pre-fix security evidence (S1)

The Phase 0 analysis identified S1: `Exchange.withdraw` broadcasts the chain
transfer before debiting the internal balance. This phase records the "before"
state without fixing it.

Command:

```sh
.venv/bin/python scripts/show_s1.py
```

Actual output (saved in `reports/evidence/phase1-s1.json`):

```json
{
  "api_response": {"code": -1, "msg": "not enough 999999.0 omg in available balance"},
  "balance_before": 10.0,
  "balance_after": 10.0,
  "broadcasts_before": 0,
  "broadcasts_after": 1
}
```

Interpretation: the API correctly rejected the debit and the internal balance
was unchanged, but a withdrawal transaction was already broadcast to the
simulated chain. This is the defect the Phase 4 red test must lock down:

```text
test_withdraw_over_limit_must_not_broadcast
```

The fix order is: write the failing test, then reserve/debit before broadcast,
then make the test green.

---

## 6. Known limitations

- `fakeredis` is in-process: state is shared within one process, not across
  processes. The demo server and its verification script each own their state.
- The fake chain models balances, pending deposits, and broadcasts; it does not
  model gas, nonces, confirmations, or EIP-7702 delegation. Those are Phase 3
  and Phase 4 scenario features.
- The order book is a single seeded level at a fixed clock. Phase 2/3 will add a
  richer deterministic book for the dashboard and replay.
- The 2018 `requirements.txt` and `Dockerfile` are not used by this path and
  remain unmodified.
- S1 remains present until Phase 4. Do not record the "blocked" proof yet.

---

## 7. Next phase

1. **Phase 2 — branding + dashboard.** Serve a dark dashboard from
   `scripts/run_demo_server.py`, show balances/order book/history, and keep the
   "INDEPENDENT EDUCATIONAL SIMULATOR — NOT BINANCE" banner visible.
2. **Phase 4 red test (before any control code).**
   `test_withdraw_over_limit_must_not_broadcast` must fail on the current
   ordering.
3. **Phase 3 — deterministic incident replay.** Extend `FakeChain` with the
   synthetic delegation/authorization model and label every event
   `PUBLIC FACT` or `SCENARIO`.

Reproduce this baseline with:

```sh
cd /Users/admin/harness/binance-simulator
bash scripts/bootstrap.sh
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 .venv/bin/python -m pytest -o addopts='' -q
.venv/bin/python scripts/verify_phase1.py
.venv/bin/python scripts/show_s1.py
```
