# Network Attack Simulator — v2 Build Plan

## How to use this
Paste each **Prompt** block into Claude Code in your project root, one at a time. Review what it changes before moving to the next phase — don't batch multiple phases into one giant prompt, or you lose the ability to catch mistakes early and verify each layer works before building on top of it.

---

## Phase 0 — Safety rails (do this before Phase 4)
Any real firewall enforcement work must happen inside an isolated VM or container, never on your real network or host machine. Set this up (a throwaway Ubuntu VM in VirtualBox/UTM, or a Docker container with `NET_ADMIN` capability) before you touch `actions.py`.

---

## Phase 1 — Fix the detection pipeline (Core)

```
Fix the feature contract mismatch between training and inference:
1. Show me the exact column names/order in dataset_generator.py's output
   vs FEATURE_COLUMNS in feature_engineering.py
2. Decide and implement one canonical feature set — prefer making
   aggregate_by_time_window() produce it, and retrain the model on data
   generated the same way
3. In detection_service.py, remove `label = random.choice(possible_labels)`
   and use the model's actual predicted_label
4. Replace the random risk_score/confidence assignment with
   model.predict_proba(X)[i].max() and a risk_score derived from it
   (not a random range per tier)
5. Add a sanity test: run 20 known port_scan rows and 20 known normal
   rows through the fixed pipeline and print predicted vs expected
   labels, so I can verify accuracy before moving on
Don't touch the response/decision engine or actions.py yet.
```

## Phase 2 — Full attack coverage (Core)

```
Extend scripts/ to generate live traffic for the four missing attack
classes: ddos, bruteforce, sql_injection, malware — consistent with
the ranges already defined in attack_taxonomy.py. Wire them into
auto_attack.py's loop alongside the existing port_scan and normal
generators, with sensible relative frequencies (attacks should be
rarer than normal traffic).

Then show me: is it feasible to swap the synthetic taxonomy-range
generator for a real public dataset (CICIDS2017, NSL-KDD, or
UNSW-NB15) as the training/simulation source instead? Give me the
tradeoffs — don't implement yet, just report.
```

## Phase 3 — Anomaly detection layer (Stretch, recommended)

```
Add an Isolation Forest trained only on normal traffic, running
alongside the existing Random Forest classifier. Design:
- If Random Forest flags a known attack type with high confidence,
  use that label
- If Random Forest says "normal" but Isolation Forest flags the
  point as anomalous, emit label = "unknown_anomaly" with a lower
  confidence tier — this is the zero-day detection path
- Log both models' outputs in the detection record so I can inspect
  disagreements
Add a short evaluation: what % of held-out attack traffic does the
anomaly model catch that the classifier misses, and vice versa.
```

## Phase 4 — Real enforcement, sandboxed (Core)

```
Replace the stub functions in actions.py with real enforcement,
scoped ONLY to the sandbox environment I've set up (confirm with me
before running anything if you're unsure which environment this is):
- firewall_block: use python-iptables or a subprocess call to
  iptables/nftables (Linux) to actually drop traffic from the
  flagged IP
- throttle: implement actual rate-limiting (tc/nftables rate rules),
  and fix response/engine.py so RATE_LIMIT actually maps here
  instead of silently becoming "log"
- Add rollback: when a hard-block's expiry timestamp (already in the
  policy engine) passes, actually remove the corresponding rule
Add a dry-run flag so I can test the decision logic without applying
real rules while I'm not in the sandbox.
```

## Phase 5 — Explainability (Stretch, high value)

```
Add SHAP explainability to the Random Forest classifier. For each
detection, compute and store the top 3 contributing features and
their SHAP values. Add a new API endpoint that returns this
breakdown for a given detection ID, and a minimal frontend panel
that shows "why this fired" per alert.
```

## Phase 6 — Plumbing cleanup (Core)

```
Consolidate the three divergent hard-block file paths
(backend/app/policy/hard_blocked_ips.json,
data/processed/hard_blocked_ips.json,
data/policies/hard_blocked_ips.json) into a single canonical path
used everywhere. Remove or clearly mark policy/engine.py as
deprecated dead code since response/decision.py is the active path.
Fix routes_system.py to read from data that is actually written —
either make the audit writer also populate
data/audit/decision_audit.csv, or point routes_system.py at
security_events.jsonl instead.
```

## Phase 7 — Evaluation suite (Core for your report)

```
Build an evaluation harness that:
1. Runs the full pipeline against a held-out labeled test set
2. Reports precision, recall, F1, and false-positive rate per
   attack class
3. Compares against a naive static-threshold baseline (e.g., flag
   if packet_rate > fixed number) so I can show the ML pipeline
   actually outperforms simple rules
Output results as a markdown table I can drop into my final report.
```

## Phase 8 — Real-time dashboard (Stretch)

```
Add a FastAPI WebSocket endpoint that pushes new detection events to
the frontend as they're written, and update the dashboard to consume
it instead of polling on a timer. Keep the polling code as a fallback
if the WebSocket connection drops.
```

---

## v2 feature brainstorm — extra stack / novelty ideas

### AI/ML depth
- **LLM-generated incident summaries** — feed a raw detection JSON to an LLM and get back a human-readable analyst note ("Repeated failed logins from 203.0.113.4 over 90s, consistent with a brute-force attempt; recommend block"). Ties directly into your explainability work, cheap to build, strong demo impact.
- **Adversarial robustness test** — deliberately craft inputs designed to evade your own classifier and report what you find. This is a current, legitimate research angle (adversarial ML in network security) and shows depth beyond "I trained a model."
- **Drift monitoring** — track live prediction confidence over time, flag when it degrades, trigger a retrain. Shows you understand ML systems don't stay accurate forever.
- **LSTM/GRU sequence model** — catches slow, low-and-drip attacks a single-snapshot classifier misses.

### Infrastructure ("extra stack")
- **Docker Compose** — one-command spin-up of backend, frontend, and model service. Makes your live demo trivial to run and looks professional in a report.
- **Model as its own microservice** — split the ML serving layer into a separate FastAPI container from the main backend. Lets you genuinely say "microservice architecture" and demonstrates you understand separation of concerns.
- **Redis pub/sub or lightweight queue** for event streaming instead of file polling — pairs naturally with Phase 8.
- **Auth (JWT, admin vs analyst roles)** — turns a single-user demo into something that looks like real SOC tooling.
- **Isolated attacker/victim containers on a bridge network** — lets you run genuinely live traffic instead of pure synthetic generation. Big novelty jump, but a heavy time investment — only if the core phases are already solid.

### Threat intelligence
- Cross-reference flagged IPs against a free-tier reputation API (e.g. AbuseIPDB) to enrich alerts with external context.
- Simple GeoIP lookup on flagged sources for a map visualization.

### Reporting / demo polish
- Auto-generated PDF incident report per detection.
- **Replay mode** — feed a real public pcap/attack dataset through the whole live pipeline during your viva, so evaluators watch it detect and respond to real captured traffic in real time. One of the more memorable demos for this category of project.

---

## Recommended minimum v2 scope (if "everything" doesn't fit the semester)

**Core:** Phases 1, 2, 4, 6, 7
**One anomaly story:** Phase 3 (Isolation Forest — best effort-to-payoff ratio)
**One extra-stack pick:** LLM-generated incident summaries *or* Docker Compose — both are high visible impact relative to the work involved, unlike the live attacker/victim bridge network, which is a much bigger lift for similar payoff.

Everything else in the brainstorm list is genuinely good — just treat it as a backlog to pull from if you finish early, not a checklist you need to clear entirely.
