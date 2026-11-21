---
name: biomodel-maboss-simulation
description: Convert, inspect, configure and stochastically simulate Boolean biological models with BioModelAgent's MaBoSS tasks. Use when an agent has a curated SIF or a .bnet file and must produce a model bundle, inspect nodes/rules/initial state/parameters, set output nodes or initial states, run simulations or mutation analyses, or plot trajectories. Covers the bundle convention (model.bnd + model.cfg directory), the required configuration order before simulation (outputs, initial state, max_time), the NeKo-to-MaBoSS bridge, accepted initial-state forms, and reading probtraj TSVs. Triggers maboss_bnet_to_bnd_cfg, neko_export_bnet, maboss_list_nodes, maboss_get_initial_state, maboss_get_logical_rules, maboss_get_mutations, maboss_get_parameters, maboss_change_rule, maboss_update_parameters, maboss_set_output_nodes, maboss_set_initial_state, maboss_run_simulation, maboss_simulate_mutation, maboss_plot_trajectories, maboss_check, Boolean model, stochastic simulation, state probabilities, trajectory plot, mutation analysis.
---

# Simulate Boolean models with MaBoSS

## What this skill covers

Operational guidance for the 15 MaBoSS-family tasks (including the
`neko_export_bnet` bridge): the bundle convention, the configure-then-
simulate flow, and reading simulation results. Per-task signatures,
defaults and semantics are in the task docstrings
(`python/tasks/maboss_*.py`, `python/tasks/neko_export_bnet.py`) — shown by
`scout workflow task BioModelAgent <task> --help` — and are not repeated
here.

## The bundle convention

A **model bundle** is one directory with fixed members `model.bnd`
(logical rules) and `model.cfg` (parameters, initial state, output nodes).
Bundle tasks take `bundle:` (the directory path) and return the path of a
**new** bundle; inputs are never modified. A task that returns a bundle
declares extension `bnd`.

## The standard flow

1. **Get a bundle** — from a curated SIF via `neko_export_bnet`
   (bimodal-free required — run `neko_remove_bimodal_interactions` first)
   then `maboss_bnet_to_bnd_cfg`; or from any existing `.bnet` file.
2. **Inspect** — `maboss_list_nodes`, `maboss_get_logical_rules`,
   `maboss_get_initial_state`, `maboss_get_mutations`,
   `maboss_get_parameters` (all TSV).
3. **Configure before simulating** — a converted model starts with an
   **empty initial state** and `max_time=1000`:
   - `maboss_set_output_nodes` — **do this first**; the state space is
     2^N and outputs bound what the simulation tracks.
   - `maboss_set_initial_state` — accepts `[P(OFF), P(ON)]` per node, a
     state→probability mapping, or
     `[{"state": [...], "probability": p}, …]` records (normalized).
   - `maboss_update_parameters` — e.g. `max_time=10,time_tick=1,sample_count=5000`.
     An empty `parameters` string returns the current parameters as TSV.
   - `maboss_change_rule` — replace one node's logical rule.
4. **Simulate / analyse** — `maboss_run_simulation` (state probabilities
   over time, TSV), `maboss_simulate_mutation` (WT vs `ON`/`OFF`/`WT`
   mutant, TSV), `maboss_plot_trajectories` (PNG), `maboss_check`
   (Markdown sanity report).

## Reading simulation output

`maboss_run_simulation` writes a TSV: one row per time point, one column
per tracked state (including `<nil>` when the engine reports it). It is a
scout-convention table — use Workspace `tsv_*` tasks to query it. The plot
task renders the same data as a PNG.

## Gotchas

- **Empty initial state after conversion** — the initial-state check of
  `maboss_check` may report all-zero probabilities until you set one.
- **`max_time=1000` default** — a converted model simulates for a long
  time and can be slow; set a modest `max_time` first.
- **Mutations are set, not applied in place**: `maboss_simulate_mutation`
  compares WT vs mutant without touching the bundle.
- **The bridge raises on bimodal networks** — curate first
  (`neko_remove_bimodal_interactions`).
- The MaBoSS engine (cmaboss) runs out-of-process; a failing engine shows
  up as a `RuntimeError` from the task, not a scout error.
