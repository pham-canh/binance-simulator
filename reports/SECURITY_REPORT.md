# Security Report — Withdrawal Controls

- **Date:** 2026-11-05
- **Branch:** `demo/binance-incident`
- **Scope:** `simulator/security.py`, `simulator/exchange/exchange.py`,
  `simulator/exchange/binance.py`, `simulator/incident.py`,
  `simulator/dashboard.py`, `binance_api.py`, `tests/`
- **Result:** 56 passed, 14 skipped, 5 xfailed; live API 10/10; replay and
  audit-chain gates green. See `reports/TEST_RESULTS.json`.

This is an independent educational simulator. All accounts, balances, keys,
addresses, tokens and transactions are synthetic. No real Binance credential,
wallet, endpoint, node or asset is used.

---

## 1. Finding S1 — broadcast before debit

### Root cause

The original `Exchange.withdraw` called the chain shim first and debited the
internal balance second:

```python
tx = web3_interface.withdraw(...)          # broadcast first
self.balance.withdraw(...)                 # rejects afterwards
```

If the debit failed, the API returned an error but a transfer had already been
broadcast. The pre-fix evidence is kept in
`reports/evidence/phase1-s1.json`:

```json
{
  "api_response": {"code": -1, "msg": "not enough 999999.0 omg in available balance"},
  "balance_before": 10.0,
  "balance_after": 10.0,
  "broadcasts_before": 0,
  "broadcasts_after": 1
}
```

### Fix

`Exchange.withdraw` now runs, in order:

1. validate the token and amount;
2. take a per-user withdrawal lock;
3. return the prior activity for a repeated idempotency key;
4. authorize through the guard (pause, revocation, limits, velocity,
   untrusted-address checks);
5. debit the internal available balance — the gate;
6. broadcast to the in-process fake chain;
7. refund the internal debit if the chain shim raises before broadcasting;
8. write the activity and commit limits/idempotency/audit.

Post-fix evidence is in `reports/evidence/phase4-s1-fixed.json`:
request rejected, balance `10 → 10`, broadcasts `0 → 0`.

The regression tests are:

- `tests/test_withdraw_atomicity.py::test_withdraw_over_limit_must_not_broadcast`
  — the pre-fix red test (`0 != 1` before the fix).
- `tests/test_withdraw_atomicity.py::test_insufficient_balance_must_not_broadcast`
  — amount inside policy limits, only the debit can reject it. This test would
  still fail if broadcast-before-debit were reintroduced.

## 2. Controls

| Control | Implementation | Test |
|---|---|---|
| Authorization | Per-user API key, allowlist, revocation | `test_revoked_permission_blocks_until_regranted` |
| Single-withdrawal limit | Per-asset, default 1000, OMG 500, ETH 10 | `test_single_withdrawal_limit_blocks_before_broadcast` |
| Daily limit | Per user **and per asset**, fixed UTC day | `test_daily_limit_blocks_after_accumulated_withdrawals`, `test_daily_limit_is_scoped_per_asset` |
| Velocity limit | 3 withdrawals / 60 s window | `test_velocity_limit_blocks_rapid_requests` |
| Emergency pause | Global or per-user; blocks before debit | `test_emergency_pause_blocks_and_resume_restores` |
| Permission revocation | Deny until explicitly re-granted | `test_revoked_permission_blocks_until_regranted` |
| Anomaly detection | New address alert ≥100; hard block ≥500 | `test_untrusted_address_is_alerted_and_blocked_for_large_amounts` |
| Idempotency | Key scoped `(user, asset, key)`; per-user lock | `test_idempotency_key_prevents_double_broadcast`, `test_idempotency_key_is_scoped_per_asset`, `test_concurrent_same_key_broadcasts_once` |
| Chain-failure refund | Debit restored if the chain shim raises | `test_chain_failure_refunds_the_internal_debit` |
| Audit trail | SHA-256 hash chain; optional JSONL export | `test_audit_chain_detects_tampering` |
| Input hardening | Reject NaN/non-finite, non-positive and empty addresses | `test_destination_address_is_required`, balance-handler tests |

The live API exposes the state through `/api/v1/simulator/status` and reports
`canWithdraw: false` when the synthetic operator is paused or revoked.

## 3. Verification

Commands:

```sh
cd /Users/admin/harness/binance-simulator
bash scripts/bootstrap.sh
.venv/bin/python scripts/verify_all.py
```

Observed:

| Gate | Result |
|---|---|
| `pytest` | **56 passed, 14 skipped, 5 xfailed** |
| Live HTTP API | **10/10 checks**, `status: ok` |
| Incident replay | 16 events, 5 public facts, 1 broadcast, audit valid |
| Audit file | 11 records, hash chain valid |
| Withdrawal ordering | rejected request, broadcasts unchanged |
| Dashboard | HTTP 200, all disclaimer markers present |

Evidence files:

- `reports/evidence/phase5-pytest.txt`
- `reports/evidence/phase1-api.json`
- `reports/evidence/phase3-replay.json`
- `reports/evidence/phase4-s1-fixed.json`
- `reports/evidence/phase1-s1.json` (historical pre-fix)
- `reports/AUDIT_LOG.jsonl`
- `reports/TEST_RESULTS.json`

## 4. Independent review

A separate review agent examined the changed files after the first green run.
Concrete findings and their disposition:

| Severity | Finding | Status |
|---|---|---|
| BLOCKER | Concurrent same-key requests could both broadcast | Fixed: per-user lock around the whole withdraw flow; concurrent test added |
| HIGH | Idempotency key was not asset-scoped (OMG key could replay an ETH request) | Fixed: key is `(user, asset, key)`; test added |
| HIGH | Audit verifier accepted empty lists and did not check sequence/truncation | Fixed: contiguous `seq`, optional expected count/head, file read-back gate; truncation still needs an external anchor (see limitations) |
| HIGH | Audit-file write failure could report a successful withdrawal as failed | Fixed: optional file append is non-fatal; in-memory chain remains authoritative |
| HIGH | Any non-empty API key selected a new identity | Fixed: synthetic key allowlist (`demo-user`, `ops-demo`, test key), configurable via `SIMULATOR_API_KEYS` |
| HIGH | Committed values looked like real secrets | Fixed: replaced with clearly synthetic placeholders; no request uses them |
| HIGH | Revocation attempt was masked by the active pause | Fixed: replay resumes before revoking; evidence shows `-9002` |
| HIGH | Ordering test used an amount rejected by policy, so it did not prove the debit gate | Fixed: added an inside-limit insufficient-balance test |
| MEDIUM | Daily limit mixed assets | Fixed: keyed by asset |
| MEDIUM | NaN and empty address could pass checks | Fixed: finite check and required address (`-9007`) |
| MEDIUM | `debug=True` on `0.0.0.0` in direct `binance_api.py` run | Fixed: `127.0.0.1`, `debug=False` |
| MEDIUM | Simulation timestamp could call a scheduler without a fixed clock | Fixed: `SIMULATOR_OFFLINE` now gates the scheduler call |
| MEDIUM | `.json` evidence contained a log line | Fixed: logging disabled in the evidence script; historical file cleaned |
| LOW | Guard state leaked between test modules | Fixed: `reset_guard()` in the atomicity `setUp` |

## 5. Known limitations

- **Single process.** Pause, revocation, limits, idempotency and the audit chain
  live in process memory. The demo is intended for one local server process;
  multiple workers would not share state.
- **Synthetic authorization.** The API key is an allowlisted tenant string,
  not a signed credential. It demonstrates the control boundary, not real
  authentication.
- **Audit truncation.** The hash chain detects modification and reordering.
  Detecting deletion of the newest records requires an external anchor; the
  verification gate checks the whole file but does not have a remote head.
- **Float balances.** The original engine uses floating-point Redis values.
  Limits are demonstration controls, not accounting-grade.
- **HTTP semantics.** Rejected withdrawals return the original Binance-style
  `{"code": -1, "msg": ...}` body with HTTP 200. A production monitor should
  use the body, not only the status code.
- **Real incident not reproduced.** The public incident involved an internal
  signing service and EIP-7702 delegations. This simulator is an analogue at
  the withdrawal-control boundary.

## 6. Safety statement

- Local only: `127.0.0.1`.
- No real Binance credentials, keys, wallets, endpoints or funds.
- No real blockchain call; `FakeChain` is in-process.
- The dashboard always shows: **INDEPENDENT EDUCATIONAL SIMULATOR — NOT BINANCE.**
- No Binance logo is used.
