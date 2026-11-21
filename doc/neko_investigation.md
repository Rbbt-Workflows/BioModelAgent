# NeKo → BioModelAgent port: investigation notes

This document is self-contained: with it (plus the repository it describes) a
reader can author a new native Python task for this workflow, and decide
whether to reach the NeKo functionality through the MCP server package
(Route A) or the `neko` library directly (Route B). Everything stated here was
validated on this machine during the port (work orders A–C); sources are
quoted inline.

Companion documents:

- `doc/neko_python_tasks.md` — the per-task design decisions (task tables,
  dropped-tool rationale, D-add/D-defaults/D-reports/D-tsv/D-names).
- `README.md` — user-facing overview, per-task reference, the validated
  chaining demo.

## 1. How to author native Python tasks in Scout (PythonWorkflow)

### Mechanism, as validated here

1. **One plain Python file per task** under `python/tasks/`. The file is
   ordinary Python: top-level imports must be **stdlib + `from scout import
   task` only**. Heavy imports (`neko`, `pandas`, `networkx`) stay lazy inside
   function bodies — scout-rig re-runs each task file in a subprocess at
   registration time (and at every workflow load), so a top-level `import
   neko` costs ~0.4–0.5 s of import time *per registration, per load*. With 17
   tasks that is seconds of pure overhead on every `workflow.rb` load.
2. **The task is a type-annotated function decorated with `@task`:**

   ```python
   @task
   def neko_remove_genes(sif_path: pathlib.Path, genes: list[str],
                         database: str = "omnipath") -> str:
       """Remove genes from a SIF network.

       Extension: sif

       (Google-style docstring; Args/Returns sections below.)
       """
   ```

3. **Docstring → task metadata.** The docstring's first line becomes the task
   description; an `Args:` section supplies per-input help; a standalone
   `Extension: <suffix>` line sets the result filename suffix. Critical
   detail discovered during the port: the `Extension:` field is extracted
   from the **function's** docstring. In the first Tier 2 cut the field sat in
   the *module* docstring, and metadata extraction silently returned
   `extension: null` (Scout then falls back to its default suffix for the
   result type, which for these tasks is `.text`, not `.sif`/`.tsv`). Scout-rig
   0.2.6 `python/scout/runner.py` `_extract_extension()`:

   ```python
   for line in docstring.splitlines():
       if re.match(r"^\s*Extension:", line):
           ...
   ```

   It is applied to `inspect.getdoc(func)` — the function docstring. The
   contract is documented in scout-rig `doc/user/DefiningPythonTasks.md`
   §"extension": "A function may override it by adding one standalone
   `Extension:` field to its docstring".
4. **Registration in `workflow.rb`** — one explicit line per task, always with
   `file:`:

   ```ruby
   BioModelAgent.python_task :neko_remove_genes,
     file: File.expand_path('python/tasks/neko_remove_genes.py', __dir__)
   ```

   **`file:` is mandatory in this runtime.** scout-rig 0.2.6
   `lib/scout/workflow/python/task.rb` line 117:

   ```ruby
   file ||= Open.readpath(python_task_dir[name].find_with_extension('py'))
   ```

   The implicit lookup calls `Open.readpath`, which does **not exist** in this
   runtime (scout-gear 10.13.1 does not define it; verified in-process:
   `Open.respond_to?(:readpath) # => false`). Without `file:` the load dies
   with `NoMethodError: undefined method 'readpath' for Open:Module`.
5. **Artifacts.** Task bodies write files into the job's files directory and
   return the absolute path string as the task result:

   ```python
   import os, tempfile

   def files_dir():
       d = os.environ.get("SCOUT_JOB_FILES_DIR")
       if d: return d
       return tempfile.mkdtemp(prefix="neko_")   # direct-invocation fallback
   ```

   The tempfile fallback is what keeps every task directly callable from
   tests and the pymaboss REPL with no scout present.

### Environment evidence (validated)

- Python tasks execute under the **pymaboss micromamba env**:
  `/home/mvazque2/software/micromamba/envs/pymaboss/bin/python`, CPython
  3.12.12 (confirmed via `sys.executable` probe through the scout runner).
- `neko` 1.10.1 is importable there (resolves to pymaboss site-packages;
  see §3). `networkx` and `pandas` are installed there as well.
- `scout-rig 0.2.6` + `scout-gear 10.13.1` (Ruby 3.3.1); the scout python
  runner lives at
  `~/.rvm/gems/ruby-3.3.1/gems/scout-rig-0.2.6/python` and must be on
  `PYTHONPATH` when invoking task files directly.
- `mcp_biomodelling_servers` 2.4.0 imports standalone in pymaboss (Route A;
  see §2).

### Gotchas actually hit during the port

- **Stdout is the result channel.** scout-rig's runner decodes the task's
  stdout to reconstruct the return value; any stray `print()` corrupts it.
  Several neko methods print (`add_node`, `remove_edge`, `print_my_paths`,
  `connect_subgroup`, …). Every neko call in this workflow is wrapped in
  `capture_stdout(fn, *args, **kwargs)` (`python/tasks/neko_common.py`),
  which redirects stdout to an `io.StringIO` for the duration of the call and
  returns the captured text; tasks log it to `sys.stderr`. (WO-B caught one
  misuse where `capture_stdout` was treated as a context manager — it is a
  call-wrapper.)
- **`print_my_paths` prints Python list literals**, e.g.
  `['TP53', 'ESR1', 'MYC']` — one path per line, not arrow-separated text.
  `neko_find_paths` parses them with `ast.literal_eval` into
  `path_length / path / nodes` columns, with an arrow-line fallback kept.
- **`ruby workflow.rb` does nothing on its own.** A workflow file only
  declares; run tasks via `Probe.job(:task, name).run` / `scout workflow task`
  / `debug_task`, or the test helper.
- **Scout TSV convention** (scout-gear `doc/user/ProcessingTabularData.md`):
  first line is a `#`-prefixed tab-separated header, then plain tab-separated
  rows; no `#:` directives. All TSV-producing tasks here follow it via
  `write_tsv()` in `neko_common.py`.
- **`# Reference PMID:` lines precede each SIF row** (see §3 SIF format).
  `read_sif_rows()` pairs each data row with the reference line that precedes
  it.
- **Job `.files` directories are not readable from the sandboxed `bash`
  tool** (no read grant under `~/.scout/var/jobs`). Reading chain artifacts
  back requires the probe path-kind or the scout job record; the tasks
  themselves resolve each other's paths natively (proven across the 5-hop
  chain).

## 2. Route A: connecting via `mcp_biomodelling_servers`

### Import evidence (validated)

- `mcp_biomodelling_servers` **2.4.0 is installed in pymaboss** and imports
  standalone (`import mcp_biomodelling_servers` works with no sys.path
  surgery). It is the MCP server *framework* package the vendored server is
  built against.
- The vendored **NeKo server is not a pip package**. `import NeKo` only works
  after putting the vendored directory on `sys.path`:

  ```python
  sys.path.insert(0, "/bulk/mvazque2/git/workflows/BioModelAgent/mcp-biomodelling-servers")
  from NeKo.services import network_analysis   # dotted imports
  from NeKo import utils
  ```

  Importable that way (validated): `NeKo.services.network_analysis`,
  `NeKo.utils`, plus the modules `handoff`, `ode_handoff`,
  `artifact_manager` found under the vendored tree
  (`NeKo/services/…`), which import cleanly under their dotted names.
- `NeKo` is **not** installed as a distribution: `pip show NeKo` finds
  nothing; only the vendored checkout exists.

### Why the port did not use it

Every MCP *tool* function is welded to the session model. In
`mcp-biomodelling-servers/NeKo/server.py` there are **33 `@tool`-decorated
functions** (27 in `server.py`, 2 in `tools/analysis.py`, 4 in
`tools/history.py`; enumerated by AST over the `@tool(...)` decorators). Their
signatures take `session_id` and the MCP `ctx`, and resolve the Network
through `SessionManager` (`session_manager.py`: `get_session`,
`ensure_session`, `session_scope`, `snapshot`, …) — `grep session_id
NeKo/server.py` matches **91 lines**. Concretely, the coupling for a single
"remove one gene" operation is: tool function → `ctx` → `session_id` →
SessionManager lookup → network history snapshot → `network.remove_node` →
stdout capture lock (`_stdout_capture_lock`) → artifact manager bookkeeping.
Calling `NeKo` tools from a stateless scout task would mean either faking a
session per task invocation (a session model by the back door) or abandoning
the tool layer and importing the private helpers anyway.

The genuinely reusable pure helpers (`NeKo.services.network_analysis`
report/record builders, the handoff writers in `handoff`/`ode_handoff`)
duplicate little of what the tasks need: network manipulation is all in the
`neko` library underneath, and our SIF-parse reports are a few dozen lines of
plain Python. The handoff/artifact modules additionally assume the MCP
artifact-directory layout.

### What a future port could reuse from Route A, and under what conditions

- `NeKo.services.network_analysis` (`node_records`,
  `referenced_interaction_records`, `gene_set_components`, `edge_degrees`, …)
  — reusable if a future task wants MCP-shaped markdown reports with the same
  wording, provided it feeds them plain node/edge records instead of a
  session. They are presentation helpers, not network logic.
- `handoff` / `ode_handoff` — the deferred bnet/BioMASS handoff writers.
  Reusable when that tier is built, again decoupled from
  `artifact_manager`'s session-scoped layout.
- `NeKo.utils.format_*` guidance functions — output-shaping only.

None of these is needed for the current 17 tasks.

## 3. Route B (chosen): connecting directly to `neko`

- `import neko` in pymaboss resolves to
  `…/envs/pymaboss/lib/python3.12/site-packages/neko/` — distribution
  `neko`, version **1.10.1** in the package metadata. A file-by-file `diff`
  against the vendored `nekomata_packages/neko/` showed the installed copy is
  **source-identical** to the vendored one (same files, same bytes), so
  referencing either is equivalent; the installed copy avoids sys.path
  surgery and stays read-only-clean.
- Caveat noted for accuracy: `neko.__version__` is not set by the package
  (`AttributeError`); the 1.10.1 figure comes from the installed dist-info.

### The API surface we use (real signatures, neko 1.10.1, `inspect.signature`)

```python
Network.__init__(self, initial_nodes: list[str] = None, sif_file=None, resources=None)
Network.complete_connection(self, maxlen: Optional[int] = 2, algorithm=UNSET,
    minimal=UNSET, only_signed: bool = False, consensus: bool = False,
    connect_with_bias=UNSET, *, path_policy: Optional[PathPolicy] = None,
    reuse_policy: Optional[ReusePolicy] = None) -> None
Network.add_node(self, node: str, from_sif: bool = False) -> bool
Network.remove_node(self, node: str) -> None
Network.remove_edge(self, node1: str, node2: str) -> None
Network.connect_nodes(self, only_signed: bool = False, consensus_only: bool = False) -> None
Network.connect_component(self, comp_A, comp_B, maxlen: int = 2,
    mode: Literal['OUT','IN','ALL'] = 'OUT', only_signed: bool = False,
    consensus: bool = False) -> None
Network.connect_to_upstream_nodes(self, nodes_to_connect=None, depth: int = 1,
    rank: int = 1, only_signed: bool = True, consensus: bool = False) -> None
Network.connect_subgroup(self, group, maxlen: int = 1, only_signed: bool = False,
    consensus: bool = False) -> None
Network.remove_bimodal_interactions(self)
Network.remove_undefined_interactions(self)
Network.print_my_paths(self, node1: str, node2: str, maxlen: int = 2,
    genesymbol: bool = True) -> None
Network.convert_edgelist_into_genesymbol(self) -> pd.DataFrame
Exports.export_sif(self, file_name='logic_model.sif')
```

Key traps:

- **`Network(sif_file=...)` without `resources=` raises `TypeError`.** The
  MCP server never hit this because its sessions already held a `Network`
  object; a stateless task rebuilding a Network from a SIF must always supply
  the resource universe. This is why every SIF-loading task takes a
  `database` input (`"omnipath"` or `"signor"`; anything else →
  `ValueError`) — decision D-add.
- `complete_connection`'s `path_policy`/`reuse_policy` are keyword-only and
  take the string names (`"one_shortest"` / `"discovered_paths"`).
- `connect_component` does not only bridge the two components: after bridging
  it interconnects *all remaining* nodes via `connect_subgroup`.
- neko methods print to stdout (see §1 gotcha); wrap every call.

### SIF format (`Exports.export_sif`)

Export alternates a reference comment with each edge row:

```
# Reference PMID: 25893259
TP53	stimulation	MDM2
# Reference PMID: 7623821
MDM2	inhibition	TP53
```

(one TAB between columns; effect tokens observed: `stimulation`,
`inhibition`, `form_complex`, `bimodal`, `undefined`). `read_sif_rows()` in
`neko_common.py` parses this into `(source, effect, target, references)`
tuples, skipping other `#` comment lines.

### SIF round-trip fidelity findings (Steps 1 and 7)

- **References survive rewrites byte-identically.** Across the 5-hop chain
  (create → remove bimodal → remove gene → report → find paths) every
  surviving edge kept its original `# Reference PMID: …` string; the hop-2
  and hop-3 outputs were strict subsets of their inputs' (edge, reference)
  pairs.
- **Counts are stable**: reload via `Network(sif_file=..., resources=…)`
  reproduces the same node/edge counts as the file (verified by unittest
  round-trip tests).
- **Reloaded edgelist columns**: `network.convert_edgelist_into_genesymbol()`
  yields the standard columns (`source`, `target`, `effect`, plus reference
  columns) — used in tests to compare identity.
- **Isolated-seed caveat**: a seed gene with no interaction at all never
  appears in the SIF (SIF only carries edges). Reports derived from the SIF
  therefore cannot see isolated seeds; `add_nodes(autoconnect=True)` is the
  remedy. The old PoC README made the same observation.

### Recommendation

**Route B (`import neko` from pymaboss site-packages) for all network
manipulation.** Rationale: it is the same code the MCP server itself calls
(the server is a session/session-manager wrapper around `neko`); it is
source-identical to the vendored copy; it needs no sys.path surgery; and it
keeps the port free of the session coupling described in §2. Route A's pure
helpers are worth revisiting only when a future task wants MCP-shaped report
or handoff logic (see the conditions in §2).

## 4. Task inventory (final, 17 tasks)

Full input/output/API detail lives in `doc/neko_python_tasks.md` (Tier 1 and
Tier 2 tables) and in `README.md` (per-task reference with exact signatures).
Summary:

| Name | Tier | Output | neko / networkx API |
| --- | --- | --- | --- |
| `neko_create_sif` | 1 | sif | `Network(genes, resources=…)`, `complete_connection` |
| `neko_add_nodes` | 1 | sif | `add_node`, `connect_nodes` |
| `neko_remove_genes` | 1 | sif | `remove_node` |
| `neko_remove_interaction` | 1 | sif | `remove_edge` |
| `neko_remove_bimodal_interactions` | 1 | sif | `remove_bimodal_interactions` |
| `neko_network_report` | 1 | md | none (direct SIF parse) |
| `neko_list_interactions` | 1 | tsv | none (direct SIF parse) |
| `neko_find_paths` | 1 | tsv | `print_my_paths` |
| `neko_remove_undefined_interactions` | 2 | sif | `remove_undefined_interactions` |
| `neko_complete_connection` | 2 | sif | `complete_connection` |
| `neko_connect_targeted_nodes` | 2 | sif | `connect_subgroup` / `connect_to_upstream_nodes` |
| `neko_bridge_components` | 2 | sif | `connect_component` |
| `neko_filter_interactions` | 2 | tsv | none (direct SIF parse) |
| `neko_get_references` | 2 | tsv | none (direct SIF parse) |
| `neko_analyze_connectivity` | 2 | tsv | networkx `connected_components` |
| `neko_analyze_gene_set` | 2 | md | networkx induced subgraph, `isolates` |
| `neko_preview_connection_impact` | 2 | md | degree ranking; fresh-copy `complete_connection` |

`neko_common.py` (same directory) holds the shared helpers and registers no
task.

## 5. Dropped / deferred MCP tools, and open question D4

The full table with one-line rationales is in `doc/neko_python_tasks.md` §
"Dropped MCP tools". Summary of scope against the 33 `@tool` registrations
checked in `NeKo/server.py`, `NeKo/tools/analysis.py`,
`NeKo/tools/history.py`:

- **Dropped (by design):** the entire session/history layer — 9 `@tool`
  functions (`create_session`, `list_sessions`, `list_artifact_sessions`,
  `set_default_session`, `delete_session`, `list_network_history`,
  `navigate_network_history`, `compare_network_states`,
  `set_network_history_limit`) plus the session-scoped
  `network_history_resource` registration — and
  `set_default_params`, `status`, `reset_network`, `list_bnet_files`,
  `clean_generated_files`.
- **Deferred:** the BNET branch of `export_network` (Boolean-network export;
  multi-file, requires full connectivity) and both handoffs
  (`export_neko_handoff`, `export_biomass_handoff`) — multi-file artifacts and
  cross-server handoffs, later tier; `apply_global_connection`'s radial and
  atopo strategies (heavy global strategies). Its `complete` strategy *is*
  ported (`neko_complete_connection` and the build inside `neko_create_sif`).
- **Ported:** the remaining 17 network/report tools, session-free (see §4).

**Open question D4 ("remove cycles").** The user asked for "remove cycles";
the port implements *bimodal-conflict removal*
(`neko_remove_bimodal_interactions`) as the stand-in, because that is what
the MCP surface offers and what neko implements. True SCC-based cycle removal
would be **new functionality, not a port** (neko 1.10.1 has no
`remove_cycles`/SCC-removal method; networkx could provide
`strongly_connected_components` on the SIF edge list if the user wants it).
Decision needed from the user: keep the bimodal stand-in (current state) or
commission a new `neko_remove_cycles` task.

## Reproducing the evidence

```bash
cd /bulk/mvazque2/git/workflows/BioModelAgent
PY=/home/mvazque2/software/micromamba/envs/pymaboss/bin/python
export PYTHONPATH="$HOME/.rvm/gems/ruby-3.3.1/gems/scout-rig-0.2.6/python"

# neko API signatures (§3)
$PY -c "import inspect, neko.core.network as n; print(inspect.signature(n.Network.__init__))"

# Open.readpath absence (§1)
ruby -I. -e "require './workflow'; puts Open.respond_to?(:readpath)"   # false

# MCP tool count / session coupling (§2)
grep -c session_id mcp-biomodelling-servers/NeKo/server.py             # 91
$PY - <<'PY2'
import ast
files = ["NeKo/server.py", "NeKo/tools/analysis.py", "NeKo/tools/history.py"]
for p in files:
    for node in ast.parse(open("mcp-biomodelling-servers/"+p).read()).body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and \
           any(isinstance(d, ast.Call) and getattr(d.func, "id", None) == "tool"
               for d in node.decorator_list):
            print(p, node.name)
PY2
```
