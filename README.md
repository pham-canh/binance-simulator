# BINANCE SIMULATOR — Educational Demo

**INDEPENDENT EDUCATIONAL SIMULATOR — NOT BINANCE.**
Synthetic accounts, balances and an in-process fake chain only. No real funds,
wallets, keys, endpoints or blockchain calls. This is an independent
withdrawal-control analogue, not a reproduction of the October 2026 intrusion.

The project keeps the original KyberNetwork exchange engine and replaces the
2018 Redis/chain integration with `fakeredis` and a deterministic `FakeChain`.

## Quick start (no Docker)

From the repository root:

```sh
bash scripts/bootstrap.sh
.venv/bin/python scripts/run_demo_server.py
```

Open <http://127.0.0.1:5100/>. The dashboard is dark, shows balances, the
OMGETH order book, open orders, withdrawal history and the control state. The
disclaimer is always visible.

Synthetic account:

```sh
curl -s http://127.0.0.1:5100/ping
curl -s -H 'X-MBX-APIKEY: demo-user' http://127.0.0.1:5100/api/v3/account
curl -s http://127.0.0.1:5100/api/v1/simulator/status
```

## Incident replay

```sh
.venv/bin/python scripts/replay_incident.py
```

This writes `reports/evidence/phase3-replay.json` and
`reports/AUDIT_LOG.jsonl`. Every event is labelled `PUBLIC FACT`, `SCENARIO`,
`CONTROL` or `EVIDENCE`. See `reports/INCIDENT_TIMELINE.md`.

The replay shows:

- an over-limit withdrawal rejected before any broadcast;
- balance unchanged after a rejected request;
- anomaly alert, emergency pause and permission revocation;
- a SHA-256 hash-chained audit trail that verifies from disk.

## Verification

```sh
.venv/bin/python scripts/verify_all.py
```

Expected output:

```text
56 passed, 14 skipped, 5 xfailed
10/10 live API checks
overall: ok
```

The script writes `reports/TEST_RESULTS.json`. Individual evidence:

| File | Content |
|---|---|
| `reports/PROJECT_ANALYSIS.md` | Phase 0 repository analysis and safety boundary |
| `reports/PHASE1_BASELINE.md` | local baseline before the fix |
| `reports/INCIDENT_TIMELINE.md` | public facts vs synthetic replay |
| `reports/SECURITY_REPORT.md` | S1 root cause, controls, review, limits |
| `reports/TEST_RESULTS.json` | observed gate results |
| `reports/AUDIT_LOG.jsonl` | hash-chained withdrawal decisions |

## Security changes

- `Exchange.withdraw` now authorizes, debits, then broadcasts.
- A rejected debit or policy check cannot reach the chain.
- A chain failure before broadcast refunds the internal debit.
- Controls: per-asset limits, daily limits, velocity, pause, revocation,
  untrusted-address alerts, idempotency keys.
- `reports/evidence/phase1-s1.json` is the historical pre-fix proof
  (`broadcasts 0 → 1`); `reports/evidence/phase4-s1-fixed.json` is the
  post-fix proof (`0 → 0`).

## Original upstream

The original repository is a 2018 KyberNetwork centralized-exchange simulator
with deposit/withdrawal, balances and order execution. The legacy Docker and
2018 dependency path remains in `Dockerfile` and `requirements.txt` for
reference; the local demo path above does not use it.

## Safety

- Local `127.0.0.1` only; no Docker, real Redis or chain node required.
- Synthetic API keys are allowlisted (`demo-user`, `ops-demo`, test key).
- No real Binance credentials, wallets, private keys, funds or RPC calls.
- No Binance logo; the UI states it is independent and educational.
