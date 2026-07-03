# Add Intel Source Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a two-step frontend flow for probing and saving configurable intel sources.

**Architecture:** Reuse the existing backend `probe_intel_source` collector for detection, add a small config persistence service for atomic JSON appends, and expose two FastAPI endpoints. The frontend adds one dashboard dialog that calls probe first, allows metadata edits, then saves the recommended source.

**Tech Stack:** FastAPI, Pydantic, aiohttp, pytest, Next.js 16, React 19, TypeScript, Tailwind CSS 4, lucide-react.

---

## File Map

- Create `backend/src/services/intel_source_config.py`: atomic load/append/write helpers for `intel_sources.json`.
- Modify `backend/src/api/intel.py`: request/response models and source probe/create endpoints.
- Modify `backend/tests/api/test_intel_api.py`: API tests for probe, create, duplicate, and invalid configs.
- Modify `frontend/src/types/intel.ts`: shared source config and API payload types.
- Modify `frontend/src/lib/intel-api.ts`: POST helpers for probe and create.
- Create `frontend/src/components/operations-dashboard/add-source-dialog.tsx`: modal-style two-step UI.
- Modify `frontend/src/app/dashboard/page.tsx`: dashboard-level dialog state and refresh behavior.
- Modify `frontend/src/components/operations-dashboard/dashboard-shell.tsx`: header action slot for the add button.

## Tasks

### Task 1: Backend Probe API

**Files:**
- Modify: `backend/tests/api/test_intel_api.py`
- Modify: `backend/src/api/intel.py`

- [ ] **Step 1: Write failing API test**

Add a test that monkeypatches `probe_intel_source` and verifies `POST /api/intel/sources/probe` returns `status`, `sample_count`, `message`, and `recommended_source`.

- [ ] **Step 2: Run failing test**

Run: `cd backend && bash scripts/test.sh tests/api/test_intel_api.py::test_probe_intel_source_endpoint_returns_recommendation -v`

Expected: FAIL because the route does not exist.

- [ ] **Step 3: Implement minimal endpoint**

Add Pydantic request/response models in `backend/src/api/intel.py`, create an `aiohttp.ClientSession`, call `probe_intel_source`, and return `recommended_source.model_dump(mode="json")`.

- [ ] **Step 4: Run passing test**

Run the same test command. Expected: PASS.

### Task 2: Backend Config Persistence

**Files:**
- Create: `backend/src/services/intel_source_config.py`
- Modify: `backend/tests/api/test_intel_api.py`
- Modify: `backend/src/api/intel.py`

- [ ] **Step 1: Write failing save tests**

Add tests that:

- monkeypatch `intel_api.CONFIG_PATH` to a temp JSON file,
- `POST /api/intel/sources` appends a valid source,
- duplicate `source_id` returns 409,
- missing feed URL for a feed source returns 422.

- [ ] **Step 2: Run failing tests**

Run: `cd backend && bash scripts/test.sh tests/api/test_intel_api.py -v`

Expected: new tests fail because the create endpoint and service do not exist.

- [ ] **Step 3: Implement config service**

Create `append_intel_source(path: Path, source: IntelSource) -> IntelSource`, load existing sources with `load_intel_sources_from_file`, reject duplicate `source_id`, write sorted, indented JSON through `path.with_suffix(".tmp")` and `replace`.

- [ ] **Step 4: Implement create endpoint**

Add `POST /api/intel/sources`; validate adapter requirements before calling the service; convert duplicates to 409.

- [ ] **Step 5: Run backend tests**

Run: `cd backend && bash scripts/test.sh tests/api/test_intel_api.py tests/collectors/test_intel_source_probe.py tests/collectors/test_university_sources.py -v`

Expected: PASS.

### Task 3: Frontend API Types

**Files:**
- Modify: `frontend/src/types/intel.ts`
- Modify: `frontend/src/lib/intel-api.ts`

- [ ] **Step 1: Add TypeScript types**

Add source config, request, and response interfaces matching the backend payloads.

- [ ] **Step 2: Add POST helper**

Create a local `post<T>` helper in `intel-api.ts`; add `probeIntelSource` and `createIntelSource`.

- [ ] **Step 3: Run lint**

Run: `cd frontend && npm run lint`

Expected: PASS or only unrelated existing failures.

### Task 4: Frontend Dialog UI

**Files:**
- Create: `frontend/src/components/operations-dashboard/add-source-dialog.tsx`
- Modify: `frontend/src/components/operations-dashboard/dashboard-shell.tsx`
- Modify: `frontend/src/app/dashboard/page.tsx`

- [ ] **Step 1: Build dialog component**

Create a client component with URL input, source type select, group/name inputs, probe button, preview state, and save button disabled unless probe status is `success`.

- [ ] **Step 2: Add dashboard entry point**

Pass an action slot into `DashboardShell`, render a lucide `Plus` icon button, and mount `AddSourceDialog` from `DashboardPage`.

- [ ] **Step 3: Refresh after save**

After save, refetch source nav and the active panel data by incrementing a local reload token.

- [ ] **Step 4: Run lint and build**

Run: `cd frontend && npm run lint && npm run build`

Expected: PASS or document unrelated failures.

### Task 5: Full Verification

**Files:**
- No new files.

- [ ] **Step 1: Run backend focused tests**

Run: `cd backend && bash scripts/test.sh tests/api/test_intel_api.py tests/collectors/test_intel_source_probe.py tests/collectors/test_university_sources.py -v`

Expected: PASS.

- [ ] **Step 2: Run frontend verification**

Run: `cd frontend && npm run lint && npm run build`

Expected: PASS.

- [ ] **Step 3: Inspect git diff**

Run: `git diff -- backend/src/api/intel.py backend/src/services/intel_source_config.py backend/tests/api/test_intel_api.py frontend/src/types/intel.ts frontend/src/lib/intel-api.ts frontend/src/components/operations-dashboard/add-source-dialog.tsx frontend/src/components/operations-dashboard/dashboard-shell.tsx frontend/src/app/dashboard/page.tsx docs/superpowers/specs/2026-05-28-add-intel-source-design.md docs/superpowers/plans/2026-05-28-add-intel-source.md`

Expected: only scoped changes for this feature.

## Self-Review

- Spec coverage: probe, preview, editable metadata, confirm save, duplicate handling, and no immediate sync are covered.
- Placeholder scan: no placeholders remain.
- Type consistency: backend `IntelSource` maps to frontend `IntelSourceConfig`; endpoint names match `probeIntelSource` and `createIntelSource`.
