# BioModelAgent — session-free NeKo port as Scout python tasks

BioModelAgent exposes the [NeKo](https://github.com/NeKo-Quant-Bio-Lab/NeKo)
network-building capability as 17 native Scout **python tasks** (8 Tier 1 + 9
Tier 2). It calls the `neko` library directly (pymaboss site-packages,
source-identical to the vendored `nekomata_packages/neko/`); it does **not**
call the MCP server and does **not** use any NeKo session concept.

The model is stateless artifact chaining: **networks circulate as SIF artifact
paths** between tasks; reports come back as `md` or `tsv` artifacts. Each task
returns the absolute path of the artifact it wrote, and that path is what the
next task takes as `sif_path`.

## History

An earlier, uncommitted 2-task proof of concept (`neko_create_sif` +
`neko_sif_report`) existed only in the working tree and was superseded by the
full port. `neko_sif_report` (a JSON report) survives as
**`neko_network_report`** (a Markdown report) — renamed and reworked; the
PoC's automatic bimodal/undefined edge removal on create was dropped in favour
of explicit curation chain steps. That PoC was never committed to git.

## Environment

| Component | Value |
| --- | --- |
| Python | pymaboss micromamba env, CPython 3.12.12 (`/home/mvazque2/software/micromamba/envs/pymaboss/bin/python`) — this interpreter executes the python tasks |
| neko | 1.10.1 (pymaboss site-packages; source-identical to `nekomata_packages/neko/`) |
| networkx / pandas | installed in the same env (used for graph reports / edgelist handling) |
| Ruby side | scout-rig 0.2.6 + scout-gear 10.13.1 (Ruby 3.3.1) |

Two operational consequences:

- **scout-rig 0.2.6 requires explicit `file:` on every `python_task`
  registration.** The implicit lookup calls `Open.readpath`
  (`lib/scout/workflow/python/task.rb:117`), which this runtime does not
  define; without `file:` loading the workflow fails with `NoMethodError`.
  All 17 registrations in `workflow.rb` pass
  `file: File.expand_path('python/tasks/<name>.py', __dir__)`.
- **OmniPath downloads on first use**: `neko` pulls the interaction resource
  through pypath (the MCP/`resources="omnipath"` default). First invocation of
  a network-building task on a cold cache downloads ~tens of MB and takes
  ~10 s+; afterwards a local cache makes rebuilds fast (~1–2 s). Tasks with
  `database="signor"` avoid OmniPath entirely.

## Per-task reference

Signatures below are exact (extracted from the task files' metadata; not
hand-typed). All network-returning tasks write `neko_network.sif`; report
filenames are given per task. Every task returns `str` — the absolute path of
its artifact.

### Tier 1

| Task | Signature | Output |
| --- | --- | --- |
| `neko_create_sif` | `genes: list[str]`, `database: str = "omnipath"`, `max_len: int = 1`, `path_policy: str = "one_shortest"`, `reuse_policy: str = "discovered_paths"`, `only_signed: bool = True`, `consensus: bool = True` | `neko_network.sif` |
| `neko_add_nodes` | `sif_path: pathlib.Path`, `genes: list[str]`, `database: str = "omnipath"`, `autoconnect: bool = True`, `only_signed: bool = True`, `consensus: bool = True` | `neko_network.sif` |
| `neko_remove_genes` | `sif_path: pathlib.Path`, `genes: list[str]`, `database: str = "omnipath"` | `neko_network.sif` |
| `neko_remove_interaction` | `sif_path: pathlib.Path`, `node_a: str`, `node_b: str`, `database: str = "omnipath"` | `neko_network.sif` |
| `neko_remove_bimodal_interactions` | `sif_path: pathlib.Path`, `database: str = "omnipath"` | `neko_network.sif` |
| `neko_network_report` | `sif_path: pathlib.Path` | `neko_report.md` |
| `neko_list_interactions` | `sif_path: pathlib.Path` | `neko_interactions.tsv` |
| `neko_find_paths` | `sif_path: pathlib.Path`, `source: str`, `target: str`, `maxlen: int = 3`, `database: str = "omnipath"` | `neko_paths.tsv` |

Details:

- **`neko_create_sif`** — build a signed interaction network from seed genes
  (`Network(genes, resources=database)` + `complete_connection`) and export
  SIF. `genes`: 2–20 unique non-empty symbols.
- **`neko_add_nodes`** — extend a SIF network with new genes
  (`add_node` per gene; `connect_nodes` when `autoconnect=True`).
- **`neko_remove_genes`** — remove genes from a SIF network (`remove_node`
  per gene; logs removed/missing counts).
- **`neko_remove_interaction`** — remove one edge between two nodes
  (`remove_edge(node_a, node_b)`).
- **`neko_remove_bimodal_interactions`** — drop edges with conflicting
  direction signs (`remove_bimodal_interactions`; logs removed count).
- **`neko_network_report`** — Markdown summary parsed directly from the SIF
  (no network object): node/edge counts, effect-token counts, top-10 degree
  nodes, references-present flag. Successor of the PoC's `neko_sif_report`
  (JSON) — note the rename and format change.
- **`neko_list_interactions`** — the full edge list as TSV
  (`source, effect, target, references`), parsed directly from the SIF.
- **`neko_find_paths`** — paths between two nodes (`print_my_paths` output
  parsed into `path_length / path / nodes` columns); validates that `source`
  and `target` are network nodes (`ValueError` otherwise).

### Tier 2

| Task | Signature | Output |
| --- | --- | --- |
| `neko_remove_undefined_interactions` | `sif_path: pathlib.Path`, `database: str = "omnipath"` | `neko_network.sif` |
| `neko_complete_connection` | `sif_path: pathlib.Path`, `database: str = "omnipath"`, `max_len: int = 2`, `path_policy: str = "one_shortest"`, `reuse_policy: str = "discovered_paths"`, `only_signed: bool = True`, `consensus: bool = True` | `neko_network.sif` |
| `neko_connect_targeted_nodes` | `sif_path: pathlib.Path`, `nodes: list[str]`, `strategy: str = "connect_subgroup"`, `max_len: int = 1`, `database: str = "omnipath"`, `only_signed: bool = True`, `consensus: bool = True` | `neko_network.sif` |
| `neko_bridge_components` | `sif_path: pathlib.Path`, `comp_a: list[str]`, `comp_b: list[str]`, `max_len: int = 2`, `mode: str = "OUT"`, `database: str = "omnipath"`, `only_signed: bool = True`, `consensus: bool = True` | `neko_network.sif` |
| `neko_filter_interactions` | `sif_path: pathlib.Path`, `effect: list[str] \| None = None`, `source: str \| None = None`, `target: str \| None = None` | `neko_filtered.tsv` |
| `neko_get_references` | `sif_path: pathlib.Path`, `node1: str`, `node2: str \| None = None` | `neko_references.tsv` |
| `neko_analyze_connectivity` | `sif_path: pathlib.Path` | `neko_connectivity.tsv` |
| `neko_analyze_gene_set` | `sif_path: pathlib.Path`, `genes: list[str]`, `connectivity: str = "weak"` | `neko_gene_set.md` |
| `neko_preview_connection_impact` | `sif_path: pathlib.Path`, `method: str = "hubs"`, `top_k: int = 10` | `neko_impact_preview.md` |

Details:

- **`neko_remove_undefined_interactions`** — drop edges whose effect token is
  `undefined`.
- **`neko_complete_connection`** — re-run connection completion on an existing
  network (this is the MCP `apply_global_connection` *complete* strategy,
  session-free).
- **`neko_connect_targeted_nodes`** — connect a set of nodes; `strategy` ∈
  `connect_subgroup` (default; connects members to each other) or
  `connect_to_upstream_nodes` (pulls upstream regulators in). The neko
  `depth`/`rank` knobs of `connect_to_upstream_nodes` are not exposed.
- **`neko_bridge_components`** — bridge two node sets with
  `connect_component(comp_A, comp_B, maxlen, mode)`, `mode` ∈ `OUT | IN | ALL`.
  Note neko semantics: after bridging, all remaining nodes are interconnected
  via `connect_subgroup`.
- **`neko_filter_interactions`** — filtered edge-list view (all supplied
  filters AND-ed; effect matching case-insensitive). The MCP `nodes`/
  `node_scope` variant is not ported; use `neko_get_references` for
  edges touching a node.
- **`neko_get_references`** — references for edges involving `node1` (both
  directions), or exactly between `node1` and `node2` when given.
- **`neko_analyze_connectivity`** — weakly connected components of the edge
  list via networkx; single-node components flagged isolated; sorted by size
  descending.
- **`neko_analyze_gene_set`** — presence/absence of requested genes, internal
  vs boundary edges, induced isolates, and the (`weak`|`strong`) component
  partition of the induced subgraph.
- **`neko_preview_connection_impact`** — non-mutating what-if: `hubs` ranks
  degree, `relax_max_len`/`unsigned` re-run `complete_connection` on a fresh
  in-memory copy and report the edge-count delta. Never writes a SIF.

Shared helper module (registers no task): `python/tasks/neko_common.py`
(`load_network`, `write_sif`, `files_dir`, `artifact_path`, `read_sif_rows`,
`write_tsv`, `write_md`, `capture_stdout`).

## Chaining demo (validated through the Scout workflow)

The core contract proven in work order B: a `pathlib.Path` input resolves a
previous job's `.files` artifact path natively. Five hops, each run through
`debug_task` on workflow `BioModelAgent` (clean recompute), feeding each
returned path into the next hop's `sif_path`:

| # | Task | Inputs | Returned path (abbreviated) | Lines | sha256 |
| --- | --- | --- | --- | --- | --- |
| P1 | `neko_create_sif` | `genes=["TP53","MDM2","MYC","AKT1"]`, `max_len=2`, `only_signed=false`, `consensus=false` | `…/neko_create_sif/Default_389f8fd3….sif.files/neko_network.sif` | 54 | `8972bf8c…03f8` |
| P2 | `neko_remove_bimodal_interactions` | `sif_path=P1` | `…/neko_remove_bimodal_interactions/Default_8599b1ca….sif.files/neko_network.sif` | 46 | `4503912b…9158` |
| P3 | `neko_remove_genes` | `sif_path=P2`, `genes=["AKT1"]` | `…/neko_remove_genes/Default_a2eefb99….sif.files/neko_network.sif` | 30 | `df1ca73b…fa34` |
| P4 | `neko_network_report` | `sif_path=P3` | `…/neko_network_report/Default_1fea32d3….md.files/neko_report.md` | 31 | `957d9ee2…49a19` |
| P5 | `neko_find_paths` | `sif_path=P3`, `source="MYC"`, `target="TP53"`, `maxlen=3` | `…/neko_find_paths/Default_4a30dc81….tsv.files/neko_paths.tsv` | 2 | `51f72f6e…4b257` |

(`…` abbreviates `~/.scout/var/jobs/BioModelAgent/<task>/`; UUIDs and full
hashes shortened but recognizable.) Line counts include comment/reference
lines. Equivalent scout CLI:

```bash
scout workflow task BioModelAgent neko_create_sif \
  --genes '["TP53","MDM2","MYC","AKT1"]' --max_len 2 \
  --only_signed false --consensus false
# …take the returned .files/neko_network.sif path and pass it as --sif_path to:
scout workflow task BioModelAgent neko_remove_bimodal_interactions --sif_path <P1>
scout workflow task BioModelAgent neko_remove_genes --sif_path <P2> --genes '["AKT1"]'
scout workflow task BioModelAgent neko_network_report --sif_path <P3>
scout workflow task BioModelAgent neko_find_paths --sif_path <P3 \
  --source MYC --target TP53 --maxlen 3
```

**Fidelity finding:** through the whole chain every surviving edge kept its
`# Reference PMID: …` line byte-identically; P2 ⊂ P1 and P3 ⊂ P2 as (edge,
reference) sets. Edge counts fell 27 → 23 data edges (bimodal removal −4,
AKT1 removal −8, of which 4 remained in the report set). The chain hops all
recomputed (`clean: true`) and no artifact-dir fallback was needed — job
`.files` paths resolve directly. One operational note: the sandboxed shell
cannot read `~/.scout/var/jobs` (no grant); inspect artifacts through the job
record or an unsandboxed probe, not plain `cat`.

**Seed-choice note:** the demo initially used `max_len=1`, which produced a
degenerate 1-edge network for these four seeds; `max_len=2` yields a
27-edge network. Pick seeds/max_len to suit; isolated seeds (genes with no
interaction at all) never appear in a SIF, since SIF carries only edges.

## Format contract

- **Networks: SIF.** Tasks declare `Extension: sif`; the result is the path
  text of `neko_network.sif`. Format:
  `# Reference PMID: <pmid>` line preceding each tab-separated
  `source\teffect\ttarget` row (effects observed: `stimulation`,
  `inhibition`, `form_complex`, `bimodal`, `undefined`).
- **Tables: scout TSV.** First line `#`-prefixed tab-separated header
  (`#source\teffect\ttarget\treferences`), then plain tab rows; no `#:`
  directives (scout-gear `user/ProcessingTabularData.md` convention).
- **Narrative reports: Markdown** (`neko_report.md`, `neko_gene_set.md`,
  `neko_impact_preview.md`).
- **Artifact directory:** `SCOUT_JOB_FILES_DIR` when scout runs the task;
  when absent (direct python invocation in tests) each task falls back to a
  fresh `tempfile.mkdtemp` and still returns a usable absolute path.
- **Stdout discipline:** task functions never print to stdout (it is scout's
  result channel); all neko output is captured and logged to `sys.stderr`.

## Testing

```bash
cd /bulk/mvazque2/git/workflows/BioModelAgent
PY=/home/mvazque2/software/micromamba/envs/pymaboss/bin/python
export PYTHONPATH="$HOME/.rvm/gems/ruby-3.3.1/gems/scout-rig-0.2.6/python"

# Python unit suites (no scout needed; hit OmniPath once each on a cold cache)
timeout 600 env -u SCOUT_JOB_FILES_DIR $PY python/test/test_tier1.py   # 20 tests
timeout 600 env -u SCOUT_JOB_FILES_DIR $PY python/test/test_tier2.py   # 22 tests

# Direct functional smoke harnesses (one call per task; tempfile fallback)
timeout 600 env -u SCOUT_JOB_FILES_DIR $PY python/test/smoke_tier1.py
timeout 600 env -u SCOUT_JOB_FILES_DIR $PY python/test/smoke_tier2.py

# Ruby-side scout tests (registration + input exposure + descriptions)
ruby test/BioModelAgent/tasks/test_neko_python_tasks_tier1.rb   # 3 tests / 26 assertions
ruby test/BioModelAgent/tasks/test_neko_python_tasks_tier2.rb   # 3 tests / 36 assertions

# Workflow loads with all 17 tasks
ruby -I. -e "require './workflow'; puts BioModelAgent.tasks.length"  # => 17
```

`test/test_helper.rb` (repo `test/`) is the shared Ruby harness the Ruby
test files load.

## MCP-source scope

Checked the registered tools in `mcp-biomodelling-servers/NeKo/server.py`
(27 `@tool` functions), `NeKo/tools/analysis.py` (2) and
`NeKo/tools/history.py` (4) — 33 in total.

- **Ported (session-free):** the 17 network/report operations above,
  including `apply_global_connection`'s *complete* strategy (as
  `neko_complete_connection` / the build step of `neko_create_sif`).
- **Dropped by design:** the whole session/history layer (9 `@tool`
  functions — `create_session`, `list_sessions`, `list_artifact_sessions`,
  `set_default_session`, `delete_session`, `list_network_history`,
  `navigate_network_history`, `compare_network_states`,
  `set_network_history_limit` — plus the session-scoped
  `network_history_resource` registration),
  `set_default_params`, `status`, `reset_network`, `list_bnet_files`,
  `clean_generated_files`. A stateless task chain replaces sessions with
  SIF artifact paths; history navigation is replaced by Scout job
  provenance.
- **Deferred:** the BNET branch of `export_network` (Boolean-network
  export; multi-file, requires full connectivity) and both handoffs
  (`export_neko_handoff`, `export_biomass_handoff`) — multi-file artifacts /
  cross-server handoffs, later tier; `apply_global_connection`'s radial and
  atopo strategies (heavy global strategies).

Limitations inherited from the PoC analysis stand: the inventory is the
registered NeKo tools, not all prompts/resources/helpers; syntax/metadata
checks do not prove external data availability or scientific validity; SIF
carries interactions, not all NeKo state (isolated seeds absent); an empty
edge export still creates a file. MCP options for database selection are
exposed per task (`database`), while MCP session options are not.
`neko_filter_interactions` omits the MCP `nodes`/`node_scope` variant (needs
the node table; use `neko_get_references`).
**Open question D4:** the requested "remove cycles" is currently served by
bimodal-conflict removal (`neko_remove_bimodal_interactions`); true
SCC-based cycle removal would be new functionality, not a port.

## Sources

- neko API: `nekomata_packages/neko/core/network.py` (vendored, read-only
  reference; the running copy is the pymaboss site-packages one, diffed
  source-identical); SIF export: `nekomata_packages/neko/_outputs/exports.py`.
- MCP registrations checked: `mcp-biomodelling-servers/NeKo/server.py`,
  `NeKo/tools/analysis.py`, `NeKo/tools/history.py`.
- PythonWorkflow conventions: scout-rig `doc/user/DefiningPythonTasks.md`
  (task authoring, `extension:`/`Extension:`).
- TSV convention: scout-gear `doc/user/ProcessingTabularData.md`.
- Port investigation (routes A/B, evidence, gotchas):
  `doc/neko_investigation.md`; per-task design decisions:
  `doc/neko_python_tasks.md`.
