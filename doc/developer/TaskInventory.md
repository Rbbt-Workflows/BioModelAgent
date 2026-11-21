# Task inventory and MCP port disposition

32 tasks: 17 NeKo + 15 MaBoSS. File names are `python/tasks/<task>.py`;
shared helpers `neko_common.py` / `maboss_common.py` register no task.

## NeKo tasks (17)

| Task | Extension | Purpose |
| --- | --- | --- |
| `neko_create_sif` | sif | Build a signed network from seed genes via `complete_connection` |
| `neko_add_nodes` | sif | Add genes to a network (optional autoconnect) |
| `neko_remove_genes` | sif | Remove genes and their edges |
| `neko_remove_interaction` | sif | Remove one edge A→B |
| `neko_remove_bimodal_interactions` | sif | Drop edges with conflicting signs |
| `neko_remove_undefined_interactions` | sif | Drop `undefined`-effect edges |
| `neko_complete_connection` | sif | Re-run connection completion on an existing network |
| `neko_connect_targeted_nodes` | sif | Connect a node set (`connect_subgroup` / `connect_to_upstream_nodes`) |
| `neko_bridge_components` | sif | Bridge two node sets (`OUT` / `IN` / `ALL`) |
| `neko_network_report` | md | Markdown summary of a SIF (counts, degrees, references) |
| `neko_list_interactions` | tsv | Full edge list (`source`, `effect`, `target`, `references`) |
| `neko_find_paths` | tsv | Paths between two nodes up to `maxlen` |
| `neko_filter_interactions` | tsv | Filtered edge-list view (effect / source / target) |
| `neko_get_references` | tsv | References for edges touching a node or node pair |
| `neko_analyze_connectivity` | tsv | Weak components and isolates |
| `neko_analyze_gene_set` | md | Gene-set audit (presence, internal/boundary edges, components) |
| `neko_preview_connection_impact` | md | Non-mutating what-if (hubs / relax_max_len / unsigned) |

## MaBoSS tasks (15)

| Task | Extension | Purpose |
| --- | --- | --- |
| `neko_export_bnet` | bnet | SIF → BoolNet `.bnet` (the NeKo→MaBoSS bridge; raises on bimodal networks) |
| `maboss_bnet_to_bnd_cfg` | bnd | `.bnet` → model bundle |
| `maboss_list_nodes` | tsv | All nodes and output flags |
| `maboss_get_initial_state` | tsv | Initial-state probabilities |
| `maboss_get_logical_rules` | tsv | Node → logical rule |
| `maboss_get_mutations` | tsv | Current mutations |
| `maboss_get_parameters` | tsv | Current parameters |
| `maboss_change_rule` | bnd | Replace a node's rule (new bundle) |
| `maboss_update_parameters` | bnd | Set parameters (`k=v,...`; empty string → parameters report) |
| `maboss_set_output_nodes` | bnd | Set output nodes (new bundle) |
| `maboss_set_initial_state` | bnd | Set initial state (three accepted forms; new bundle) |
| `maboss_run_simulation` | tsv | Stochastic simulation; state probabilities over time |
| `maboss_simulate_mutation` | tsv | WT vs mutant comparison |
| `maboss_plot_trajectories` | png | Trajectory plot (Agg backend) |
| `maboss_check` | md | `sim.check()` rendered as Markdown |

## Upstream MCP tool disposition

Ported from
[mcp-biomodelling-servers](https://github.com/marcorusc/mcp-biomodelling-servers.git)
(NeKo server: 33 registered tools; MaBoSS server: 24). Session management
and server-side state were dropped by design; Scout job provenance and
artifact paths replace them.

**NeKo** — ported: network build/edit/curation/connection operations and
the reports above (including `apply_global_connection`'s *complete*
strategy as `neko_complete_connection`). Dropped: the session/history layer
(9 tools), `set_default_params`, `status`, `reset_network`,
`list_bnet_files`, `clean_generated_files`. Deferred: BNET branch of
`export_network`, both handoffs (`export_neko_handoff`,
`export_biomass_handoff`), radial/atopo global strategies.

**MaBoSS** — ported: `bnet_to_bnd_and_cfg`, the five inspectors,
`change_maboss_rule`, `set_maboss_output_nodes`, `set_maboss_initial_state`,
`run_simulation` (with `get_simulation_result` collapsed in),
`simulate_mutation`, `visualize_network_trajectories`. Split:
`update_maboss_parameters` → `maboss_get_parameters` +
`maboss_update_parameters`. Folded: `export_maboss_bnd_cfg` (the bundle is
bnd+cfg). Dropped: 5 session tools, `import_neko_handoff` (superseded by
`neko_export_bnet`), `list_generated_files`, `clean_generated_files`.
Deferred: `export_maboss_handoff` (PhysiCell).

New tasks with no MCP counterpart: `neko_export_bnet` (replaces
`import_neko_handoff`) and `maboss_check` (`sim.check()`).
