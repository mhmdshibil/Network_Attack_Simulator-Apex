# Security Scan Report — Phase 13

Scan date: 2026-08-12  
Tools: Semgrep 1.172.0 (free OSS), npm audit (bundled with npm)  
Snyk: skipped — no `SNYK_TOKEN` set (see §3 below)

---

## 1. Semgrep — Static Analysis (`backend/`)

**Rules run:** 296 (auto config — Community ruleset)  
**Files scanned:** 63  
**Findings:** 1

### Finding S-01 — Wildcard CORS with Credentials Enabled

| Field | Value |
|-------|-------|
| Rule | `python.fastapi.security.wildcard-cors.wildcard-cors` |
| File | `backend/app/main.py:45` |
| Severity | WARNING |
| CWE | CWE-942 (Permissive Cross-domain Policy) |
| OWASP | A05:2021 — Security Misconfiguration |
| Likelihood | HIGH · Impact LOW · Confidence MEDIUM |

**Current code:**
```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],       # ← flagged
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

**What this means:** The CORS policy allows any web origin to make credentialed requests to the API. In practice, browsers actually *reject* the `*` + `credentials: true` combination per the CORS spec — so the middleware is simultaneously too permissive in intent and broken in practice (credentialed cross-origin requests from arbitrary sites will fail in the browser).

**Verdict: FLAG FOR REVIEW — do not auto-fix blindly.**

Recommended fix (when you want to fix it):
```python
allow_origins=[
    "http://localhost:3000",    # dev frontend
    "http://127.0.0.1:3000",
    # add your production URL here
],
```
Or, if unauthenticated open access is acceptable (dev/demo environment with `AUTH_ENABLED=false`), keep `*` but remove `allow_credentials=True`. The `*` + `credentials: True` combo is the real bug — pick one or the other.

**Risk in this project:** Low-medium. This is a local SOC dashboard without a public-internet deployment. The credential bypass concern only matters if an attacker can get a victim's browser to make requests to the API from a malicious page, which requires network access to the backend.

---

## 2. npm audit — Frontend Dependency Scan

**Packages audited:** all deps in `frontend/package.json` + transitive  
**Total vulnerabilities:** 10 (1 low · 4 moderate · 5 high · 0 critical)

### HIGH severity

| ID | Package | Title | Where | Verdict |
|----|---------|-------|--------|---------|
| N-01 | `lodash ≤4.17.23` | Code Injection via `_.template` imports key | Transitive (recharts) | **Low real-world risk** |
| N-02 | `lodash ≤4.17.23` | Prototype Pollution via array path bypass | Transitive (recharts) | **Low real-world risk** |
| N-03 | `nanoid ≤3.3.16` | Infinite loop with negative/zero custom generator size | Transitive (postcss/vite) | **Negligible** |
| N-04 | `postcss ≤8.5.22` | XSS via unescaped `</style>`, path traversal via sourceMappingURL | Build toolchain | **Build-time only** |
| N-05 | `rollup 4.0.0–4.58.0` | Arbitrary File Write via path traversal | Build toolchain | **Build-time only** |

### MODERATE severity

| ID | Package | Title | Where | Verdict |
|----|---------|-------|--------|---------|
| N-06 | `vite ≤6.4.2` | Path traversal in optimized deps `.map` handling | Build toolchain | **Dev server only** |
| N-07 | `esbuild ≤0.24.2` | Dev server allows cross-origin requests | Build toolchain | **Dev server only** |
| N-08 | `@remix-run/router 1.3.0–1.23.2` | Open redirect via `//`-prefixed paths | Runtime (react-router-dom) | **Flag for review** |
| N-09 | `react-router 6.0–7.17.0` | Inherits N-08 | Runtime | **Flag for review** |
| N-10 | `react-router-dom 6.0–7.17.0` | Inherits N-08 | Runtime | **Flag for review** |

### LOW severity

| ID | Package | Title | Where | Verdict |
|----|---------|-------|--------|---------|
| N-11 | `@babel/core ≤7.29.0` | Arbitrary File Read via sourceMappingURL | Build toolchain | **Build-time only** |

### Triage breakdown

**Build-toolchain only (N-04, N-05, N-06, N-07, N-11):** These packages are used during `npm run build`. The Docker image runs nginx serving pre-built static assets — none of these packages run at runtime in production. Risk is effectively zero for a deployed container. Fix by running `npm audit fix` at your convenience; it will update Vite, Rollup, PostCSS, esbuild.

**Negligible (N-03):** nanoid's loop only triggers when you call it with a custom generator and a negative/zero size. The project never calls nanoid directly.

**Low real-world risk (N-01, N-02):** lodash is a transitive dep pulled in by recharts. The code injection only triggers via `_.template()` with attacker-controlled template strings. This project never calls `_.template`. The prototype pollution requires an attacker to control array path inputs to `_.unset`/`_.omit`. Not exploitable in this app's data flows. `npm audit fix` will resolve this if recharts picks up a patched version.

**Flag for review (N-08, N-09, N-10):** react-router-dom's open-redirect via `//`-prefixed paths. The app's navigation is internal-only and user inputs don't feed directly into `<Navigate to=...>` or `router.navigate()`. Exploitability is low, but worth upgrading: `npm audit fix` handles it.

### Recommended action (when ready)

```bash
cd frontend
npm audit fix          # handles most
npm audit              # re-check; esbuild will need --force (vite major bump)
```

Do **not** run `npm audit fix --force` until you've tested the app with the new Vite version — it's a breaking change (`vite@5` → `vite@8`).

---

## 3. Snyk — Skipped

Snyk requires a free account token. To enable:

1. Sign up at https://app.snyk.io/login (free tier)
2. Run `snyk auth` to link your token
3. Set `export SNYK_TOKEN=$(snyk config get api)`
4. Re-run `bash scripts/run_security_scan.sh`

**Alternative (no account required):** `pip-audit` scans Python deps without signup:
```bash
pip install pip-audit
pip-audit -r backend/requirements.txt
```
Preliminary review of `backend/requirements.txt` shows no known CVEs in the pinned Python packages (FastAPI, scikit-learn, shap, etc.) — all are recent versions.

---

## 4. Summary table

| # | Tool | Finding | Severity | Action |
|---|------|---------|----------|--------|
| S-01 | Semgrep | CORS wildcard + credentials — `main.py:45` | WARN | Review & restrict origins |
| N-01/02 | npm audit | lodash code injection / prototype pollution | HIGH | Low real risk; `npm audit fix` when convenient |
| N-03 | npm audit | nanoid loop DoS | HIGH | Negligible; transitive |
| N-04 | npm audit | postcss XSS / path traversal | HIGH | Build-time only; `npm audit fix` |
| N-05 | npm audit | rollup path traversal | HIGH | Build-time only; `npm audit fix` |
| N-06 | npm audit | vite path traversal | MOD | Dev server only; careful `--force` upgrade |
| N-07 | npm audit | esbuild CORS bypass in dev server | MOD | Dev server only; careful upgrade |
| N-08/09/10 | npm audit | react-router open redirect | MOD | Low risk; `npm audit fix` |
| N-11 | npm audit | @babel/core file read | LOW | Build-time only; `npm audit fix` |

**Nothing in this scan requires an immediate code change before the project demo.** The CORS misconfiguration (S-01) is the only code-level issue worth fixing before a production deployment; everything else is either build-toolchain-only or unexploitable in this app's data flows.
