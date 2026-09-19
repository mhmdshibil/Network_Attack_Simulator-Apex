# Contributing to Apex Argus

---

## Development Setup

```bash
# Python environment (conda base or venv — project was built on conda base)
python3.11 -m venv venv
source venv/bin/activate

pip install -r backend/requirements.txt

# Frontend
cd frontend && npm install && cd ..

# Start backend
cp .env.example .env
uvicorn backend.app.main:app --reload --host 0.0.0.0 --port 8000

# Start frontend (separate terminal)
cd frontend && npm run dev
```

→ Full setup guide: [SETUP.md](SETUP.md)  
→ Full architecture: [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md)

---

## How to Add a New Attack Type

The entire pipeline is driven by two config files. Adding a new class takes ~5 minutes.

**1. Add feature ranges to `backend/app/ml/attack_taxonomy.py`**
```python
ATTACK_CLASSES["new_attack"] = {
    "packets_per_second": (lo, hi),
    "avg_request_rate":   (lo, hi),
    "failed_connections": (lo, hi),
    "unique_ports":       (lo, hi),
    "bytes_per_packet":   (lo, hi),
    "connection_duration":(lo, hi),
    "payload_entropy":    (lo, hi),
}
```
Pick ranges that are realistic and distinguishable from existing classes (check the confusion matrix in [docs/EVALUATION_REPORT.md](docs/EVALUATION_REPORT.md) for current overlap patterns).

**2. Create a generator in `scripts/generate_<name>.py`**

Follow the pattern of any existing generator (e.g. `generate_bruteforce_attack.py`). The function must return a list of 12-element rows:
```
[timestamp, src_ip, dst_ip, dst_port, protocol, packet_count,
 request_rate, success_flag, label, bytes_per_packet,
 connection_duration, payload_entropy]
```

**3. Wire the generator into `backend/app/services/auto_attack.py`**
```python
from scripts.generate_new_attack import generate_new_attack
_ATTACK_GENERATORS.append((generate_new_attack, {"n_events": 30}, "new_attack.csv", 2))
```

**4. Add MITRE mapping in `backend/app/ml/mitre_mapping.py`**
```python
"new_attack": {"tactic": "...", "technique_id": "T...", "technique_name": "..."}
```

**5. Retrain**
```bash
python -m backend.app.ml.build_dataset
python -m backend.app.ml.train_model
python -m backend.app.ml.anomaly_model
python -m backend.app.ml.evaluation_harness  # verify accuracy >= 95%
```

---

## How to Add a New API Endpoint

All routes follow the same pattern. Look at `backend/app/api/routes_explain.py` as a clean example.

1. Create (or add to) a router file in `backend/app/api/`
2. Define the route:
   ```python
   from fastapi import APIRouter, Depends
   from backend.app.core.auth import require_analyst

   router = APIRouter(prefix="/api/my-feature", tags=["my-feature"])

   @router.get("/")
   def my_endpoint(_: dict = Depends(require_analyst)):
       return {"data": "..."}
   ```
3. Register the router in `backend/app/main.py`:
   ```python
   from backend.app.api.my_router import router as my_router
   app.include_router(my_router)
   ```
4. Add a fetch wrapper in `frontend/src/api/api.js`:
   ```js
   export async function fetchMyFeature() {
     const res = await apiFetch(`${API_BASE}/api/my-feature/`)
     return res.json()
   }
   ```

---

## How to Add a New Frontend Page

Look at `frontend/src/pages/ModelInsights.jsx` as a minimal example.

1. Create `frontend/src/pages/MyPage.jsx` and (optionally) `MyPage.css`
2. Add the section to `frontend/src/pages/UnifiedDashboard.jsx`:
   ```jsx
   import MyPage from './MyPage'
   const sections = {
     ...
     'my-page': { component: MyPage },
   }
   ```
3. Add a nav item to `frontend/src/components/Sidebar.jsx`:
   ```jsx
   import { SomeIcon } from 'lucide-react'
   // in menuItems:
   { id: 'my-page', label: 'My Page', icon: SomeIcon },
   ```

The `activeSection` prop controls visibility — the UnifiedDashboard renders all sections but CSS hides inactive ones.

---

## Pull Request Guidelines

- **Describe what and why**, not what the diff shows. The diff is already in the PR.
- Keep PRs focused — one feature or bug fix per PR.
- Run the evaluation harness before submitting changes to any ML file:
  ```bash
  python -m backend.app.ml.evaluation_harness
  # Overall accuracy must stay >= 95%
  ```
- Run `npm run build` and confirm it succeeds before submitting frontend changes.
- The CI pipeline (`backend-test` + `frontend-build`) must pass. Security scan findings from `continue-on-error` jobs should be acknowledged in the PR description if they're new.
