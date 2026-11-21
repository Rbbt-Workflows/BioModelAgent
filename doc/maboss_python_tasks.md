# MaBoSS Scout tasks — decision record

Work order A (plan Steps 2–4) froze this task inventory after the probe
evidence in [maboss_investigation.md](maboss_investigation.md). The ported
specification is `mcp-biomodelling-servers/MaBoSS/server.py` (read-only); no
session layer, no MCP imports — every task calls the installed `maboss`
package directly (Route B).

## Conventions carried over from the NeKo PoC

- Registration: `BioModelAgent.python_task :name, file: File.expand_path(...)`
  (explicit `file:` — scout-rig 0.2.6 lacks `Open.readpath`).
- Every task file: module docstring; `sys.path.insert(0, dirname(abspath(__file__)))`;
  `from scout import task`; Google docstring with an `Extension:` line;
  one absolute `str` path returned; **nothing printed to stdout**.
- Artifacts go to `$SCOUT_JOB_FILES_DIR` via `neko_common.files_dir()` with a
  `tempfile.mkdtemp` fallback, so tasks run as plain functions too.

### Deviation from the NeKo convention (deliberate, evidence-backed)

**Module-level `import maboss` in every MaBoSS task file and in
`maboss_common`.** The work order's convention was "lazy imports inside the
function body". That is unsafe here: scout-rig 0.2.6 runs task bodies inside
an `atexit` handler (`runner.py::_scout_run_deferred`), and CPython 3.12
finalizes `sys.modules` before atexit bodies run, so a first-time
`import maboss` there fails with
`AttributeError: 'NoneType' object has no attribute 'thread_count'`
(cmaboss registers an atexit hook that imports
`concurrent.futures.thread` at shutdown). Importing `maboss` at module load
time — which scout-rig does in a normal-phase subprocess during metadata
extraction — caches every module so the atexit body only sees cache hits.
Measured cost: `--scout-metadata` extraction takes ~2.9 s per file either
way (`import maboss` is ~1.3 s of it), and scout-rig runs extraction once per
registration, not per job. Secondary libs (`pandas`, `matplotlib`, `neko`)
stay lazy in the bodies where they are used.

## Bundle representation (Step 2 decision)

See [maboss_investigation.md](maboss_investigation.md#design-decision-bundle-representation):
a **directory** with fixed names `model.bnd`/`model.cfg`; tasks return the
directory path. Scout passes `path`-typed params through **verbatim**
(scenario inputs are not rewritten), but the CLI runner hands the task a
`str`, not a `Path` — `maboss_common.load_bundle()` coerces internally so
every task is immune. Bundle-returning tasks declare `Extension: bnd` (the
directory path itself has no suffix and scout-rig wants a non-empty
extension).

Config tasks never mutate their input: they load, change, validate, and write
a **new** bundle directory. Step 5 checksum-asserts this.

## `get_simulation_result` disposition

**Collapsed into `maboss_run_simulation`.** P2 showed the run result exposes
exactly two natural tables (`get_states_probtraj`,
`get_last_states_probtraj`) plus node trajectories; a separate extractor task
would need a serialized "result object" artifact, which is session-state in
disguise. `maboss_run_simulation` returns the full state-probability
trajectory TSV (the superset; the last row is the final distribution), and
`maboss_simulate_mutation` returns the last-state comparison for WT vs
mutant. `get_last_nodes_probtraj`-style views can be derived from the TSV
with ordinary tsv tasks.

## Frozen inventory — all 24 MCP tools

| MCP tool | Disposition | Scout task | Shape |
|---|---|---|---|
| — (new bridge) | **new** | `neko_export_bnet` | sif_path → .bnet |
| `bnet_to_bnd_and_cfg` | port | `maboss_bnet_to_bnd_cfg` | bnet_path → bundle |
| `build_simulation` | collapse | internal `load_bundle()` | — |
| `import_neko_handoff` | drop (superseded by the direct bnet bridge) | — | — |
| `get_maboss_nodes` | port | `maboss_list_nodes` | bundle → tsv |
| `get_maboss_initial_state` | port | `maboss_get_initial_state` | bundle → tsv |
| `get_maboss_logical_rules` | port | `maboss_get_logical_rules` | bundle → tsv |
| `get_maboss_mutations` | port | `maboss_get_mutations` | bundle → tsv |
| `update_maboss_parameters` (inspect half) | port | `maboss_get_parameters` | bundle → tsv |
| `update_maboss_parameters` (update half) | port | `maboss_update_parameters` | bundle + params → bundle; empty params → tsv (dual, MCP-faithful) |
| `change_maboss_rule` | port | `maboss_change_rule` | bundle + node + rule → bundle |
| `set_maboss_output_nodes` | port | `maboss_set_output_nodes` | bundle + nodes → bundle |
| `set_maboss_initial_state` | port | `maboss_set_initial_state` | bundle + nodes + probs → bundle |
| `run_simulation` | port | `maboss_run_simulation` | bundle → tsv |
| `get_simulation_result` | collapse into `maboss_run_simulation` | — | — |
| `simulate_mutation` | port | `maboss_simulate_mutation` | bundle + nodes + state → tsv |
| `visualize_network_trajectories` | port | `maboss_plot_trajectories` | bundle + until → png |
| `export_maboss_bnd_cfg` | fold (the bundle **is** bnd+cfg) | — | — |
| `export_maboss_handoff` | defer (cross-server PhysiCell handoff, multi-file) | — | — |
| `create_session` | drop (session layer) | — | — |
| `list_sessions` | drop (session layer) | — | — |
| `list_artifact_sessions` | drop (session layer) | — | — |
| `set_default_session` | drop (session layer) | — | — |
| `delete_session` | drop (session layer) | — | — |
| `list_generated_files` | drop (Scout job `.files` dirs replace artifact dirs) | — | — |
| `clean_generated_files` | drop (Scout job `.files` dirs replace artifact dirs) | — | — |
| — (optional extra, cheap) | new | `maboss_check` | bundle → md |

Deviations from the tentative mapping in the plan (all logged here):

1. **`update_maboss_parameters` split into two tasks** — the MCP tool's
   no-arguments behavior is an inspect-only report, which returns a *TSV*,
   not a bundle. A dedicated inspect task `maboss_get_parameters`
   (bundle → tsv) was extracted so the report exists in the registered
   inventory. The update half stayed `maboss_update_parameters`, which also
   **retains the MCP's dual behavior for fidelity**: empty/absent
   `parameters` → inspect-only TSV report (`maboss_parameters.tsv`), any
   value → a new bundle (covered by
   `test_maboss_tier2.py::test_update_parameters_empty_inspects`). The
   honest consequence: that task's return type genuinely varies with the
   `parameters` input — bundle (`.bnd`) versus TSV — and its `Extension:`
   line records the bundle case; consumers relying on a stable extension
   should call `maboss_get_parameters` instead.
2. **`change_maboss_rule` validates with `sim.check()`** exactly like the
   spec (revert-on-invalid with the previous rule restored), rather than
   round-tripping through a reload. Same guarantee, one engine call.
3. **String inputs for list-shaped params** — scout passes `nodes: "A,B"` as
   one token; `parse_node_spec` splits on commas (JSON arrays still work),
   and `maboss_update_parameters` accepts both `k=v,k=v` pairs and a JSON
   object.

## Formats

| Artifact | Format |
|---|---|
| node/parameter/rule/mutation inspections | scout-convention TSV (`#`-header) |
| run trajectory, mutation comparison | scout-convention TSV |
| model bundles | directory + `model.bnd`/`model.cfg` (MaBoSS native) |
| models entering the chain | `.bnet` (BoolNet format from the NeKo bridge) |
| trajectory plot | PNG (Agg-forced matplotlib) |
| `sim.check()` report | markdown |

## Registration block (workflow.rb)

```ruby
# MaBoSS tasks (design note: doc/maboss_python_tasks.md). Same explicit file:
# convention as the NeKo block above.
BioModelAgent.python_task :neko_export_bnet, file: File.expand_path('python/tasks/neko_export_bnet.py', __dir__)
BioModelAgent.python_task :maboss_bnet_to_bnd_cfg, file: File.expand_path('python/tasks/maboss_bnet_to_bnd_cfg.py', __dir__)
BioModelAgent.python_task :maboss_list_nodes, file: File.expand_path('python/tasks/maboss_list_nodes.py', __dir__)
BioModelAgent.python_task :maboss_get_initial_state, file: File.expand_path('python/tasks/maboss_get_initial_state.py', __dir__)
BioModelAgent.python_task :maboss_get_logical_rules, file: File.expand_path('python/tasks/maboss_get_logical_rules.py', __dir__)
BioModelAgent.python_task :maboss_get_mutations, file: File.expand_path('python/tasks/maboss_get_mutations.py', __dir__)
BioModelAgent.python_task :maboss_get_parameters, file: File.expand_path('python/tasks/maboss_get_parameters.py', __dir__)
BioModelAgent.python_task :maboss_change_rule, file: File.expand_path('python/tasks/maboss_change_rule.py', __dir__)
BioModelAgent.python_task :maboss_update_parameters, file: File.expand_path('python/tasks/maboss_update_parameters.py', __dir__)
BioModelAgent.python_task :maboss_set_output_nodes, file: File.expand_path('python/tasks/maboss_set_output_nodes.py', __dir__)
BioModelAgent.python_task :maboss_set_initial_state, file: File.expand_path('python/tasks/maboss_set_initial_state.py', __dir__)
BioModelAgent.python_task :maboss_run_simulation, file: File.expand_path('python/tasks/maboss_run_simulation.py', __dir__)
BioModelAgent.python_task :maboss_simulate_mutation, file: File.expand_path('python/tasks/maboss_simulate_mutation.py', __dir__)
BioModelAgent.python_task :maboss_plot_trajectories, file: File.expand_path('python/tasks/maboss_plot_trajectories.py', __dir__)
BioModelAgent.python_task :maboss_check, file: File.expand_path('python/tasks/maboss_check.py', __dir__)
```

17 NeKo + 15 MaBoSS tasks = **32** (`ruby -I. -e "require './workflow'; puts
BioModelAgent.tasks.length"`).
