---
name: biomodel-network-construction
description: Build and curate signed biological interaction networks with BioModelAgent's NeKo tasks. Use when an agent must create a network from seed genes, add or remove genes/edges, remove bimodal or undefined interactions, connect or bridge nodes, or produce network reports (edge lists, paths, references, connectivity, gene-set audits). Covers the artifact-path chaining model (SIF path in, SIF path out), the curation order before Boolean conversion, OmniPath/SIGNOR database choice, and reading the resulting SIF/TSV/Markdown reports. Triggers neko_create_sif, neko_add_nodes, neko_remove_genes, neko_remove_interaction, neko_remove_bimodal_interactions, neko_remove_undefined_interactions, neko_complete_connection, neko_connect_targeted_nodes, neko_bridge_components, neko_network_report, neko_list_interactions, neko_find_paths, neko_filter_interactions, neko_get_references, neko_analyze_connectivity, neko_analyze_gene_set, neko_preview_connection_impact, interaction network, signed PPI, seed genes, SIF.
---

# Build and curate interaction networks (NeKo tasks)

## What this skill covers

Operational guidance for the 17 `neko_*` tasks: the chaining model, the
usual build → curate → inspect flow, and how to choose among the report
tasks. Per-task signatures, defaults and semantics are in the task
docstrings (`python/tasks/neko_*.py`) — the `desc` shown by
`scout workflow task BioModelAgent <task> --help` — and are not repeated
here. Format details live in `doc/user/README.md`.

## The chaining model

Every network task takes a SIF path in (`sif_path`) and returns the
absolute path of a **new** SIF. Networks are never held in memory across
calls and never mutated in place. Feed the returned path to the next task.
Keep the paths of intermediate networks: Scout job provenance is the
history mechanism (there are no sessions and no undo).

## The standard flow

1. **Build** — `neko_create_sif` from seed genes (2–20 unique symbols),
   or `neko_add_nodes` to extend an existing SIF. `max_len` 1 is compact;
   2 yields denser networks (more connector nodes, longer download on a
   cold OmniPath cache). `database="signor"` avoids OmniPath entirely.
2. **Curate toward a Boolean model** —
   `neko_remove_bimodal_interactions` (conflicting signs; **required**
   before `neko_export_bnet`), then optionally
   `neko_remove_undefined_interactions` (edges with no sign).
3. **Inspect at any point** — the report tasks below do not modify the
   network.
4. **Convert** — `neko_export_bnet` on the curated SIF (see the
   `biomodel-maboss-simulation` skill for what follows).

## Choosing report tasks

| Question | Task |
| --- | --- |
| Overview (nodes, edges, degrees, references present?) | `neko_network_report` (md) |
| All edges / a filtered view | `neko_list_interactions`, `neko_filter_interactions` (tsv) |
| Is there regulation A → B, and through what? | `neko_find_paths` |
| Literature evidence for an edge | `neko_get_references` |
| Is the network connected? | `neko_analyze_connectivity` |
| Which of my genes of interest are in it, and how do they sit? | `neko_analyze_gene_set` |
| What would relaxing parameters buy? | `neko_preview_connection_impact` (never writes a SIF) |

## Gotchas

- **OmniPath cold cache** downloads tens of MB on the first build; later
  calls are cached and fast.
- **Isolated seeds never appear in a SIF** — the format carries only
  edges; a gene with no interaction is simply absent.
- **An empty edge set still writes a file** — check `neko_network_report`
  counts before working with a tiny network.
- `neko_preview_connection_impact` is read-only: it never returns a SIF.
- After `neko_bridge_components`, remaining nodes are interconnected via
  `connect_subgroup` semantics (neko library behaviour).

## Reading the artifacts

- **SIF**: `# Reference PMID: …` lines interleaved with
  `source<TAB>effect<TAB>target` rows; effects `stimulation`,
  `inhibition`, `form_complex`, `bimodal`, `undefined`.
- **TSV** reports are scout-convention tables (header line starts with
  `#`); readable with Workspace `tsv_*` tasks.
