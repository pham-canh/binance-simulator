# Incident Timeline — Educational Replay

- **Date:** 2026-11-05
- **Branch:** `demo/binance-incident`
- **Replay:** `simulator/incident.py` → `scripts/replay_incident.py`
- **Evidence:** `reports/evidence/phase3-replay.json`,
  `reports/AUDIT_LOG.jsonl`
- **Seed / clock:** `binance-incident-demo` / `1700000000000`

Every row is labelled. `PUBLIC FACT` rows reproduce the public reporting
summarised in `PROJECT_ANALYSIS.md` and were checked on 2026-11-05 against
the Binance post "29 October 2026 Binance Security Incident: Initial
Findings and Response Update" (2026-11-03):
<https://www.binance.com/en/blog/education/3229153443759566763>. `SCENARIO` and `CONTROL` rows are
synthetic and exist only in this simulator. The replay is an analogue at the
withdrawal-control boundary, **not** a reproduction of the real intrusion.

---

## 1. Public facts

| Date / time (UTC) | Classification | Event | Source |
|---|---|---|---|
| 2026-10-29 20:05 | PUBLIC FACT | Binance hot wallets compromised; approximately **$6.3B** of token assets affected. | Binance Support, Security Incident Update #2 (2026-10-30) |
| 2026-10-30 | PUBLIC FACT | Withdrawals suspended; roughly **$3B** frozen on-chain; Binance found no evidence that wallet private keys leaked. | Same update |
| 2026-11-03 | PUBLIC FACT | Initial findings: unauthorized access to an **internal wallet signing service**, malicious **EIP-7702** authorizations, **50 signing transactions**, **$6.34B** impacted, **$2.85B** frozen. | Binance, 29 October 2026 Incident: Initial Findings |
| 2026-10-29 23:56 | PUBLIC FACT | Final unauthorized transfer of **2,961.9 ETH** finalized on-chain. | Same initial-findings update |
| 2026-10-30 00:10 | PUBLIC FACT | Binance cleared the EIP-7702 delegation code from the `Binance14` hot wallet. | Same initial-findings update |

The real incident was not a normal withdrawal-API bug. The demo must not imply
that the scenario below is the actual attack chain.

## 2. Synthetic replay

| # | Classification | Event | Observed result |
|---|---|---|---|
| 1–5 | PUBLIC FACT | Reported incident facts, quoted above. | Recorded, not simulated. |
| 6 | SCENARIO | Three deterministic in-process ledgers are seeded (`ethereum`, `bsc`, `tron`). | No node, wallet or network call. |
| 7 | SCENARIO | Synthetic operator `ops-demo` receives **1,000 OMG** available. | Synthetic balance only. |
| 8 | SCENARIO | A stolen synthetic API key is used at the authorization boundary. | No phishing, endpoint, or signing-service model. |
| 9 | CONTROL | Withdrawal of **999999 OMG** to an untrusted address. | Rejected `-9003` (single-withdrawal limit). Balance 1000 → 1000. Broadcasts 0 → 0. |
| 10 | SCENARIO | Withdrawal of **400 OMG** to the same untrusted address. | Allowed once; `anomaly.detected` recorded. Balance 1000 → 600. Broadcasts 0 → 1. |
| 11 | CONTROL | Incident response pauses withdrawals. | Guard state `paused: true`. |
| 12 | CONTROL | Retry **400 OMG** while paused. | Rejected `-9001`. Broadcasts 1 → 1. |
| 13 | CONTROL | Synthetic withdraw permission revoked. | Guard state records the revocation. |
| 14 | CONTROL | Retry **1 OMG** to a trusted address while revoked. | Rejected `-9002`. No movement. |
| 15 | CONTROL | Permission restored after the drill. | Synthetic state only. |
| 16 | EVIDENCE | Audit trail verified. | 11 hash-chained records, chain valid. |

## 3. What the replay proves

- The over-limit request is rejected **before** the internal debit and before
  any simulated chain broadcast.
- A rejected request leaves the available balance unchanged.
- Pause and revocation stop subsequent attempts at the authorization layer.
- Every allow/deny decision is written to a SHA-256 hash-chained audit trail.
- The audit file reads back and verifies (`reports/TEST_RESULTS.json`,
  gate `audit-file-chain`).

## 4. What it does not prove

- It does not model the real internal signing service, EIP-7702 delegation,
  nonce manipulation, key compromise, or the DPRK attribution.
- It does not model production concurrency, multiple processes, or real
  authorization infrastructure.
- It does not prove that any real Binance control failed or succeeded.

## 5. Reproduce

```sh
cd /Users/admin/harness/binance-simulator
bash scripts/bootstrap.sh
.venv/bin/python scripts/replay_incident.py
.venv/bin/python scripts/verify_all.py
```

The first command writes `reports/evidence/phase3-replay.json` and
`reports/AUDIT_LOG.jsonl`. The second writes `reports/TEST_RESULTS.json`.
