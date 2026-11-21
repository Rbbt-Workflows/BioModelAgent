# Using BioModelAgent

BioModelAgent builds, curates, converts and simulates biological network
models. It is a Scout workflow of 32 python tasks in two families: **NeKo**
(interaction networks) and **MaBoSS** (Boolean models and stochastic
simulation), connected by the `neko_export_bnet` bridge. It was ported from
our previous MCP servers,
[mcp-biomodelling-servers](https://github.com/marcorusc/mcp-biomodelling-servers.git);
the MCP session layer was replaced by **artifact paths** — there are no
sessions to manage.

## The one rule: everything is a path

Each task takes paths in, and returns the absolute path of the artifact it
wrote. That returned path is the input of the next task. Nothing is held in
memory across calls.

| Artifact | Format | Path ends in | Tasks that take it |
| --- | --- | --- | --- |
| Interaction network | SIF | `.sif` | any `neko_*` task with `sif_path` |
| Boolean model | BND+CFG **bundle** | `model.bnd`/`model.cfg` dir | any `maboss_*` task with `bundle` |
| BoolNet model | `.bnet` | `.bnet` | `maboss_bnet_to_bnd_cfg` (`bnet_path`) |
| Tables | scout TSV | `.tsv` | Workspace `tsv_*` tasks |
| Reports | Markdown | `.md` | reading |
| Plot | PNG | `.png` | reading |

A **bundle** is one directory holding fixed members `model.bnd` (logical
rules) and `model.cfg` (parameters, initial state, outputs). A
bundle-returning task returns the directory path; configuration tasks write
a **new** bundle and never modify the input bytes.

## Quick start

Seeds → curated Boolean model → simulation:

```ruby
sif = BioModelAgent.job(:neko_create_sif).run(
  genes: ["TP53", "MDM2", "MYC", "AKT1"], max_len: 2
)
sif = BioModelAgent.job(:neko_remove_bimodal_interactions).run(sif_path: sif)
bnet = BioModelAgent.job(:neko_export_bnet).run(sif_path: sif)     # raises if bimodal
bundle = BioModelAgent.job(:maboss_bnet_to_bnd_cfg).run(bnet_path: bnet)
bundle = BioModelAgent.job(:maboss_set_output_nodes).run(bundle: bundle, nodes: ["TP53","MDM2"])
bundle = BioModelAgent.job(:maboss_update_parameters).run(
  bundle: bundle, parameters: "max_time=10,time_tick=1,sample_count=5000"
)
probtraj = BioModelAgent.job(:maboss_run_simulation).run(bundle: bundle)
```

Or from the CLI, chaining by hand:

```bash
scout workflow task BioModelAgent neko_create_sif \
  --genes '["TP53","MDM2","MYC","AKT1"]' --max_len 2
scout workflow task BioModelAgent neko_remove_bimodal_interactions --sif_path <sif-path>
scout workflow job BioModelAgent neko_export_bnet --sif_path <sif-path>
scout workflow task BioModelAgent maboss_bnet_to_bnd_cfg --bnet_path <bnet-path>
scout workflow task BioModelAgent maboss_set_output_nodes \
  --bundle <bundle> --nodes '["TP53","MDM2"]'
scout workflow task BioModelAgent maboss_run_simulation --bundle <bundle>
```

## Task reference

Full documentation for every task is in its **docstring** — it is the task's
`desc` and is shown by `scout workflow task BioModelAgent <task> --help`.
This page intentionally does not repeat it. To discover tasks:

```bash
scout workflow task BioModelAgent --list   # all 32
scout workflow task BioModelAgent neko_find_paths --help
```

The families and their flows:

### NeKo — network construction and curation

```
seeds ─► neko_create_sif ─┬─► neko_add_nodes ────────────┐
                          │                              │
                          ▼                              ▼
                     [SIF network] ◄── neko_complete_connection
                          │         ◄── neko_connect_targeted_nodes
                          │         ◄── neko_bridge_components
                          │
        curation (SIF → new SIF):
        neko_remove_bimodal_interactions ──► neko_remove_undefined_interactions
        neko_remove_genes / neko_remove_interaction
                          │
                          ├─► neko_export_bnet ──► .bnet ──► MaBoSS (see below)
                          │
        reports (read-only): neko_network_report (md), neko_list_interactions (tsv),
        neko_find_paths (tsv), neko_filter_interactions (tsv), neko_get_references (tsv),
        neko_analyze_connectivity (tsv), neko_analyze_gene_set (md),
        neko_preview_connection_impact (md)
```

Build with `neko_create_sif` (or `neko_add_nodes`), curate until the SIF is
bimodal-free, then inspect with the report tasks or hand it to
`neko_export_bnet`.

### MaBoSS — model inspection, configuration, simulation

```
.bnet ─► maboss_bnet_to_bnd_cfg ─► [bundle] ─► [configure] ─► [simulate / plot]
                                       │            │               │
                                       │            │               ├─ maboss_run_simulation (tsv)
                                       │            │               ├─ maboss_simulate_mutation (tsv)
                                       │            │               └─ maboss_plot_trajectories (png)
                                       │            │
                                       │            └─ configure (bundle → new bundle):
                                       │                 maboss_set_output_nodes (first!)
                                       │                 maboss_set_initial_state
                                       │                 maboss_update_parameters
                                       │                 maboss_change_rule
                                       │
                                       ├─ inspect (tsv): maboss_list_nodes,
                                       │    maboss_get_initial_state, maboss_get_logical_rules,
                                       │    maboss_get_mutations, maboss_get_parameters
                                       └─ maboss_check (md)
```

**Workflow recipes** (details in the docstrings):

- **Inspect a model**: `maboss_list_nodes` → `maboss_get_logical_rules` /
  `maboss_get_initial_state` / `maboss_get_parameters`.
- **Configure**: outputs (`maboss_set_output_nodes` — do this first, the
  state space is 2^N), initial state (`maboss_set_initial_state`), rules
  (`maboss_change_rule`), parameters (`maboss_update_parameters`, empty
  string returns the current parameters as TSV).
- **Simulate**: `maboss_run_simulation` (state probabilities over time as
  TSV), `maboss_simulate_mutation` (WT vs mutant), `maboss_plot_trajectories`
  (PNG).
- **Sanity check**: `maboss_check` (Markdown report).

## Formats

- **SIF** — `# Reference PMID: …` lines interleaved with
    `source<TAB>effect<TAB>target` rows (effects: `stimulation`,
    `inhibition`, `form_complex`, `bimodal`, `undefined`).
- **TSV** — scout-convention tables: `#`-prefixed header line, tabs, no
  `#:` directives. Readable by Workspace `tsv_*` tasks.
- **Bundle** — directory `model.bnd` + `model.cfg`; see above.
- **Markdown / PNG** — reports and plots.

## Practical notes

- **OmniPath downloads on first use.** Network-building `neko_*` tasks query
  OmniPath (or SIGNOR via `database="signor"`) through pypath; a cold cache
  downloads tens of MB and takes 10 s+. Subsequent calls hit a local cache.
- **Curate before the bridge.** `neko_export_bnet` raises on bimodal
  networks; run `neko_remove_bimodal_interactions` first. Undefined effects
  do not block it (`neko_remove_undefined_interactions` for a clean Boolean
  reading).
- **Set outputs and time horizon before simulating.** The MaBoSS state space
  is 2^N; always `maboss_set_output_nodes` and a modest `max_time` (a
  converted model defaults to `max_time=1000`).
- **Initial states.** A converted model starts with an **empty** initial
  state; set it with `maboss_set_initial_state` (accepts `[P(OFF), P(ON)]`,
  a state→probability mapping, or `[{"state": …, "probability": …}]`
  records).
- **Isolated genes never appear in a SIF** — SIF carries only edges. If a
  seed has no interaction, it will not be in the output.
- **Bundles are immutable inputs.** Configuration tasks return a new bundle;
  the input bytes are never modified.
- **Job artifacts live under `~/.scout/var/jobs/`.** A sandboxed shell
  cannot read them; inspect through the job record, not plain `cat`.

## Where to look next

- Per-task documentation: task docstrings (`python/tasks/<task>.py`) — the
  `desc` shown by `--help`.
- Developer docs: `doc/developer/README.md` (authoring, inventory,
  provenance of the port).
- The upstream MCP servers (specification of the ported behaviour):
  the `mcp-biomodelling-servers/` submodule.
