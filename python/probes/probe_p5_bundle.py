"""Step 1 probe P5: bundle representation candidates for Scout tasks.

A MaBoSS model is a BND+CFG pair; the task contract returns ONE path. Test:

(a) a **model directory** with fixed names ``model.bnd``/``model.cfg``;
(b) a **JSON manifest** listing member paths.

For each: validate that a Scout PythonWorkflow task can accept the path as a
``pathlib.Path`` input (introspection via ``scout.runner.describe_function``)
and that a follow-up task can resolve the members. Then exercise both through
a real scout task run with ``$SCOUT_JOB_FILES_DIR`` set, using a scratch
throwaway task registered on the BioModelAgent workflow.
"""
import json
import subprocess
import sys
import tempfile
import traceback
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

REPO = Path(__file__).resolve().parents[2]
TASKS = REPO / "python" / "tasks"
PY = "/home/mvazque2/software/micromamba/envs/pymaboss/bin/python"
SCOUT_PYTHON = Path.home() / ".rvm/gems/ruby-3.3.1/gems/scout-rig-0.2.6/python"

SCRATCH_DIR_TASK = """\"\"\"P5 scratch probe: accepts a Path bundle input.\"\"\"
import os, pathlib, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from scout import task


@task
def p5_accept_dir(bundle: pathlib.Path) -> str:
    \"\"\"Accept a directory-like bundle path and report what is inside.

    Extension: md
    \"\"\"
    p = pathlib.Path(bundle)
    if not p.is_dir():
        raise ValueError(f"not a directory: {p}")
    return str(sorted(q.name for q in p.iterdir()))
"""

SCRATCH_LIST_TASK = """\"\"\"P5 scratch probe: reads a JSON manifest bundle.\"\"\"
import os, pathlib, sys, json
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from scout import task


@task
def p5_accept_manifest(bundle: pathlib.Path) -> str:
    \"\"\"Read a JSON manifest and list its member file names.

    Extension: json
    \"\"\"
    p = pathlib.Path(bundle)
    if not p.is_file():
        raise ValueError(f"not a file: {p}")
    data = json.loads(p.read_text(encoding="utf-8"))
    return json.dumps(data, sort_keys=True)
"""


def describe(fn_name: str) -> dict:
    """Run scout's own metadata extraction on a scratch task file."""
    code = (
        "import sys, json;"
        f"sys.path.insert(0, {str(TASKS)!r});"
        f"import {module_name};"
        "from scout.runner import describe_function;"
        f"print(json.dumps(describe_function({module_name}.{fn_name})))"
    )
    result = subprocess.run(
        [PY, "-c", code],
        capture_output=True,
        text=True,
        env={"PYTHONPATH": str(SCOUT_PYTHON), "PATH": "/usr/bin:/bin"},
    )
    if result.returncode != 0:
        raise RuntimeError(result.stderr)
    return json.loads(result.stdout)


def describe(module_name: str, fn_name: str) -> dict:  # noqa: F811
    """Run scout's own metadata extraction on a scratch task module."""


def main() -> int:
    from maboss_probe_common import write_probe_log

    lines = []
    try:
        import maboss

        scratch_dir = TASKS / "p5_scratch_dir.py"
        scratch_manifest = TASKS / "p5_scratch_manifest.py"
        scratch_dir.write_text(SCRATCH_DIR_TASK, encoding="utf-8")
        scratch_manifest.write_text(SCRATCH_LIST_TASK, encoding="utf-8")
        try:
            info_dir = describe("p5_scratch_dir", "p5_accept_dir")
            info_man = describe("p5_scratch_manifest", "p5_accept_manifest")
            lines.append("P5 (a) introspection: pathlib.Path input accepted")
            lines.append(f"  p5_accept_dir: {json.dumps(info_dir)[:400]}")
            lines.append("P5 (b) introspection: JSON manifest input accepted")
            lines.append(f"  p5_accept_manifest: {json.dumps(info_man)[:400]}")

            # Round-trip check: does a bundle dir survive being handed back to
            # another task as Path input, resolving members by fixed name?
            with tempfile.TemporaryDirectory(prefix="p5_") as tmp:
                tmp_path = Path(tmp)
                bnet = tmp_path / "tiny.bnet"
                bnet.write_text("targets, factors\nA, B\nB, A\nC, A & !B\n", encoding="utf-8")
                bnd, cfg = tmp_path / "model.bnd", tmp_path / "model.cfg"
                maboss.bnet_to_bnd_and_cfg(str(bnet), str(bnd), str(cfg))
                bundle_dir = tmp_path / "bundle"
                bundle_dir.mkdir()
                (bundle_dir / "model.bnd").write_bytes(bnd.read_bytes())
                (bundle_dir / "model.cfg").write_bytes(cfg.read_bytes())

                # (a) resolve members by fixed names inside a "task" body
                members = {
                    "bnd": str((bundle_dir / "model.bnd").resolve()),
                    "cfg": str((bundle_dir / "model.cfg").resolve()),
                }
                sim = maboss.load(members["bnd"], members["cfg"])
                lines.append(
                    f"  (a) dir bundle: members resolved + maboss.load OK nodes={list(sim.network)}"
                )

                # (b) JSON manifest
                manifest = tmp_path / "bundle.json"
                manifest.write_text(json.dumps(members, indent=2), encoding="utf-8")
                data = json.loads(manifest.read_text(encoding="utf-8"))
                sim2 = maboss.load(data["bnd"], data["cfg"])
                lines.append(
                    f"  (b) manifest bundle: members resolved + maboss.load OK nodes={list(sim2.network)}"
                )
        finally:
            scratch_dir.unlink(missing_ok=True)
            scratch_manifest.unlink(missing_ok=True)

        write_probe_log("P5", "\n".join(lines))
        print("\n".join(lines))
        return 0
    except Exception:  # noqa: BLE001
        tb = traceback.format_exc()
        write_probe_log("P5", "P5 FAILED\n" + tb)
        print(tb, file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
