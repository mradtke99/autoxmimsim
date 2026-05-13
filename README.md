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
