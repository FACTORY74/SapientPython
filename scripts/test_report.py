"""Pytest plugin for a concise, human-readable, one-line-per-case report."""

from __future__ import annotations

import inspect
import re
from pathlib import Path

import pytest


def pytest_addoption(parser: pytest.Parser) -> None:
    group = parser.getgroup("test report")
    group.addoption(
        "--test-report",
        metavar="PATH",
        help="Write a PASS/FAIL, name, and description line for every test case.",
    )


def pytest_configure(config: pytest.Config) -> None:
    if config.getoption("--test-report"):
        config.pluginmanager.register(ConciseTestReporter(config), "concise-test-reporter")


class ConciseTestReporter:
    def __init__(self, config: pytest.Config) -> None:
        self.path = Path(config.getoption("--test-report"))
        self.cases: dict[str, tuple[str, str]] = {}
        self.results: dict[str, str] = {}

    @pytest.hookimpl
    def pytest_collection_modifyitems(self, items: list[pytest.Item]) -> None:
        for item in items:
            name = _short_name(item.nodeid)
            obj = getattr(item, "obj", None)
            doc = inspect.getdoc(obj) if obj is not None else None
            description = doc.splitlines()[0] if doc else _humanize(item.originalname or item.name)
            self.cases[item.nodeid] = (name, _one_line(description))

    @pytest.hookimpl
    def pytest_runtest_logreport(self, report: pytest.TestReport) -> None:
        if report.when == "setup" and report.failed:
            self.results[report.nodeid] = "ERROR"
        elif report.when == "setup" and report.skipped:
            self.results[report.nodeid] = "SKIP"
        elif report.when == "call":
            if hasattr(report, "wasxfail"):
                self.results[report.nodeid] = "XFAIL" if report.skipped else "XPASS"
            elif report.passed:
                self.results[report.nodeid] = "PASS"
            elif report.failed:
                self.results[report.nodeid] = "FAIL"
            else:
                self.results[report.nodeid] = "SKIP"
        elif report.when == "teardown" and report.failed:
            self.results[report.nodeid] = "ERROR"

    @pytest.hookimpl
    def pytest_sessionfinish(self, session: pytest.Session) -> None:
        lines = []
        for nodeid, (name, description) in self.cases.items():
            status = self.results.get(nodeid, "NOT RUN")
            lines.append(f"{status:<7} | {name} | {description}")
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text("\n".join(lines) + "\n", encoding="utf-8")
        session.config.pluginmanager.get_plugin("terminalreporter").write_line(
            f"Concise test report written to {self.path}"
        )


def _short_name(nodeid: str) -> str:
    path, _, test = nodeid.partition("::")
    module = Path(path).stem.removeprefix("test_")
    test = test.removeprefix("test_")
    return f"{module}::{test}"


def _humanize(name: str) -> str:
    text = name.removeprefix("test_").replace("_", " ").strip()
    return text[:1].upper() + text[1:] + "."


def _one_line(text: str) -> str:
    return re.sub(r"\s+", " ", text).replace("|", "-").strip()
