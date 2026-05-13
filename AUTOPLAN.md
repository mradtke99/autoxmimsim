# /autoplan Review: Narrow Real-Backend Optimizer Loop

Generated: 2026-05-13
Branch: main
Base commit: a92ae6c
Plan file: DESIGN.md
Status: DRAFT

## Plan Summary

Implement one tiny real XMI-MSIM optimizer loop using `tests/fixtures/CuSnBronze.xmsi`.
The loop should generate one low-photon target spectrum, evaluate only 2-3 fixed candidate
parameter sets, store every run in its own artifact directory, score candidates with
`normalized_rmse`, and write a minimal report/summary.

This is intentionally narrower than the long-term plan. It proves the real backend,
artifact traceability, and scoring path before adding caching, Bayesian optimization,
measured spectrum import, or a GUI.

## Premises

1. Real XMI-MSIM execution is now available through `XmiMsimCliBackend`.
2. A full parameter grid is too expensive for the next step; the smoke run took about 28 seconds.
3. The next phase should optimize for auditability over search power.
4. Every candidate score must point to its own `.xmsi`, `.xmso`, and `.csv` artifacts.
5. The existing fake-backend recovery path should remain fast and covered by unit tests.

## CEO Review

Mode: selective expansion.

### Strategy Verdict

The narrowed loop is the right next move. It is small enough to ship quickly, but it tests the most important product claim: autoxmimsim can compare real XMI-MSIM spectra and choose the closest candidate.

### Premise Challenge

- The project should not jump to Bayesian optimization yet. One real candidate still costs tens of seconds, and the artifact model is not stable enough.
- The project should not generalize the XMSI parameter schema yet. Cu/Sn bronze gives enough surface area for the first real inverse loop.
- The project should not prioritize GUI or polished reporting until the real-backend loop can preserve evidence for every score.

### Dream State Delta

The long-term dream remains: measured spectra in, optimized geometry/composition plus uncertainty report out. The next phase should only build the smallest trustworthy bridge from "single XMI-MSIM smoke run" to "real candidate comparison."

### CEO Score

8/10. The plan is focused and scientifically honest. It loses points only because the target spectrum is still synthetic/generated from the same template, so it does not yet prove measured-data readiness.

## Design Review

Skipped: no UI scope for this phase.

The reporting output is developer/scientist-facing HTML, but no new screen, form, dashboard, GUI, or interaction model is planned. GUI remains deferred.

## Engineering Review

### What Already Exists

- `src/autoxmimsim/backends.py`: `XmiMsimCliBackend` can render `.xmsi`, execute XMI-MSIM, convert `.xmso` to CSV, and load a `Spectrum`.
- `src/autoxmimsim/optimization.py`: `grid_search()` scores candidates against a target spectrum.
- `src/autoxmimsim/xmsi.py`: `XmsiTemplate` edits Cu/Sn composition, bronze thickness, geometry, photons, and outputfile.
- `src/autoxmimsim/objectives.py`: `normalized_rmse()` compares whole spectra.
- `src/autoxmimsim/reporting.py`: `write_recovery_report()` already writes HTML and JSON for a recovery run.
- Tests cover fake recovery, XMSI rendering, CSV loading, and CLI backend happy path.

### NOT In Scope

- Bayesian optimization: defer until runtime, artifacts, and candidate scoring are reliable.
- General parameter schema: defer until Cu/Sn candidate comparison reveals the useful knobs.
- Caching: defer, but artifact directory structure should be compatible with later caching.
- GUI: defer until the CLI/report loop is useful.
- Full uncertainty model: defer; near-best intervals are enough for the next proof.
- Measured spectrum import: defer until the real-backend synthetic target loop works.
- CI and releases: defer; local `py10` plus GitHub repo is enough for this phase.

### Architecture Diagram

```text
CLI: real-bronze-demo
  |
  v
workflows.run_real_bronze_demo()
  |
  +--> target/
  |     +--> XmsiTemplate.apply_parameters()
  |     +--> XmiMsimCliBackend.simulate(run_id="target")
  |     +--> target.xmsi -> target.xmso -> target.csv -> Spectrum
  |
  +--> candidates [fixed list of 2-3 ParameterValues]
  |     |
  |     +--> candidate-000/
  |     |     +--> XmiMsimCliBackend.simulate(run_id="candidate-000")
  |     |     +--> normalized_rmse(target, candidate)
  |     |
  |     +--> candidate-001/
  |     +--> candidate-002/
  |
  +--> OptimizationResult
  |
  +--> write_recovery_report()
        +--> report.html
        +--> summary.json
```

### Architecture Decisions

1. Add `run_id` to `SimulationRequest`.
   Classification: mechanical.
   Principle: explicit over clever.
   Rationale: the optimizer must tie every score to the artifacts that produced it.

2. Use per-run artifact directories.
   Classification: mechanical.
   Principle: choose completeness.
   Rationale: XMI-MSIM emits multiple files per candidate, and overwriting destroys evidence.

3. Limit the first real loop to 2-3 fixed candidates.
   Classification: mechanical.
   Principle: pragmatic.
   Rationale: one smoke candidate took about 28 seconds, so a grid can become slow quickly.

4. Keep generic `grid_search()` available, but use a narrow workflow for this first real run.
   Classification: taste.
   Principle: explicit over clever.
   Rationale: a fixed candidate list is safer for the first real-backend proof; generic grids can follow.

### Failure Modes Registry

| Codepath | Realistic Failure | Test Exists? | Error Handling? | User Outcome | Critical Gap? |
|---|---|---:|---:|---|---:|
| Render target XMSI | Missing required XML node | Partial | Yes | Exception names missing element | No |
| Run `xmimsim-cli` | Bad XML, missing DLL path, simulator crash | Gap | Yes | RuntimeError with command/logs | No |
| Run `xmso2csv` | `.xmso` missing or conversion fails | Gap | Yes | RuntimeError with command/logs | No |
| Load CSV | Empty/malformed CSV | Partial | Partial | ValueError for short rows | No |
| Candidate loop | Candidate overwrites previous artifacts | Gap | Planned fix | Misleading report if not fixed | Yes until fixed |
| Scoring | Energy grids differ | Yes through objective behavior | Yes | ValueError | No |
| Report | Candidate missing expected parameter | Gap | No | KeyError during report render | No for narrow loop |

### Engineering Score

7/10 before implementation. The shape is good, but artifact identity and failure tests must land before a real optimizer loop is trustworthy.

## Test Review

### Coverage Diagram

```text
CODE PATHS                                               TEST STATUS
[+] SimulationRequest.run_id
  +-- default run id preserves existing fake tests         [GAP]
  +-- explicit run id reaches backend artifact path        [GAP]

[+] XmiMsimCliBackend.simulate()
  +-- target writes target/candidate files under run_id    [GAP]
  +-- xmimsim-cli happy path                               [TESTED]
  +-- xmimsim-cli failure includes command/stdout/stderr   [GAP]
  +-- xmso2csv happy path                                  [TESTED]
  +-- xmso2csv failure includes command/stdout/stderr      [GAP]
  +-- CSV loads into Spectrum                              [TESTED]

[+] Narrow real bronze workflow
  +-- generate target spectrum once                        [GAP]
  +-- evaluate candidate-000..candidate-002                [GAP]
  +-- choose lowest normalized_rmse score                  [GAP]
  +-- report best parameters and artifact paths            [GAP]

[+] CLI
  +-- command dispatches narrow workflow                   [GAP]
  +-- prints best score and report path                    [GAP]
```

### Required Tests

- `tests/test_optimization.py`: assert `grid_search()` generates stable `candidate-000` ids when no explicit ids are supplied.
- `tests/test_xmimsim_cli_backend.py`: assert explicit `run_id` writes under its own directory.
- `tests/test_xmimsim_cli_backend.py`: assert simulator failure raises `RuntimeError` with command, stdout, and stderr.
- `tests/test_xmimsim_cli_backend.py`: assert converter failure raises `RuntimeError` with command, stdout, and stderr.
- `tests/test_real_bronze_workflow.py`: use a fake runner/backend to prove target plus 2-3 candidates are evaluated and best candidate is returned.
- `tests/test_cli.py`: assert the new CLI command calls the workflow and prints the result without running XMI-MSIM.

### Test Score

6/10 before implementation. Existing tests are good for the smoke backend, but the next phase needs identity, failure, and workflow orchestration tests.

## Performance Review

One low-photon real candidate took about 28 seconds. The next phase must avoid a general grid by default.

### Performance Decisions

- Use 1 target plus 2-3 candidates only.
- Keep photon counts at smoke settings for this phase: `n_photons_interval=10`, `n_photons_line=100`.
- Do not parallelize yet. XMI-MSIM thread/process behavior should be measured first.
- Do not add caching yet. Directory identity should make caching easy later.

### Performance Score

7/10. Runtime is acceptable for a tiny proof, but not for broad parameter search.

## DX Review

Product type: Python CLI/library for scientific simulation workflows.

### Developer Journey Map

| Stage | Current State | Target For Next Phase |
|---|---|---|
| Discover | README explains synthetic demo and template smoke commands | Add real bronze demo command |
| Install | Editable install in `py10` documented | Keep same |
| Configure | XMI-MSIM path hard-coded to Windows install | Document override later, not this phase |
| First run | `run-template-smoke` works | `real-bronze-demo` works |
| Inspect output | Artifacts in `reports/` | Per-run folders with clear names |
| Debug failure | RuntimeError includes subprocess logs | Add tests to lock this |
| Extend | `XmsiTemplate` has typed operations | Keep Cu/Sn only for now |
| Automate | No caching or batch mode | Deferred |
| Upgrade | No release process yet | Deferred |

### DX Scorecard

| Dimension | Score | Notes |
|---|---:|---|
| Time to hello world | 7/10 | Good if `py10` and XMI-MSIM are present |
| CLI naming | 7/10 | Commands are explicit but growing wordy |
| Error messages | 6/10 | Subprocess errors need tests and clearer CLI surfacing |
| Docs | 6/10 | README examples exist, but no troubleshooting section |
| Local environment | 7/10 | `py10` path is pinned; XMI-MSIM install path is assumed |
| Artifacts | 5/10 | Needs per-run structure before real search |
| Extensibility | 6/10 | Good boundaries, parameter schema still narrow |
| Release/upgrade | 3/10 | Not needed yet, but undeveloped |

Overall DX: 6/10.
Current TTHW: about 10-15 minutes if XMI-MSIM is installed.
Target TTHW after next phase: under 5 minutes from editable install to real bronze demo.

### DX Implementation Checklist

- Add README command for real bronze demo.
- Print report path and artifact root after the run.
- Make subprocess failure messages include problem, command, stdout, stderr, and likely fix.
- Keep default run small enough that first-time users do not accidentally start a long job.

## Cross-Phase Themes

1. Artifact traceability appears in CEO, engineering, test, and DX review.
2. Scope control appears in CEO, engineering, and performance review.
3. Error messages appear in engineering, tests, and DX review.

## Deferred To TODOs

- Add Bayesian optimization after real-backend loop and caching are stable.
- Add measured spectrum import after synthetic real-backend comparison works.
- Add cache/reuse of candidate artifacts after per-run directories are stable.
- Add GUI after CLI/report workflow has real scientific value.
- Add CI/release workflow when the API surface settles.

## Decision Audit Trail

| # | Phase | Decision | Classification | Principle | Rationale | Rejected |
|---|---|---|---|---|---|---|
| 1 | CEO | Keep next phase narrow: one target plus 2-3 real candidates | Mechanical | Pragmatic | Real candidate runtime is high enough that broad search is premature | Full grid, Bayesian search |
| 2 | Eng | Add `run_id` to `SimulationRequest` | Mechanical | Explicit over clever | Candidate identity belongs in the request/result path | Backend-local counter |
| 3 | Eng | Store each run in its own artifact directory | Mechanical | Choose completeness | Every score needs auditable `.xmsi`, `.xmso`, and `.csv` files | Shared folder, overwriting |
| 4 | Eng | Add subprocess failure tests for both XMI-MSIM commands | Mechanical | Choose completeness | Real simulator failures need immediate diagnosis | Happy-path only |
| 5 | Eng | Use fixed candidate list for first real workflow | Taste | Explicit over clever | Safer than exposing a general grid before runtime controls exist | Generic `ParameterSpace` grid now |
| 6 | DX | Add one copy-paste README command and concise CLI output | Mechanical | Bias toward action | TTHW improves without adding new infrastructure | Separate docs overhaul |

## Final Recommendation

Approve the narrowed plan as-is. It is ready to implement.

### Implementation Contract

1. Add `run_id` to `SimulationRequest`.
2. Update `grid_search()` or the narrow workflow so candidate ids are stable.
3. Update `XmiMsimCliBackend` to write each run under `work_dir / run_id`.
4. Add simulator and converter failure tests.
5. Add `run-real-bronze-demo` or similarly named CLI command.
6. Run only one target plus 2-3 fixed candidates.
7. Write a minimal report/summary with best score, parameters, and artifact paths.
