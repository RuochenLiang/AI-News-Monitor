from __future__ import annotations

import importlib
import sys
from collections.abc import Iterable
from dataclasses import dataclass

RuntimeDependency = tuple[str, str]

RUNTIME_DEPENDENCIES: tuple[RuntimeDependency, ...] = (
    ("PySide6", "PySide6"),
    ("feedparser", "feedparser"),
    ("httpx", "httpx"),
    ("bs4", "beautifulsoup4"),
    ("yaml", "PyYAML"),
    ("dotenv", "python-dotenv"),
)


@dataclass(frozen=True)
class DependencyReport:
    missing: list[str]
    python_executable: str
    in_virtualenv: bool

    @property
    def ok(self) -> bool:
        return not self.missing


def check_runtime_dependencies(
    dependencies: Iterable[RuntimeDependency] = RUNTIME_DEPENDENCIES,
) -> DependencyReport:
    missing = []
    for import_name, package_name in dependencies:
        try:
            importlib.import_module(import_name)
        except Exception:
            missing.append(package_name)
    return DependencyReport(missing=missing, python_executable=sys.executable, in_virtualenv=_in_virtualenv())


def dependency_guidance(report: DependencyReport) -> str:
    if report.ok:
        return "All required runtime dependencies are installed."
    lines = [
        "Missing required runtime dependencies:",
        *[f"- {name}" for name in report.missing],
        "",
        "Run: python -m pip install -r requirements.txt",
        f"Python executable: {report.python_executable}",
        f"Virtual environment: {'yes' if report.in_virtualenv else 'no'}",
    ]
    return "\n".join(lines)


def assert_runtime_dependencies(
    dependencies: Iterable[RuntimeDependency] = RUNTIME_DEPENDENCIES,
) -> None:
    report = check_runtime_dependencies(dependencies)
    if not report.ok:
        raise RuntimeError(dependency_guidance(report))


def _in_virtualenv() -> bool:
    return sys.prefix != getattr(sys, "base_prefix", sys.prefix)
