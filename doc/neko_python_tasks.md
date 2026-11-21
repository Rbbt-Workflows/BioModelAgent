# NeKo → BioModelAgent port: python task design

This note records the design of the BioModelAgent python tasks that port the
NeKo MCP server (`mcp-biomodelling-servers/NeKo`) to scout tasks. The port
replaces the MCP session model with stateless scout tasks exchanging SIF file
artifacts: every network-returning task writes `neko_network.sif`, every report
task writes its own named artifact.

Environment facts driving the design (from the Step 1 environment report):

- Tasks run under the pymaboss python
  (`/home/mvazque2/software/micromamba/envs/pymaboss/bin/python`), where
  `neko` 1.10.1 is importable.
- `Network(sif_file=...)` requires a `resources=` argument; the MCP server
  could omit it only because its sessions already held a Network. Every task
  that loads a SIF therefore takes a `database` input.
- `python_task` registration must pass an explicit `file:` because scout-rig
  0.2.6 lacks `Open.readpath`, which the implicit lookup would call.
- scout TSV convention: first line is a `#`-prefixed tab-separated header,
  then plain tab rows; no `#:` directives.
- scout-rig re-runs each task file as a subprocess, so task files keep
  top-level imports to stdlib + `from scout import task`; neko/pandas imports
  are lazy inside function bodies. Task functions never print to stdout (it
  carries the result); logging goes to stderr.

## Tier 1 task table

| Name | Tier | Inputs (type = default) | Output (format, filename) | neko API called |
| --- | --- | --- | --- | --- |
| `neko_create_sif` | 1 | `genes: list[str]` (required), `database: str = "omnipath"`, `max_len: int = 1`, `path_policy: str = "one_shortest"`, `reuse_policy: str = "discovered_paths"`, `only_signed: bool = True`, `consensus: bool = True` | SIF, `neko_network.sif` | `Network(genes, resources=database)`, `complete_connection(...)` |
| `neko_add_nodes` | 1 | `sif_path: pathlib.Path` (required), `genes: list[str]` (required), `database: str = "omnipath"`, `autoconnect: bool = True`, `only_signed: bool = True`, `consensus: bool = True` | SIF, `neko_network.sif` | `Network(sif_file=..., resources=...)`, `add_node`, `connect_nodes` |
| `neko_remove_genes` | 1 | `sif_path: pathlib.Path` (required), `genes: list[str]` (required), `database: str = "omnipath"` | SIF, `neko_network.sif` | `Network(sif_file=...)`, `remove_node` |
| `neko_remove_interaction` | 1 | `sif_path: pathlib.Path` (required), `node_a: str` (required), `node_b: str` (required), `database: str = "omnipath"` | SIF, `neko_network.sif` | `Network(sif_file=...)`, `remove_edge` |
| `neko_remove_bimodal_interactions` | 1 | `sif_path: pathlib.Path` (required), `database: str = "omnipath"` | SIF, `neko_network.sif` | `Network(sif_file=...)`, `remove_bimodal_interactions` |
| `neko_network_report` | 1 | `sif_path: pathlib.Path` (required) | markdown, `neko_report.md` | none (parses the SIF file directly) |
| `neko_list_interactions` | 1 | `sif_path: pathlib.Path` (required) | TSV, `neko_interactions.tsv` | none (parses the SIF file directly) |
| `neko_find_paths` | 1 | `sif_path: pathlib.Path` (required), `source: str` (required), `target: str` (required), `maxlen: int = 3`, `database: str = "omnipath"` | TSV, `neko_paths.tsv` | `Network(sif_file=...)`, `print_my_paths` |


## Tier 2 task table

| Task | Tier | Inputs (types, defaults) | Output format + filename | neko/networkx API called |
| --- | --- | --- | --- | --- |
| `neko_remove_undefined_interactions` | 2 | `sif_path: pathlib.Path` (required), `database: str = "omnipath"` | SIF, `neko_network.sif` | `Network(sif_file=...)`, `remove_undefined_interactions` |
| `neko_complete_connection` | 2 | `sif_path: pathlib.Path` (required), `database: str = "omnipath"`, `max_len: int = 2`, `path_policy: str = "one_shortest"`, `reuse_policy: str = "discovered_paths"`, `only_signed: bool = True`, `consensus: bool = True` | SIF, `neko_network.sif` | `complete_connection(maxlen, path_policy, reuse_policy, only_signed, consensus)` — the former MCP `apply_global_connection` complete strategy, session-free |
| `neko_connect_targeted_nodes` | 2 | `sif_path: pathlib.Path` (required), `nodes: list[str]` (required), `strategy: str = "connect_subgroup"`, `max_len: int = 1`, `database: str = "omnipath"`, `only_signed: bool = True`, `consensus: bool = True` | SIF, `neko_network.sif` | `connect_subgroup(group=..., maxlen=..., only_signed=..., consensus=...)` or `connect_to_upstream_nodes(nodes_to_connect=..., only_signed=..., consensus=...)` |
| `neko_bridge_components` | 2 | `sif_path: pathlib.Path` (required), `comp_a: list[str]` (required), `comp_b: list[str]` (required), `max_len: int = 2`, `mode: str = "OUT"`, `database: str = "omnipath"`, `only_signed: bool = True`, `consensus: bool = True` | SIF, `neko_network.sif` | `connect_component(comp_A, comp_B, maxlen, mode, only_signed, consensus)` |
| `neko_filter_interactions` | 2 | `sif_path: pathlib.Path` (required), `effect: list[str] \| None = None`, `source: str \| None = None`, `target: str \| None = None` | TSV, `neko_filtered.tsv` | none (parses the SIF file directly) |
| `neko_get_references` | 2 | `sif_path: pathlib.Path` (required), `node1: str` (required), `node2: str \| None = None` | TSV, `neko_references.tsv` | none (parses the SIF file directly) |
| `neko_analyze_connectivity` | 2 | `sif_path: pathlib.Path` (required) | TSV, `neko_connectivity.tsv` | networkx `connected_components` on the undirected edge list |
| `neko_analyze_gene_set` | 2 | `sif_path: pathlib.Path` (required), `genes: list[str]` (required), `connectivity: str = "weak"` | markdown, `neko_gene_set.md` | networkx induced subgraph, `weakly/strongly_connected_components`, `isolates` |
| `neko_preview_connection_impact` | 2 | `sif_path: pathlib.Path` (required), `method: str = "hubs"`, `top_k: int = 10` | markdown, `neko_impact_preview.md` | degree ranking from the SIF parse; `relax_max_len`/`unsigned` load a fresh `Network(sif_file=...)` copy and call `complete_connection` on it without writing a SIF |

### neko signatures discovered for Tier 2 (neko 1.10.1)

- `connect_component(self, comp_A, comp_B, maxlen: int = 2, mode: Literal['OUT','IN','ALL'] = 'OUT', only_signed: bool = False, consensus: bool = False) -> None`
- `connect_to_upstream_nodes(self, nodes_to_connect=None, depth: int = 1, rank: int = 1, only_signed: bool = True, consensus: bool = False) -> None`
- `connect_subgroup(self, group, maxlen: int = 1, only_signed: bool = False, consensus: bool = False) -> None`

Task defaults (`only_signed=True`, `consensus=True`) intentionally differ
from the raw neko method defaults; they follow the MCP tool defaults, per
D-defaults. `neko_connect_targeted_nodes` does not expose `depth`/`rank`
to keep the input surface small. `neko_filter_interactions` implements the
`effect`/`source`/`target` variants only; the MCP `nodes`/`node_scope`
variant needs the network node table and is not ported —
`neko_get_references` covers the "edges touching a node" case.

## Dropped MCP tools

| MCP tool | Dropped because |
| --- | --- |
| All session/history tools (`create_session`, `list_sessions`, `list_artifact_sessions`, `set_default_session`, `delete_session` in `server.py`; `list_network_history`, `navigate_network_history`, `compare_network_states`, `set_network_history_limit` in `tools/history.py`; plus the `network_history_resource` registration) | No session concept in the port; state lives in SIF artifacts and scout jobs. |
| `set_default_params` | Defaults are explicit task inputs; there is no persistent client to hold defaults. |
| `status` | Scout job records already report status. |
| `reset_network` | No session to reset; rerun `neko_create_sif` instead. |
| BNET export (the `bnet` branch of `export_network`) and both handoffs `export_neko_handoff` / `export_biomass_handoff` | Multi-file artifacts and cross-server handoffs are deferred to a later tier. |
| `list_bnet_files`, `clean_generated_files` | Artifact-directory bookkeeping belongs to scout job files, not the workflow. |
| `apply_global_connection` (radial and atopo strategies) | Heavy global connection strategies; deferred beyond the shipped tiers. |

`apply_global_connection`'s `complete_connection` strategy is not dropped: it
is ported as `neko_create_sif`'s `complete_connection` call.

## Port-specific decisions

- **D-add — `database` input on every SIF-loading task.**
  `Network(sif_file=...)` raises `TypeError` without `resources=`, because the
  MCP server never needed it (its sessions held the Network). Values are
  `"omnipath"` or `"signor"`; anything else raises `ValueError`. Tasks that
  only parse the SIF file (`neko_network_report`, `neko_list_interactions`)
  do not take it.
- **D-defaults — keep MCP tool defaults, drop PoC auto-curation.**
  `only_signed=True` and `consensus=True` are the MCP defaults and stay the
  task defaults (the earlier PoC used `False`/`False`). Deviation from the
  PoC: `neko_create_sif` no longer auto-removes bimodal/undefined edges;
  curation is an explicit chain step via
  `neko_remove_bimodal_interactions` (undefined removal is Tier 2), so the raw
  build stays inspectable.
- **D-reports — direct parse vs graph algorithms.** Reports needing only the
  edge list (`neko_network_report`, `neko_list_interactions`) parse the SIF
  file directly and never import neko. Reports needing graph algorithms
  (paths; later connectivity/gene-set reports) load
  `Network(sif_file=..., resources=database)`.
- **D-tsv — scout TSV convention.** TSV outputs start with a `#`-prefixed
  tab-separated header line followed by plain tab rows; no `#:` directives.
- **D-names — artifact filenames.** Network-returning tasks all write
  `neko_network.sif`; reports use per-task filenames (`neko_report.md`,
  `neko_interactions.tsv`, `neko_paths.tsv`, …).

## Implementation notes

- `python/tasks/neko_common.py` holds the shared helpers (not a task file, no
  `@task` functions): `load_network`, `write_sif`, `files_dir`,
  `artifact_path`, `read_sif_rows`, `write_tsv`, `write_md`, `capture_stdout`.
  Task files bootstrap it with a `sys.path.insert(0, dirname(abspath(__file__)))`
  at module top (stdlib only, cheap).
- Artifacts go to `$SCOUT_JOB_FILES_DIR` when set; otherwise a
  `tempfile.mkdtemp` fallback keeps functions directly invokable in tests.
- SIF format (from `Exports.export_sif`): one `# Reference PMID: …` comment
  line immediately before each `source<TAB>effect<TAB>target` row; effect
  tokens are `stimulation`, `inhibition`, `form_complex`, `bimodal`,
  `undefined`.
- `neko_find_paths` captures the stdout of `print_my_paths`; the installed- stdout discipline: neko's `add_node`, `remove_edge` and `print_my_paths`
  print to stdout, which scout reserves for the task result. Task files call
  them through `capture_stdout` and route the captured text to stderr
  (`print_my_paths` output is parsed, not merely logged). A full sweep of
  every task with real stdout redirected confirmed zero stray stdout.
  neko 1.10.1 prints each path as a Python list literal of gene symbols
  (`['TP53', 'ESR1', 'MYC']`), which is parsed with `ast.literal_eval` into
  `path_length`/`path`/`nodes` rows (` -> `-separated lines are accepted as a
  fallback for other builds). The format was verified by probing
  `print_my_paths` on real fixtures, not guessed; warnings/errors are logged
  and skipped, and a no-path result writes a header-only table.
