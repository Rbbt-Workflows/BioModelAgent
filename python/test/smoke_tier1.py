"""Direct functional smoke test for the Tier 1 NeKo tasks.

Run with the pymaboss python:
  env -u SCOUT_JOB_FILES_DIR \
    /home/mvazque2/software/micromamba/envs/pymaboss/bin/python \
    python/test/smoke_tier1.py

SCOUT_JOB_FILES_DIR is intentionally left unset: every task must fall back to
a tempfile directory and still return a usable absolute path.
"""

import json
import os
import sys
from pathlib import Path

# The scout python runner lives in the scout-rig gem (not in the pymaboss
# site-packages); add it so the task files can `from scout import task`.
sys.path.insert(0, os.environ.get(
    "SCOUT_RIG_PYTHON",
    str(Path.home() / ".rvm/gems/ruby-3.3.1/gems/scout-rig-0.2.6/python"),
))

TASKS_DIR = Path(__file__).resolve().parent.parent / "tasks"
sys.path.insert(0, str(TASKS_DIR))

from neko_add_nodes import neko_add_nodes
from neko_create_sif import neko_create_sif
from neko_find_paths import neko_find_paths
from neko_list_interactions import neko_list_interactions
from neko_network_report import neko_network_report
from neko_remove_bimodal_interactions import neko_remove_bimodal_interactions
from neko_remove_genes import neko_remove_genes
from neko_remove_interaction import neko_remove_interaction

results = {}


def check(name, path, kind):
    path = Path(path)
    record = {"path": str(path), "exists": path.is_file()}
    if record["exists"]:
        text = path.read_text()
        record["non_empty"] = bool(text.strip())
        if kind == "sif":
            rows = [
                line
                for line in text.splitlines()
                if line.strip() and not line.startswith("#")
            ]
            record["rows"] = len(rows)
            record["three_cols"] = all(len(line.split("\t")) == 3 for line in rows)
        elif kind == "tsv":
            first = text.splitlines()[0] if text.splitlines() else ""
            record["header_hash"] = first.startswith("#")
            record["header_fields"] = first.lstrip("#").split("\t") if first else []
        elif kind == "md":
            record["has_heading"] = text.startswith("# ")
    results[name] = record
    return record


os.environ.pop("SCOUT_JOB_FILES_DIR", None)

# Fixture: validated 1-edge config from the plan's §7 probe.
fixture = neko_create_sif(
    ["TP53", "MYC"], max_len=1, only_signed=False, consensus=False
)
check("neko_create_sif", fixture, "sif")

report = neko_network_report(fixture)
check("neko_network_report", report, "md")

interactions = neko_list_interactions(fixture)
check("neko_list_interactions", interactions, "tsv")

# find_paths between the two fixture nodes (1-edge network).
try:
    paths = neko_find_paths(fixture, "TP53", "MYC", maxlen=1)
    check("neko_find_paths", paths, "tsv")
except Exception as exc:
    results["neko_find_paths"] = {"error": f"{type(exc).__name__}: {exc}"}

# Mutating tasks: keep the fixture pristine for later work orders.
import shutil
import tempfile

work = Path(tempfile.mkdtemp(prefix="neko_smoke_"))
local = work / "net.sif"
shutil.copy(fixture, local)

try:
    added = neko_add_nodes(str(local), ["EGFR"], autoconnect=False)
    check("neko_add_nodes", added, "sif")
except Exception as exc:
    results["neko_add_nodes"] = {"error": f"{type(exc).__name__}: {exc}"}

try:
    bimodal = neko_remove_bimodal_interactions(str(local))
    check("neko_remove_bimodal_interactions", bimodal, "sif")
except Exception as exc:
    results["neko_remove_bimodal_interactions"] = {"error": f"{type(exc).__name__}: {exc}"}

try:
    removed = neko_remove_genes(str(local), ["MYC", "NOT_PRESENT"])
    check("neko_remove_genes", removed, "sif")
except Exception as exc:
    results["neko_remove_genes"] = {"error": f"{type(exc).__name__}: {exc}"}

try:
    trimmed = neko_remove_interaction(str(local), "TP53", "MYC")
    check("neko_remove_interaction", trimmed, "sif")
except Exception as exc:
    results["neko_remove_interaction"] = {"error": f"{type(exc).__name__}: {exc}"}

# Validation checks (expected failures).
def expect_error(name, fn, *args, **kwargs):
    try:
        fn(*args, **kwargs)
        results[name] = {"validation": "NO ERROR RAISED (unexpected)"}
    except Exception as exc:
        results[name] = {"validation": f"raised {type(exc).__name__}: {exc}"}


expect_error(
    "validate_create_sif_bad_database",
    neko_create_sif,
    ["TP53", "MYC"],
    "bogus",
)
expect_error("validate_create_sif_too_few", neko_create_sif, ["TP53"])
expect_error(
    "validate_create_sif_duplicates", neko_create_sif, ["TP53", "TP53"]
)
expect_error(
    "validate_find_paths_missing_node", neko_find_paths, fixture, "TP53", "ZZZ9", 1
)
expect_error(
    "validate_load_network_missing_file", neko_network_report, "/no/such/file.sif"
)

print(json.dumps(results, indent=2))
