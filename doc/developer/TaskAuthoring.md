# Task authoring in BioModelAgent

All 32 tasks are **PythonWorkflow tasks**: one python file per task under
`python/tasks/`, loaded by `workflow.rb`, each registering exactly one
scout task through the `scout.task` decorator. The scientific behaviour
lives entirely in the imported libraries (`neko`, `maboss`); task files are
thin adapters.

## Anatomy of a task file

```python
"""One-line summary.

Optional longer description of what the task does and any caveats.
"""

import os
import pathlib
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from scout import task


@task
def neko_example(sif_path: pathlib.Path, database: str = "omnipath") -> str:
    """Human summary shown as the task description.

    Extension: sif

    Longer description...

    Args:
        sif_path: Path to an existing network SIF.
        database: Resource universe; "omnipath" or "signor".

    Returns:
        Absolute path of the written artifact.
    """
    from neko_common import log, write_sif   # lazy imports inside the body

    ...
    return str(path)
```

Rules this repo follows:

- **One task per file**, file name = task name = function name
  (`neko_create_sif.py` → task `neko_create_sif`). The two `*_common.py`
  modules register no task.
- **Docstring is the documentation.** The preamble is the task `desc`
  (shown by `--help`); a standalone `Extension: <ext>` line sets the result
  suffix; `Args:` entries document inputs. Do not duplicate this in the
  README.
- **Paths in, path out.** File inputs are annotated `pathlib.Path` (Scout
  resolves a previous job's artifact path); the function returns `str` — the
  absolute path of the artifact it wrote.
- **Extension contract.** Networks `sif`; tables `tsv`; reports `md`; plots
  `png`; bundles declare `bnd` (directory of `model.bnd`+`model.cfg`).
- **Artifacts** go to `SCOUT_JOB_FILES_DIR` when set, else a
  `tempfile.mkdtemp` fallback (so tests run without scout).
- **Never print to stdout** (it is scout's result channel); use the shared
  `log()` helper, which writes to stderr.
- **Errors**: raise `ScoutTaskError` (or a builtin such as `ValueError`/
  `FileNotFoundError`) with an actionable message; never return a
  half-written artifact as success.
- **Import discipline.** NeKo tasks import `neko` lazily inside the function
  (metadata extraction stays fast). **MaBoSS tasks must `import maboss` at
  module level** — scout-rig 0.2.6 runs task bodies in an `atexit` handler
  and a first-time import there dies on CPython 3.12 (see
  [EnvironmentNotes](EnvironmentNotes.md)).
- **Never mutate inputs.** Every task writes its own artifact; a bundle
  configuration task copies the bundle and returns the new directory.

## Registration

`workflow.rb` registers each task explicitly. As of scout-rig 0.2.6 every
registration must pass `file:` explicitly (the implicit lookup crashes; see
[EnvironmentNotes](EnvironmentNotes.md)). Note the latest commit
"Remove cruft. Python tasks should load automatically" — python tasks under
`python/tasks/` now load automatically on workflow load; check
`workflow.rb` (currently the empty-registration form) for the live pattern
and keep new tasks consistent with it.

Check registration after adding a file:

```bash
ruby -I. -e "require './workflow'; puts BioModelAgent.tasks.length"   # 32 today
scout workflow task BioModelAgent --list
scout workflow task BioModelAgent <new_task> --help
```

## Shared helpers

- `python/tasks/neko_common.py` — `load_network` (SIF→`Network`), `write_sif`,
  `validate_database`, `files_dir`, `artifact_path`, `read_sif_rows`,
  `write_tsv`, `write_md`, `capture_stdout`, `log`.
- `python/tasks/maboss_common.py` — `validate_bundle_path`, `load_bundle`,
  `save_bundle`, `parse_node_spec`, `parse_initial_state`,
  `parse_state_string`, `require_nodes`, `import_agg_matplotlib`,
  `dataframe_to_tsv`; reuses `neko_common` for paths/TSV/MD/log.

Both modules are importable without scout (tests run them directly); they
use `sys.path.insert` in the task file to find each other.

## Testing a new task

Pair every task with tests on both sides:

1. **Python unit + smoke** under `python/test/` (run with the pymaboss
   python, `env -u SCOUT_JOB_FILES_DIR`): correct outputs, error paths,
   non-mutation (sha256 of inputs).
2. **Ruby scout test** under `test/BioModelAgent/tasks/` following
   `test_neko_python_tasks_tier1.rb`: registration, metadata loads
   (description + extension), and the python suite passes.

Full commands are in the README's Testing section.
