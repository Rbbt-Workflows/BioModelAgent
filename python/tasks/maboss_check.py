"""Run pyMaBoSS's network consistency check over a model bundle."""
import os
import pathlib
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import maboss  # noqa: F401  module load: scout-rig runs task bodies in atexit

from scout import task


@task
def maboss_check(bundle: pathlib.Path) -> str:
    """Run ``sim.check()`` and report the findings as Markdown.

    Extension: md

    Cheap optional extra beyond the MCP tool inventory: pyMaBoSS ships a
    ``check()`` diagnostic that reports node issues (e.g. nodes that are
    never updated or referenced). The MCP server never exposed it; exposing
    it here gives the demo chain a pre-flight gate before a run. The report
    is narrative, so it is Markdown rather than TSV.

    Args:
        bundle: Bundle directory (``model.bnd``/``model.cfg``).

    Returns:
        Absolute path of the Markdown artifact (``maboss_check.md``).

    Raises:
        FileNotFoundError: If the bundle is missing.
        ValueError: If ``check()`` raises.
    """
    from maboss_common import artifact_path, load_bundle, log, write_md

    simulation = load_bundle(bundle)
    try:
        findings = simulation.check()
    except Exception as exc:  # noqa: BLE001 - surfaced as a task error
        raise ValueError(f"MaBoSS check failed: {exc}") from exc

    log(f"[maboss_check] {findings!r}")
    lines = []
    if not findings:
        lines += ["The model reported no issues.", ""]
    elif isinstance(findings, str):
        lines += [findings, ""]
    elif isinstance(findings, dict):
        lines += ["| finding | detail |", "| --- | --- |"]
        for key, value in findings.items():
            lines.append(f"| {key} | {value} |")
        lines.append("")
    else:
        for item in findings:
            lines.append(f"- {item}")
        lines.append("")
    return write_md(artifact_path("maboss_check.md"), "MaBoSS model check", lines)
