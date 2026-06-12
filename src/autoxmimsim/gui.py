"""Tkinter GUI for comfortable autoxmimsim runs."""

from __future__ import annotations

import os
import threading
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

from autoxmimsim.parameters import Parameter, ParameterSpace, ParameterValues
from autoxmimsim.workflows import run_real_bronze_demo


DEFAULT_ROWS = (
    ("copper_layer_thickness", "0.00055", "0.0001", "0.001", "3"),
    ("tin_layer_thickness", "0.05", "0.03", "0.07", "3"),
)


def launch_gui() -> None:
    root = tk.Tk()
    AutoXmimsimApp(root)
    root.mainloop()


class AutoXmimsimApp:
    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.root.title("autoxmimsim")
        self.root.geometry("980x720")
        self.root.minsize(860, 620)

        self.template_var = tk.StringVar(value=str(Path("tests") / "fixtures" / "CuSnBronze.xmsi"))
        self.output_var = tk.StringVar(value=str(Path("reports") / "real-bronze-demo"))
        self.evaluations_var = tk.StringVar(value="5")
        self.initial_evaluations_var = tk.StringVar(value="2")
        self.photons_interval_var = tk.StringVar(value="10")
        self.photons_line_var = tk.StringVar(value="100")
        self.status_var = tk.StringVar(value="Ready")
        self.report_path: Path | None = None
        self.plot_path: Path | None = None
        self.rows: list[ParameterRow] = []

        self._build()

    def _build(self) -> None:
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        frame = ttk.Frame(self.root, padding=14)
        frame.grid(row=0, column=0, sticky="nsew")
        frame.columnconfigure(0, weight=1)
        frame.rowconfigure(3, weight=1)

        self._build_paths(frame)
        self._build_controls(frame)
        self._build_parameter_table(frame)
        self._build_log(frame)
        self._build_actions(frame)

    def _build_paths(self, parent: ttk.Frame) -> None:
        paths = ttk.LabelFrame(parent, text="Files", padding=10)
        paths.grid(row=0, column=0, sticky="ew")
        paths.columnconfigure(1, weight=1)

        ttk.Label(paths, text="XMSI template").grid(row=0, column=0, sticky="w", padx=(0, 8), pady=4)
        ttk.Entry(paths, textvariable=self.template_var).grid(row=0, column=1, sticky="ew", pady=4)
        ttk.Button(paths, text="Browse", command=self._browse_template).grid(row=0, column=2, padx=(8, 0), pady=4)

        ttk.Label(paths, text="Output folder").grid(row=1, column=0, sticky="w", padx=(0, 8), pady=4)
        ttk.Entry(paths, textvariable=self.output_var).grid(row=1, column=1, sticky="ew", pady=4)
        ttk.Button(paths, text="Browse", command=self._browse_output).grid(row=1, column=2, padx=(8, 0), pady=4)

    def _build_controls(self, parent: ttk.Frame) -> None:
        controls = ttk.LabelFrame(parent, text="Search settings", padding=10)
        controls.grid(row=1, column=0, sticky="ew", pady=(10, 0))
        for column in range(8):
            controls.columnconfigure(column, weight=1)

        fields = (
            ("Evaluations", self.evaluations_var),
            ("Initial evaluations", self.initial_evaluations_var),
            ("Photons interval", self.photons_interval_var),
            ("Photons line", self.photons_line_var),
        )
        for index, (label, variable) in enumerate(fields):
            ttk.Label(controls, text=label).grid(row=0, column=2 * index, sticky="w", padx=(0, 6))
            ttk.Entry(controls, textvariable=variable, width=12).grid(row=0, column=2 * index + 1, sticky="ew")

    def _build_parameter_table(self, parent: ttk.Frame) -> None:
        wrapper = ttk.LabelFrame(parent, text="Bayesian parameters", padding=10)
        wrapper.grid(row=2, column=0, sticky="ew", pady=(10, 0))
        for column in range(6):
            wrapper.columnconfigure(column, weight=1)

        headings = ("Parameter", "Target", "Lower", "Upper", "Grid steps", "")
        for column, heading in enumerate(headings):
            ttk.Label(wrapper, text=heading).grid(row=0, column=column, sticky="w", padx=4, pady=(0, 6))

        self.table = wrapper
        for row_values in DEFAULT_ROWS:
            self._add_parameter_row(row_values)

        ttk.Button(wrapper, text="Add parameter", command=lambda: self._add_parameter_row()).grid(
            row=99,
            column=0,
            sticky="w",
            padx=4,
            pady=(8, 0),
        )

    def _build_log(self, parent: ttk.Frame) -> None:
        log_frame = ttk.LabelFrame(parent, text="Run log", padding=10)
        log_frame.grid(row=3, column=0, sticky="nsew", pady=(10, 0))
        log_frame.columnconfigure(0, weight=1)
        log_frame.rowconfigure(0, weight=1)

        self.log = tk.Text(log_frame, height=12, wrap="word")
        self.log.grid(row=0, column=0, sticky="nsew")
        scrollbar = ttk.Scrollbar(log_frame, orient="vertical", command=self.log.yview)
        scrollbar.grid(row=0, column=1, sticky="ns")
        self.log.configure(yscrollcommand=scrollbar.set)

    def _build_actions(self, parent: ttk.Frame) -> None:
        actions = ttk.Frame(parent)
        actions.grid(row=4, column=0, sticky="ew", pady=(10, 0))
        actions.columnconfigure(3, weight=1)

        self.run_button = ttk.Button(actions, text="Run Bayesian search", command=self._run)
        self.run_button.grid(row=0, column=0, padx=(0, 8))
        ttk.Button(actions, text="Open plot", command=self._open_plot).grid(row=0, column=1, padx=(0, 8))
        ttk.Button(actions, text="Open report", command=self._open_report).grid(row=0, column=2, padx=(0, 8))
        ttk.Label(actions, textvariable=self.status_var).grid(row=0, column=3, sticky="e")

    def _add_parameter_row(self, values: tuple[str, str, str, str, str] | None = None) -> None:
        values = values or ("", "", "", "", "3")
        row = ParameterRow(self.table, len(self.rows) + 1, values, self._remove_parameter_row)
        self.rows.append(row)

    def _remove_parameter_row(self, row: "ParameterRow") -> None:
        if len(self.rows) <= 1:
            messagebox.showinfo("autoxmimsim", "At least one parameter is required.")
            return
        row.destroy()
        self.rows.remove(row)
        for index, item in enumerate(self.rows, start=1):
            item.grid(index)

    def _browse_template(self) -> None:
        path = filedialog.askopenfilename(
            title="Choose XMSI template",
            filetypes=(("XMI-MSIM input", "*.xmsi"), ("All files", "*.*")),
        )
        if path:
            self.template_var.set(path)

    def _browse_output(self) -> None:
        path = filedialog.askdirectory(title="Choose output folder")
        if path:
            self.output_var.set(path)

    def _run(self) -> None:
        try:
            request = self._read_request()
        except ValueError as exc:
            messagebox.showerror("autoxmimsim", str(exc))
            return
        self.run_button.configure(state="disabled")
        self.status_var.set("Running XMI-MSIM...")
        self._log("Starting Bayesian search.")
        thread = threading.Thread(target=self._run_worker, args=request, daemon=True)
        thread.start()

    def _read_request(
        self,
    ) -> tuple[Path, Path, ParameterValues, ParameterSpace, int, int, ParameterValues]:
        template = Path(self.template_var.get())
        output = Path(self.output_var.get())
        if not template.exists():
            raise ValueError(f"Template does not exist: {template}")
        target: ParameterValues = {}
        parameters: list[Parameter] = []
        for row in self.rows:
            name, target_value, lower, upper, steps = row.values()
            if not name:
                raise ValueError("Every parameter row needs a name.")
            if name in target:
                raise ValueError(f"Duplicate parameter: {name}")
            target[name] = float(target_value)
            parameters.append(Parameter(name, float(lower), float(upper), int(steps)))
        evaluations = int(self.evaluations_var.get())
        initial_evaluations = int(self.initial_evaluations_var.get())
        fixed = {
            "n_photons_interval": float(self.photons_interval_var.get()),
            "n_photons_line": float(self.photons_line_var.get()),
        }
        return template, output, target, ParameterSpace(tuple(parameters)), evaluations, initial_evaluations, fixed

    def _run_worker(
        self,
        template: Path,
        output: Path,
        target: ParameterValues,
        parameter_space: ParameterSpace,
        evaluations: int,
        initial_evaluations: int,
        fixed: ParameterValues,
    ) -> None:
        try:
            result, report_path = run_real_bronze_demo(
                template,
                output,
                target_parameters=target,
                parameter_space=parameter_space,
                evaluations=evaluations,
                initial_evaluations=initial_evaluations,
                fixed_parameters=fixed,
            )
        except Exception as exc:  # pragma: no cover - UI boundary
            self.root.after(0, self._finish_error, exc)
            return
        self.root.after(0, self._finish_success, result.best.score, result.best.parameters, report_path, output)

    def _finish_success(
        self,
        score: float,
        parameters: ParameterValues,
        report_path: Path,
        output: Path,
    ) -> None:
        self.report_path = report_path
        self.plot_path = output / "spectrum-comparison.html"
        self.run_button.configure(state="normal")
        self.status_var.set("Done")
        self._log(f"Best score: {score:.8g}")
        for name, value in parameters.items():
            self._log(f"  {name}: {value:.8g}")
        self._log(f"Report: {report_path}")
        self._log(f"Plot: {self.plot_path}")

    def _finish_error(self, exc: Exception) -> None:
        self.run_button.configure(state="normal")
        self.status_var.set("Failed")
        self._log(f"ERROR: {exc}")
        messagebox.showerror("autoxmimsim", str(exc))

    def _open_plot(self) -> None:
        self._open_path(self.plot_path or Path(self.output_var.get()) / "spectrum-comparison.html")

    def _open_report(self) -> None:
        self._open_path(self.report_path or Path(self.output_var.get()) / "synthetic-recovery-report.html")

    def _open_path(self, path: Path) -> None:
        if not path.exists():
            messagebox.showinfo("autoxmimsim", f"File does not exist yet:\n{path}")
            return
        os.startfile(path)  # type: ignore[attr-defined]

    def _log(self, message: str) -> None:
        self.log.insert("end", message + "\n")
        self.log.see("end")


class ParameterRow:
    def __init__(
        self,
        parent: ttk.LabelFrame,
        grid_row: int,
        values: tuple[str, str, str, str, str],
        remove_callback,
    ) -> None:
        self.parent = parent
        self.remove_callback = remove_callback
        self.name = tk.StringVar(value=values[0])
        self.target = tk.StringVar(value=values[1])
        self.lower = tk.StringVar(value=values[2])
        self.upper = tk.StringVar(value=values[3])
        self.steps = tk.StringVar(value=values[4])
        self.widgets = (
            ttk.Entry(parent, textvariable=self.name, width=28),
            ttk.Entry(parent, textvariable=self.target, width=12),
            ttk.Entry(parent, textvariable=self.lower, width=12),
            ttk.Entry(parent, textvariable=self.upper, width=12),
            ttk.Entry(parent, textvariable=self.steps, width=8),
            ttk.Button(parent, text="Remove", command=lambda: remove_callback(self)),
        )
        self.grid(grid_row)

    def grid(self, row: int) -> None:
        for column, widget in enumerate(self.widgets):
            widget.grid(row=row, column=column, sticky="ew", padx=4, pady=3)

    def values(self) -> tuple[str, str, str, str, str]:
        return (
            self.name.get().strip(),
            self.target.get().strip(),
            self.lower.get().strip(),
            self.upper.get().strip(),
            self.steps.get().strip(),
        )

    def destroy(self) -> None:
        for widget in self.widgets:
            widget.destroy()
