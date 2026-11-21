# BioModelAgent

BioModelAgent exposes biological-network **construction, curation,
conversion and stochastic simulation** as a Scout workflow of **32 python
tasks** in two families:

- **NeKo** (17 tasks) — build and curate signed interaction networks from
  curated protein-interaction resources (OmniPath or SIGNOR).
- **MaBoSS** (15 tasks) — convert a network to a Boolean model, inspect and
  configure it, then run stochastic simulations, mutation analyses and
  trajectory plots. Includes `neko_export_bnet`, the bridge that hands a
  curated NeKo network to MaBoSS.

This workflow is a port of our previous MCP-based implementation,
[marcorusc/mcp-biomodelling-servers](https://github.com/marcorusc/mcp-biomodelling-servers.git).
The MCP servers' sessions were replaced by Scout's artifact-path chaining:
**a network is a SIF path, a model is a bundle path, and every task returns
the absolute path of the artifact it produced** — which is exactly the input
the next task takes.

## Using BioModelAgent

Load the workflow (Scout-AI loads it for agents as `BioModelAgent`; from
the CLI, `scout workflow task BioModelAgent <task> --help`).

```ruby
require './workflow'

sif = BioModelAgent.job(:neko_create_sif).run(
  genes: ["TP53", "MDM2", "MYC", "AKT1"], max_len: 2
)

report = BioModelAgent.job(:neko_network_report).run(sif_path: sif)
```

Per-task reference: **`doc/user/README.md`** — what agents receive when
loading BioModelAgent. Per-task signatures, inputs and semantics live in the
task docstrings under `python/tasks/` (they are the task `desc`, shown by
`--help`), not in this file.

## Environment

The python tasks execute under the **pymaboss micromamba environment**
(python 3.12). All scientific libraries come from that environment; this
repo holds only task code — `neko` 1.10.1 and `maboss` 0.8.16 (cmaboss
engine) are imported directly, nothing is reimplemented.

## Repository layout

| Path | Contents |
| --- | --- |
| `workflow.rb` | Workflow entrypoint: loads the python task files |
| `python/tasks/` | 32 task files + `neko_common.py`, `maboss_common.py` (shared helpers, no task) |
| `python/test/` | Python unit + smoke suites |
| `test/BioModelAgent/` | Ruby scout tests and the cross-family demo runner |
| `doc/user/` | Agent-facing reference (`README.md` is what agents get) |
| `doc/developer/` | Task authoring, task inventory, provenance of the port |
| `doc/*.md` | Port investigation and design records (how it was built) |
| `skills/` | Agent skills shipping with the repo |
| `mcp-biomodelling-servers/` | The upstream MCP servers (submodule, specification only) |
| `agentic_system_for_modelling/` | Upstream agentic system repo (submodule) |

## Testing

```bash
cd /bulk/mvazque2/git/workflows/BioModelAgent
PY=/home/mvazque2/software/micromamba/envs/pymaboss/bin/python
export PYTHONPATH="$HOME/.rvm/gems/ruby-3.3.1/gems/scout-rig-0.2.6/python"

# Python suites (hit OmniPath once each on a cold cache)
env -u SCOUT_JOB_FILES_DIR $PY python/test/test_tier1.py        # 20 tests
env -u SCOUT_JOB_FILES_DIR $PY python/test/test_tier2.py        # 22 tests
env -u SCOUT_JOB_FILES_DIR $PY python/test/test_maboss_tier1.py # 35 tests
env -u SCOUT_JOB_FILES_DIR $PY python/test/test_maboss_tier2.py # 25 tests

# Ruby scout tests (registration, input exposure, descriptions)
ruby test/BioModelAgent/tasks/test_neko_python_tasks_tier1.rb    # 3 tests / 26 assertions
ruby test/BioModelAgent/tasks/test_neko_python_tasks_tier2.rb    # 3 tests / 36 assertions
ruby test/BioModelAgent/tasks/test_maboss_python_tasks_tier1.rb  # 3 tests / 39 assertions
ruby test/BioModelAgent/tasks/test_maboss_python_tasks_tier2.rb  # 3 tests / 51 assertions

# The workflow registers all 32 tasks
ruby -I. -e "require './workflow'; puts BioModelAgent.tasks.length"  # => 32
```

## Provenance

Ported from
[mcp-biomodelling-servers](https://github.com/marcorusc/mcp-biomodelling-servers.git)
(NeKo + MaBoSS MCP servers) into native Scout python tasks. The port's
investigation and per-task design decisions are recorded in
`doc/neko_investigation.md`, `doc/neko_python_tasks.md`,
`doc/maboss_investigation.md` and `doc/maboss_python_tasks.md`; the full
MCP-tool disposition tables (what was ported, split, collapsed, dropped,
deferred) live in `doc/developer/TaskInventory.md`.

