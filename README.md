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

Launch the desktop GUI:

```powershell
C:\Users\mradtke\AppData\Local\Continuum\anaconda3\envs\py10\python.exe -m autoxmimsim gui
```

The GUI lets you choose the XMSI template, choose a measured spectrum CSV or use
synthetic target values, edit Bayesian parameter ranges, set photon counts and
evaluations, run the search, and open the generated report or spectrum comparison
plot. Use `Load from template` to populate all currently supported parameters for
the first non-air sample layer: thickness, density, each element weight fraction,
plus sample-source distance and detector-window z.

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

Optimize against a measured spectrum CSV:

```powershell
C:\Users\mradtke\AppData\Local\Continuum\anaconda3\envs\py10\python.exe -m autoxmimsim optimize-measured tests\fixtures\CuSnBronze.xmsi path\to\measured-spectrum.csv --output reports\measured-optimization --range copper_layer_thickness=0.0001:0.001:7 --range tin_layer_thickness=0.03:0.07:7 --evaluations 20
```

Measured CSV files should contain energy and counts columns. A header is allowed:

```csv
energy,counts
0.02,123
0.03,129
0.04,118
```

The measured workflow interpolates simulated spectra onto the measured energy grid
before scoring and plotting.

Measured HDF5 files are also supported when spectra are stored as
`entry/data/data` with shape `(points, spectra_per_point, channels)`, such as
`50cent1002.hdf5`. By default autoxmimsim loads point `1`, sums the four spectra
at that point, and assigns the XMI-MSIM-like energy grid `0.02 + channel * 0.01`.

```powershell
C:\Users\mradtke\AppData\Local\Continuum\anaconda3\envs\py10\python.exe -m autoxmimsim optimize-measured tests\fixtures\CuSnBronze.xmsi tests\fixtures\50cent1002.hdf5 --output reports\hdf5-optimization --range copper_layer_thickness=0.0001:0.001:7 --evaluations 20 --hdf5-point 1 --hdf5-reducer sum --hdf5-energy-offset 0.02 --hdf5-energy-step 0.01
```

Generic one-layer XMSI parameters can also be optimized directly:

```powershell
--range layer_1_thickness=0.00005:0.001:7 --range layer_1_density=4:12:7 --range layer_1_z29_fraction=50:100:6
```

For a one-layer sample, use layer `1` when layer `0` is air.
