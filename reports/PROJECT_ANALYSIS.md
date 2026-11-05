# Project Analysis — Binance Security Incident Simulator (Educational Demo)

- **Status:** Phase 0 complete. Phase 1 baseline green, Phase 2 dashboard,
  Phase 3 replay and Phase 4 controls implemented. See
  `reports/PHASE1_BASELINE.md`, `reports/INCIDENT_TIMELINE.md`,
  `reports/SECURITY_REPORT.md` and `reports/TEST_RESULTS.json`.
- **Date:** 2026-11-05
- **Repository:** `/Users/admin/harness/binance-simulator`
- **Base commit:** `073d7dc` — `KyberNetwork/exchange-simulator` (last upstream commit 2018-03-06)
- **Working tree at analysis time:** only `.opencode/` and `MASTER_PROMPT.md` untracked; no source edits.
- **Purpose:** assess the existing exchange simulator, define the safety boundary, and
  turn the 4-minute demo script into an executable build and verification plan.

---

## 0. Executive summary

The repository is a working-in-2018 KyberNetwork centralized-exchange simulator. It
already has the right domain primitives for the demo: accounts keyed by API key,
available/locked balances in Redis, order matching against simulated order books,
deposit polling from a simulated chain, and a withdrawal path. It is **not runnable or
testable on this machine today**: the code targets Python 3.6, pins `ethereum==2.1.5`
and `pycoin==0.80`, hard-codes Docker service hostnames, and the baseline test run
produces **6 collection errors and executes 0 tests**.

The security story is unusually well matched to the real October 2026 incident. The
current `Exchange.withdraw` broadcasts the on-chain transfer **before** debiting the
internal balance, and the Binance-compatible API accepts any non-empty
`X-MBX-APIKEY` header. That gives the demo an honest, reproducible "unauthorized
withdrawal" analogue and a clear defensive fix: authorize, reserve/debit, then
broadcast; add limits, velocity checks, pause, revocation, idempotency and an
append-only audit trail.

The real incident was not a normal withdrawal-API bug. Binance's public report says
the attacker abused an **internal wallet signing service** and established malicious
**EIP-7702 authorizations** that moved assets outside the normal withdrawal flow. The
demo must say so explicitly and must not claim to replay the actual intrusion chain.

---

## 1. Safety and claim boundary

This project is an **independent educational simulator**. It is not affiliated with,
endorsed by, or connected to Binance. Every account, balance, key, address, token and
transaction is synthetic.

Hard rules carried from `MASTER_PROMPT.md`:

- Local environment only.
- Synthetic accounts and balances only.
- No real Binance credentials or API keys.
- No production exchange connection.
- No real wallets, private keys, or blockchain transactions.
- No implementation of real intrusion techniques or unauthorized access.
- Never fabricate test results or security findings.

The video and UI must show, at all times, a visible disclaimer such as:

> **INDEPENDENT EDUCATIONAL SIMULATOR — NOT BINANCE.**
> Synthetic data. No real funds. No real wallets. Not a reproduction of any
> organization's production systems.

---

## 2. Verified public facts vs. scenario assumptions

### 2.1 Verified public facts (as of 2026-11-05)

| Date | Fact | Source |
|---|---|---|
| 2026-10-29 ~20:05 UTC | Binance hot wallets were compromised; approximately **$6.3B** of token assets affected. | Binance Support, "Security Incident Update #2 (2026-10-30)" |
| 2026-10-30 | Withdrawals suspended; roughly **$3B** frozen on-chain; Binance stated it found **no evidence that wallet private keys were leaked**. | Same update |
| 2026-11-03 | Initial findings: unauthorized access to an **internal wallet signing service** was used to initiate transactions **outside the normal withdrawal process**; malicious **EIP-7702** authorizations were established; **50 signing transactions** manipulated the account nonce; **$6.34B** impacted and **$2.85B** frozen/intercepted. | Binance, "29 October 2026 Binance Security Incident: Initial Findings and Response Update" |
| 2026-10-29 23:56 UTC | Final unauthorized transfer of **2,961.9 ETH** finalized on-chain. | Same update |
| 2026-10-30 00:10 UTC | Binance cleared the EIP-7702 delegation code from the `Binance14` hot wallet. | Same update |
| 2026-11-03 | Binance reported 98% of impacted token assets replenished; FBI attributed the incident to the DPRK. | Binance blog / Square post, 2026-11-03 |

Sources:

- https://www.binance.com/en/support/announcement/d3306d9dca5243548c813b605e1d1751
- https://www.binance.com/en/blog/education/3229153443759566763
- https://x.com/binance/status/2117626126214504729

### 2.2 Hypothetical reconstruction used by this demo

The simulator is **not** a model of the real attack chain. The following are explicit
scenario assumptions, invented for teaching defensive engineering:

- A synthetic operations account with withdrawal permission is compromised.
- The compromise is represented only at the **authorization layer**: a stolen API key
  and a compromised signing/delegation grant. The demo does not model phishing,
  laptop compromise, or container deployment.
- Suspicious withdrawal requests are generated deterministically from a seed.
- The simulated chain has multiple ledgers/networks so the replay can show funds
  crossing more than one network.
- The incident is reconstructed at the **withdrawal-control boundary**, which is the
  part the existing repository actually implements.

Whenever the video or reports show a number, it must be labelled either
`PUBLIC FACT` (with the source above) or `SCENARIO` (synthetic). No blended numbers.

---

## 3. Repository inventory

```
binance-simulator/
├── binance_api.py              Flask API, Binance-compatible endpoints (port 5100)
├── bittrex_api.py              Flask API, Bittrex-compatible endpoints (port 5300)
├── liqui_api.py                Flask API, Liqui-compatible endpoints
├── poloniex_api.py             Flask API, Poloniex-compatible endpoints
├── bitfinex_api.py             Flask API, Bitfinex-compatible endpoints
├── config.yml                  dev / ropsten / kovan / simulation / production modes
├── Dockerfile                  python:3.6, installs requirements, no CMD
├── requirements.txt            pycoin, ethereum 2.1.5, Flask 0.12.2, redis 2.10.6, ...
├── setup_data.py               imports order books + seeds INITIAL_BALANCE
├── fake_dev_chain_wrapper.py   JSON-RPC proxy with a 5s confirmation delay
├── simulator/
│   ├── config.py               YAML config, tokens, fake keys, initial balances
│   ├── balance_handler.py      Redis hash balances + in-memory activity history
│   ├── order.py                Order value object
│   ├── order_handler.py        CoreOrder (HTTP core:8000) / SimulationOrder (Redis)
│   ├── utils.py                logging, Redis, timestamps, pending deposits
│   ├── web3_interface.py       Ethereum JSON-RPC: balances, withdraw, tx receipt
│   └── exchange/
│       ├── exchange.py         Exchange engine: balance, trade, deposits, withdraw
│       ├── binance.py          Binance response/request adapters
│       ├── bittrex.py          Bittrex adapter
│       ├── liqui.py            Liqui adapter
│       ├── bitfinex.py         Bitfinex adapter
│       └── poloniex.py         Poloniex adapter
├── tests/                      unit + API tests (several skipped or broken)
├── info/binance.json           236 symbols, rate-limit metadata (2018 snapshot)
├── info/bittrex.json           Bittrex market metadata
├── shared/deployment_*.json    13 tokens, 5 exchange addresses, bank/reserve
└── tools/orderbook-generator/  synthetic order-book generator + Redis loader
```

Dataset facts: `shared/deployment_dev.json` defines **13 tokens** (`ADX BAT CVC DGD
EOS ETH FUN GNT KNC LINK MCO OMG PAY`) and 5 exchange addresses. `info/binance.json`
contains **236 symbols** and rate limits (1200 requests/min, 10 orders/s, 100k
orders/day) that the current engine ignores.

---

## 4. Architecture

### 4.1 Layers

| Layer | Components | Responsibility |
|---|---|---|
| HTTP/API | `binance_api.py`, `bittrex_api.py`, variants | Route requests, check header presence, coerce timestamps, JSON responses |
| Exchange adapters | `simulator/exchange/*.py` | Map exchange-specific request/response shapes onto the core engine |
| Core engine | `simulator/exchange/exchange.py` | Balance reads, order placement/matching, deposit polling, withdrawal |
| State | `BalanceHandler`, `OrderHandler`, Redis | available/locked balances, orders, order books |
| Chain | `web3_interface.py`, `fake_dev_chain_wrapper.py` | Token balances, raw tx broadcast, receipt polling, confirmation delay |
| External services | `core:8000`, `scheduler:7000`, `redis:6379`, `blockchain:8545` | Prices/pending activities, simulated clock, state, chain RPC |

### 4.2 Expected runtime topology

The code assumes Docker Compose-style DNS names and has no compose file:

- `redis:6379` — balances, orders, imported order books (`utils.get_redis_db`).
- `core:8000` — `/prices/{base}/{quote}` and `/immediate-pending-activities`
  (`order_handler.py:48`, `utils.py:155`).
- `scheduler:7000` — `/get` simulated timestamp (`utils.py:59`).
- `blockchain:8545` — Ethereum JSON-RPC (`config.yml:5`, `web3_interface.py:31`).
- API process — `uwsgi --emperor *.ini`, Binance on `0.0.0.0:5100`.

### 4.3 Withdrawal data flow (current, security-critical)

```
client
  └─ POST /wapi/v3/withdraw.html
       └─ binance_api.withdraw
            └─ action(): require non-empty X-MBX-APIKEY        (auth = header presence)
                 └─ Binance.withdraw_api
                      └─ Exchange.withdraw(api_key, coin, address, amount)
                           ├─ 1. web3_interface.withdraw(...)  ← ON-CHAIN BROADCAST FIRST
                           │      └─ eth_getTransactionCount / eth_gasPrice / eth_sendRawTransaction
                           ├─ 2. BalanceHandler.withdraw(...)  ← DEBIT SECOND
                           │      └─ HINCRBYFLOAT; rollback only if new_value < 0
                           └─ 3. BalanceHandler.add_activity(...)  ← IN-MEMORY ONLY
```

Failure mode: if step 1 succeeds and step 2 raises `not enough ... balance`, the
tokens have already left the hot wallet while the internal ledger is unchanged. This
is the defect the demo will reproduce and fix. It is also the cleanest way to prove
the "rejected transaction cannot modify balance" requirement without simulating a
real intrusion.

### 4.4 Deposit data flow

```
Exchange.get_balance (or any authenticated call, throttled by DELAY)
  └─ Exchange._update_balance
       └─ Exchange.check_deposits(api_key)
            ├─ web3_interface.get_balances(deposit_address, tokens)
            ├─ if sum > 0: web3_interface.clear_deposits(...)
            ├─ utils.get_pending_tnx(exchange)  (HMAC-signed call to core:8000)
            └─ credit available balance + record deposit activity
```

### 4.5 Trading data flow

```
Binance.trade_api
  └─ Exchange.trade
       ├─ check_pair (base_eth only)
       ├─ BalanceHandler.lock (available -> lock)
       ├─ OrderHandler.load(pair, exchange, timestamp)
       │    ├─ CoreOrder: GET http://core:8000/prices/{base}/{quote}
       │    └─ SimulationOrder: GET redis {exchange}_{base}_{quote}_{timestamp}
       ├─ match against Asks/Bids
       └─ settle executed amounts, unlock remainder
```

Known limitation: `check_pair` only accepts `*_eth` pairs, while the Binance metadata
exposes 236 symbols (BTC/BNB/ETH/USDT quotes). The adapter is therefore a partial
shape-compatibility layer, not a full Binance clone.

---

## 5. Compatibility and environment findings

### 5.1 Phase 0 baseline result (superseded by Phase 1)

Phase 1 later replaced the legacy shims with a Python 3.12 local stack. The
current baseline is **41 passed, 14 skipped, 5 xfailed**; see
`reports/PHASE1_BASELINE.md`. The snapshot below is kept to document the
starting state.

Command:

```sh
cd /Users/admin/harness/binance-simulator
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 python3 -m pytest -q
```

Actual output (2026-11-05):

```text
ERROR tests/test_balance_handler.py
ERROR tests/test_binance_api.py        - TypeError: load() missing 1 required positional argument: 'Loader'
ERROR tests/test_bittrex_api.py        - TypeError: load() missing 1 required positional argument: 'Loader'
ERROR tests/test_simulator/test_exchange.py
ERROR tests/test_web3_interface.py     - ModuleNotFoundError: No module named 'pycoin'
ERROR tools/orderbook-generator/tests/test_orderBook.py
6 errors in 0.74s
```

No test executed, so there is **no green baseline**. Phase 1 must create one before
any security work begins.

Note: without `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1`, the system `web3` package's
pytest plugin crashes collection (`ImportError: cannot import name 'ContractName'
from 'eth_typing'`). The harness must set this variable for all local runs.

### 5.2 Issue matrix

| # | Issue | Evidence | Impact | Direction |
|---|---|---|---|---|
| C1 | Target runtime is Python 3.6 | `Dockerfile:1` | Not reproducible on this Mac (`python3` = 3.12.4) | Pin a supported interpreter or container |
| C2 | Ancient crypto dependencies | `requirements.txt:1-2` (`pycoin==0.80`, `ethereum==2.1.5`) | Not importable on 3.12; likely unbuildable | Replace `web3_interface` with a self-contained fake chain or a modern client |
| C3 | `yaml.load` without `Loader` | `simulator/config.py:32` | Import crashes under PyYAML >= 6 | `yaml.safe_load` |
| C4 | `PyYAML` missing from requirements | `requirements.txt` vs `config.py:8` | Fresh install cannot import config | Add pinned dependency |
| C5 | `flask_restful` missing | `fake_dev_chain_wrapper.py:8` | Fake-chain wrapper cannot run from requirements alone | Add it or remove the import |
| C6 | No Compose file / no CMD | `Dockerfile`, service names | Cannot start the multi-service stack | Add `compose.yaml` + healthchecks |
| C7 | Hard-coded service DNS | `utils.py:27` (`redis`), `utils.py:59` (`scheduler`), `utils.py:155` / `order_handler.py:48` (`core`), `config.yml:5` (`blockchain`) | Only works inside one specific network | Make configurable via env; local defaults |
| C8 | Order-book data is absent | `data/` is gitignored; `setup_data.py` expects `data/order_books/` | Simulation mode cannot trade | Generate deterministic seed data in-repo |
| C9 | Broken test fixture | `tests/test_simulator/test_exchange.py:29` uses `config.LIQUI_ADDRESS` (not defined); `Exchange` is called with 7 args but needs 8 | Collection/attribute errors | Fix the test contract before rewriting behavior |
| C10 | Missing mocked order books | `tests/test_bittrex_api.py` reads `tests/data/mocked_order_omg_eth.json` | Tests fail once Redis is up | Add fixtures |
| C11 | In-memory activity history | `balance_handler.py:11-14` | Restart loses withdrawal/deposit history; no evidence trail | Persist append-only log |
| C12 | Float money | `balance_handler.py:19,42-48` | Precision drift; 1e-8 epsilon hides it | Use `Decimal` or integer base units |
| C13 | No timeouts on several HTTP calls | `utils.py:59,161`; `order_handler.py:49` | Replay can hang | Set explicit timeouts |
| C14 | Secrets in source | `simulator/config.py:66-82` | Fake, but teaches the wrong pattern | Move to env; rotate; document as synthetic |

### 5.3 Environment snapshot

| Tool | Result |
|---|---|
| Python | 3.12.4 |
| Node | v22.0.0 |
| Docker | **not running** |
| Redis | **not running** |
| `uwsgi` | **not installed** |
| System `pytest` | 9.1.1 |
| Installed Python packages of note | `yaml`, `web3` present; `redis`, `pycoin`, `flask` absent |

Phase 1 is blocked on Docker (or an alternative local Redis) and on the Python 3.6
dependency problem. The recommendation in §9 is to modernize the integration shims
rather than resurrect the 2018 container verbatim.

---

## 6. Security-relevant findings in the current engine

Severity is relative to the demo, not a production audit.

| ID | Sev | Finding | Location | Demo use |
|---|---|---|---|---|
| S1 | **Critical** | On-chain transfer is broadcast before the internal balance is debited. An over-limit withdrawal can leave the wallet and still fail the ledger debit. | `simulator/exchange/exchange.py:234-250` (tx at 238, debit at 243) | Primary incident analogue and primary regression test |
| S2 | **Critical** | Authentication is "non-empty `X-MBX-APIKEY` header"; no signature, secret, scope, IP allowlist, or account binding. Any key creates a separate balance namespace. | `binance_api.py:44-49`; `MISSING_ERROR['api_key']` at 21-25 | "Compromised credential" is trivially replayable; fix = signed requests + scoped keys |
| S3 | High | No withdrawal authorization policy: no allowlist, per-transaction cap, daily cap, velocity limit, or new-address challenge. | `Exchange.withdraw`; `Binance.withdraw_api` (`binance.py:88-94`) | Add the controls the demo verifies |
| S4 | High | `canWithdraw: True`, `canDeposit: True`, `canTrade: True` are hard-coded; there is no pause/revocation state. | `simulator/exchange/binance.py:31-50` | Emergency pause and permission revocation demo |
| S5 | High | No idempotency key or replay protection. A repeated request creates another withdrawal and another random activity. | `Exchange.withdraw`; `BalanceHandler.add_activity` | Duplicate-submission test |
| S6 | High | No anomaly detection: amount, destination, frequency, and network are not scored. | `Exchange.withdraw` | "Suspicious request" replay |
| S7 | Medium | Activity history is an in-memory dict; it disappears on restart and is not append-only. | `balance_handler.py:11-14,61-67` | Replace with hash-chained `AUDIT_LOG.jsonl` |
| S8 | Medium | Float balances with a `1e-8` epsilon. | `balance_handler.py:19,42-48` | Precision regression; move to `Decimal`/base units |
| S9 | Medium | Secrets and real-looking keys are committed. | `simulator/config.py:66-82` | Treat as synthetic; move to env and document |
| S10 | Medium | Errors return HTTP 200 with `{"code": -1, "msg": ...}` and are not audited. | `binance_api.py:54-59` | Audit rejected attempts too |
| S11 | Low | Rate-limit metadata exists in `info/binance.json` but is not enforced. | `info/binance.json` `rateLimits` | Add 429 + audit |
| S12 | Low | Reading a balance can trigger deposit polling (side effect inside `_update_balance`). | `simulator/exchange/exchange.py:28-44` | Keep, but make it explicit and timed |
| S13 | Low | `exchange.withdraw` does not validate the destination address. | `exchange.py:234-250` | Add allowlist/format validation |

The key insight for the video: **S1 is real, reachable, and testable without any
attack**. The replay can say "this is the class of bug that makes an unauthorized
withdrawal possible" while never pretending to reproduce Binance's actual signing-service
compromise.

---

## 7. Test inventory and gaps

| File | Current state | Needs | Value |
|---|---|---|---|
| `tests/test_balance_handler.py` | Collects, but requires live Redis at `redis:6379` | Redis or fakeredis; config import fix | Good rollback coverage (excess withdrawal, full withdrawal epsilon) |
| `tests/test_binance_api.py` | Collects, fails on config import | Redis, config fix, order-book stub | API shape + mocked withdraw |
| `tests/test_bittrex_api.py` | Collects, fails on config import + missing fixtures | Redis, fixtures | Adapter coverage |
| `tests/test_simulator/test_exchange.py` | Broken (`config.LIQUI_ADDRESS`, signature) | Rewrite fixture | Core engine trade tests |
| `tests/test_exchange.py` | Entirely `@unittest.skip` | Delete or replace | No current signal |
| `tests/test_web3_interface.py` | `@unittest.skip` | Replace by fake-chain tests | No current signal |
| `tests/test_liqui_api.py` | `@unittest.skip` | Delete or replace | No current signal |
| `tools/orderbook-generator/tests/test_orderBook.py` | Collection import error (`tests.test_orderBook`) | Package path fix | Generator coverage |

Missing coverage that the demo must add:

1. Withdrawal rejected **before** any chain broadcast.
2. Rejected withdrawal leaves `available` and `lock` unchanged.
3. Duplicate idempotency key produces one transfer.
4. Per-transaction and daily limits enforced.
5. Velocity limit enforced.
6. New-address / allowlist policy enforced.
7. Emergency pause blocks every withdrawal path.
8. Revoked key/delegation is rejected and audited.
9. Audit log is append-only and its hash chain verifies.
10. Deterministic replay: same seed -> identical timeline hash.

---

## 8. Mapping to the 4-minute video

| Time | Beat | On screen | Evidence artifact |
|---|---|---|---|
| 00:00-00:40 | Opening: the October 2026 incident | Title card, labelled public facts, repo tree | `reports/PROJECT_ANALYSIS.md` §2, source URLs on screen |
| 00:40-01:30 | Harness starts | Agent reads the withdrawal flow, writes the plan and test list | `.space/tasks.md`, plan diff, `reports/PROJECT_ANALYSIS.md` |
| 01:30-02:40 | Reconstruct in the simulator | Deterministic replay: compromised grant, anomalous withdrawal, multi-ledger movement, alerts | `reports/INCIDENT_TIMELINE.md`, replay JSONL, dashboard |
| 02:40-03:30 | Independent verification | Red test -> fix -> green test; rejected transaction does not change balance; real logs | `reports/TEST_RESULTS.json`, `AUDIT_LOG.jsonl`, terminal output |
| 03:30-04:00 | Final result | Markdown report, test summary, changed files, automation conclusion | `reports/SECURITY_REPORT.md`, `README.md`, `git diff --stat` |

Production notes:

- Every on-screen number must carry `PUBLIC FACT` or `SCENARIO`.
- The replay must be driven by a seed and print the seed on screen.
- The "blocked" proof must show both the API response and the unchanged ledger
  snapshot, not just a green test.
- The video must never show a real domain, real wallet address, or real credential.
- The disclaimer must be visible in the opening and closing frames.

---

## 9. Recommended build path

### Decision: modernize the integration shims, preserve the engine

Two options were considered:

- **Option A — resurrect the 2018 stack.** Docker `python:3.6`, old `ethereum`/`pycoin`,
  a fake RPC, Redis, `core` and `scheduler` stubs. Highest historical fidelity, but
  fragile, slow, and hard to test on this machine.
- **Option B — port the integration shims to Python 3.12 and keep the domain code.**
  Preserve `Exchange`, `BalanceHandler`, `OrderHandler`, `Order`, and the adapter
  shapes. Replace `web3_interface` with an in-process `FakeChain`, make Redis optional
  (`fakeredis` for tests, real Redis for the demo), and generate deterministic order
  books. Recommended.

Option B keeps the master prompt's "do not create a new exchange from scratch" rule:
the domain engine and API adapters remain the original ones. Only the environment
boundary changes.

### Phase 1 — environment and green baseline

1. Create a dedicated branch (`demo/binance-incident`).
2. Create `.venv` with Python 3.12 and pinned modern deps (`Flask`, `redis`,
   `PyYAML`, `pytest`, `fakeredis`).
3. Replace `yaml.load` with `safe_load`; add `PyYAML` and `flask_restful` to
   requirements (or remove the latter import).
4. Add a deterministic `FakeChain` with token balances, tx broadcast, receipt, and
   confirmation delay. No network, no real keys.
5. Add `seed.py` to create synthetic accounts, balances, order books, and the
   operations account.
6. Fix test fixtures and make the suite runnable.
7. Gate: `pytest` green; `GET /ping`, `/api/v1/exchangeInfo`, `/api/v3/account`,
   `/api/v1/depth`, `/api/v3/order`, `/wapi/v3/withdraw.html` return valid shapes.

### Phase 2 — branding and dashboard

- Dark exchange dashboard served by Flask; no external CDN.
- Balances, pairs, order book, transaction history, security banner.
- Persistent "EDUCATIONAL SIMULATOR — NOT BINANCE" disclaimer.
- Preserve the engine; the dashboard is a read/write client of the existing API.

### Phase 3 — deterministic incident reconstruction

- Seed-driven scenario file.
- Synthetic operations account with a scoped withdrawal grant.
- Events: grant misuse, anomalous request, multi-ledger movement, alerts,
  containment, revocation.
- Separate `PUBLIC FACT` and `SCENARIO` labels in the timeline.
- Gate: same seed -> same event hash; no real network calls.

### Phase 4 — defensive controls

Implement in this order, each with a failing test first:

1. **Reserve then broadcast**: debit/reserve before `FakeChain.withdraw`; release on
   failure. Fixes S1.
2. **Authorization**: signed request or scoped key; bind key to account and permissions.
3. **Limits**: per-transaction, daily, and velocity; new-address challenge.
4. **Anomaly detection**: amount deviation, destination novelty, frequency.
5. **Emergency pause**: global and per-asset.
6. **Revocation**: revoke key/grant; in-flight requests fail closed.
7. **Idempotency**: one transfer per key.
8. **Append-only audit**: JSONL with hash chain, including rejected attempts.
9. **Precision**: Decimal or integer base units.

### Phase 5 — verification

- Original tests (fixed) + new security tests + integration tests.
- Balance invariant: sum(available) + sum(lock) is unchanged by a rejected request.
- Chain invariant: a rejected request produces zero broadcast transactions.
- Independent review with a separate agent/lane.
- Record actual output in `reports/TEST_RESULTS.json`; never hand-write results.

### Phase 6 — harness workflow evidence

- `.space/tasks.md` contract with one task per control.
- `.space/run.json` from a real `oc-harness work` / `resume` run.
- Do not claim resume/recovery unless a real interrupted run is shown.

### Phase 7 — delivery

- `PROJECT_ANALYSIS.md` (this file)
- `INCIDENT_TIMELINE.md`
- `SECURITY_REPORT.md`
- `TEST_RESULTS.json`
- `AUDIT_LOG.jsonl`
- `README.md`
- Exact reproduction commands.

---

## 10. Measurable acceptance gates

| Gate | Proof |
|---|---|
| G1 | Clean install starts the API and serves all documented endpoints |
| G2 | `pytest` executes > 0 tests and exits 0 |
| G3 | Replay with the same seed produces the same timeline hash |
| G4 | Rejected withdrawal: API returns rejection, ledger snapshot unchanged, `FakeChain` broadcast count unchanged |
| G5 | Emergency pause blocks all withdrawal paths |
| G6 | Revoked key/grant is rejected and audited |
| G7 | Idempotency key produces exactly one transfer |
| G8 | Audit log hash chain verifies after append |
| G9 | Independent review verdict is recorded |
| G10 | Video shows real terminal output, real test counts, real report files |

---

## 11. Risks and open decisions

| Risk | Impact | Mitigation |
|---|---|---|
| Legacy dependencies are unbuildable | Blocks Phase 1 | Option B (modern shims) |
| Docker/Redis not running | Blocks the demo stack | Start Docker; or use `fakeredis` for tests and a local Redis for the dashboard |
| Scope of 4-minute video is large | Slips delivery | Build the 5 beats as separate artifacts; record only after G1-G8 are green |
| Binance trademark | Legal/ethical | Independent name, visible disclaimer, no official logo use |
| Factual overreach | Credibility | Label every fact; cite sources; state the reconstruction is an analogue |
| Token budget | Cost | One task per session; use `/handoff`; keep logs narrow |
| Video shows synthetic data as real | Ethical failure | On-screen labels and a spoken disclaimer |

Open decisions for the user:

1. Approve Option B (modernize shims) vs. Option A (legacy container).
2. Confirm the display name and whether "BINANCE SIMULATOR" may appear in the UI.
3. Confirm the fake incident numbers (synthetic only) or use relative values
   (`100%`, `> limit`) to avoid confusion with the real $6.34B.
4. Confirm the video language (Vietnamese voiceover with English UI, or all English).

---

## 12. Immediate next command

Phase 1 is complete. The command below is kept as the historical bootstrap
record; the next active step is Phase 2 (dashboard) or the Phase 4 red test.

Phase 1, step 1-2 only (no behaviour change):

```sh
cd /Users/admin/harness/binance-simulator
git checkout -b demo/binance-incident
python3 -m venv .venv
.venv/bin/pip install -U pip
.venv/bin/pip install 'Flask>=3,<4' 'redis>=5,<6' 'PyYAML>=6,<7' 'pytest>=8,<9' 'fakeredis>=2,<3'
```

Then the first red test must be written against the **current** behaviour:

```text
test_withdraw_over_limit_must_not_broadcast
```

It should fail on `Exchange.withdraw` because the chain call happens before the
balance check. Only after that red test exists may S1 be fixed.

---

## Appendix A — Source-of-truth files

- Requirements and scope: `MASTER_PROMPT.md`
- Video beats: user brief, 2026-11-05
- Public incident facts: Binance Support 2026-10-30 and Binance blog 2026-11-03
- Engine: `simulator/exchange/exchange.py`, `simulator/balance_handler.py`,
  `simulator/order_handler.py`, `simulator/web3_interface.py`
- API: `binance_api.py`, `simulator/exchange/binance.py`

## Appendix B — Analysis commands actually run

```sh
git status --short
git log --oneline -10
python3 --version
node --version
docker info
redis-cli ping
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 python3 -m pytest -q
python3 -c "import simulator.config"
python3 -c "import simulator.exchange"
```

Observed results are recorded in §5.1 and §5.3. No test result in this report is
inferred or fabricated.
