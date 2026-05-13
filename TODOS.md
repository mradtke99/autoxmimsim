# TODOs

## Deferred Scope

### Add Bayesian Optimization

What: Add Bayesian/active-learning optimization once the real-backend loop and caching are reliable.

Why: XMI-MSIM simulations are slow, so an intelligent search strategy should reduce candidate count.

Context: Current plan deliberately uses only 2-3 fixed candidates to prove orchestration first.

Depends on: Per-candidate artifact directories, stable real-backend scoring, runtime measurements.

### Add Measured Spectrum Import

What: Support measured spectrum files as targets.

Why: The project goal is measured spectra in, optimized geometry/composition out.

Context: Synthetic and generated target spectra are safer while validating the inverse workflow.

Depends on: Real-backend synthetic target comparison and a decision on first measured-data format.

### Add Artifact Caching

What: Reuse candidate outputs when parameters and template inputs match a prior run.

Why: Candidate simulations are expensive and repeated searches will otherwise waste time.

Context: Per-run artifact directories should be designed so a cache key can be added later.

Depends on: Stable artifact layout and parameter serialization.

### Add GUI

What: Build a GUI for watching spectra converge and inspecting reports.

Why: The long-term 10x version includes visual convergence and easier exploration.

Context: GUI should wait until the CLI/report workflow has real scientific value.

Depends on: Real-backend loop, report shape, and useful candidate history.

### Add CI And Release Workflow

What: Add GitHub Actions for tests and later release packaging.

Why: The project will need reproducible validation before wider use.

Context: Local `py10` is sufficient for the first implementation phases.

Depends on: Settled package API and a strategy for XMI-MSIM availability in CI.
