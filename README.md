# autoxmimsim

Python project scaffold for automating XMI-MSIM workflows.

## Development Environment

This project is set up to use the existing `py10` Conda environment:

```powershell
C:\Users\mradtke\AppData\Local\Continuum\anaconda3\envs\py10\python.exe
```

From the repository root, install the package in editable mode:

```powershell
C:\Users\mradtke\AppData\Local\Continuum\anaconda3\envs\py10\python.exe -m pip install -e .
```

Run the test suite:

```powershell
C:\Users\mradtke\AppData\Local\Continuum\anaconda3\envs\py10\python.exe -m unittest discover -s tests
```

Run the CLI:

```powershell
C:\Users\mradtke\AppData\Local\Continuum\anaconda3\envs\py10\python.exe -m autoxmimsim --version
```

Run the first synthetic recovery demo:

```powershell
C:\Users\mradtke\AppData\Local\Continuum\anaconda3\envs\py10\python.exe -m autoxmimsim synthetic-demo --output reports\synthetic-demo
```

The demo uses a deterministic fake XRF backend. It generates a synthetic target spectrum,
searches a small geometry/composition grid, and writes an HTML report plus a JSON summary.

Inspect an XMI-MSIM input template:

```powershell
C:\Users\mradtke\AppData\Local\Continuum\anaconda3\envs\py10\python.exe -m autoxmimsim inspect-template tests\fixtures\CuSnBronze.xmsi
```

Render a modified Cu/Sn bronze candidate input from that template:

```powershell
C:\Users\mradtke\AppData\Local\Continuum\anaconda3\envs\py10\python.exe -m autoxmimsim render-template tests\fixtures\CuSnBronze.xmsi --output reports\xmsi-template
```

Run a low-photon XMI-MSIM smoke simulation and convert the result to CSV:

```powershell
C:\Users\mradtke\AppData\Local\Continuum\anaconda3\envs\py10\python.exe -m autoxmimsim run-template-smoke tests\fixtures\CuSnBronze.xmsi --output reports\xmimsim-smoke
```

Run the first tiny real-backend Cu/Sn layer-thickness Bayesian optimization:

```powershell
C:\Users\mradtke\AppData\Local\Continuum\anaconda3\envs\py10\python.exe -m autoxmimsim run-real-bronze-demo tests\fixtures\CuSnBronze.xmsi --output reports\real-bronze-demo --target copper_layer_thickness=0.00055 --target tin_layer_thickness=0.05 --range copper_layer_thickness=0.0001:0.001:3 --range tin_layer_thickness=0.03:0.07:3 --evaluations 5
```

This renders one target from the supplied `--target` values and adaptively selects
candidate runs inside the supplied `--range` bounds. It runs XMI-MSIM for each one,
compares the spectra, and writes a report plus `spectrum-comparison.html` for
visual inspection.
