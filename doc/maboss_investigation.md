# MaBoSS investigation log

Work order A (plan Steps 0–4): probes, evidence and design decisions for
porting the MaBoSS MCP server tools into session-free BioModelAgent
PythonWorkflow tasks.

- Specification source (read-only): `mcp-biomodelling-servers/MaBoSS/server.py`
  (24 `@tool` registrations) and `.../README.md`.
- Route B: tasks `import maboss` directly; the MCP package contributes no
  scientific logic and is never imported.
- All probes run under
  `/home/mvazque2/software/micromamba/envs/pymaboss/bin/python`
  (CPython 3.12.12, `maboss` 0.8.16, `cmaboss` 1.0.0b32, `matplotlib` 3.10.8,
  `pandas` 3.0.6, `networkx` 3.7) unless noted.

## P1 — engine runability ✅

`python/probes/probe_p1_engine.py` — 3-node BNET (`A, B / B, A / C, A & !B`)
→ `bnet_to_bnd_and_cfg` → `maboss.load` → `sim.run()` →
`get_last_states_probtraj()`.

Result (log `python/probes/logs/p1.log`):

```
P1 OK: maboss=maboss file=.../site-packages/maboss/__init__.py
  nodes: ['B', 'A', 'C']
  run() -> Result; _err=0
  get_last_states_probtraj type=DataFrame shape=(1, 1) columns=['<nil>']
```

The cmaboss engine runs from an ordinary shell. Simulation tasks stay in
scope.

## P2 — pandas 3.0.6 compatibility ✅

`python/probes/probe_p2_pandas_mutations.py`. `DataFrame.to_csv(sep='\t')`
works; `sim.copy().mutate(node, state)` then `.run()` works
(`mutate()` mutates in place and returns `None` — call `.run()` separately).
`get_last_states_probtraj()`/`get_last_nodes_probtraj()` return DataFrames.

Parameter key names (log `p2.log`, `p2b.log`): `time_tick` **not**
`sample_time`; the `sim.param` dict exposes

```
['time_tick', 'max_time', 'sample_count', 'use_physiological_space',
 'display_step', 'start_index', 'thread_count', 'has_noise', 'palette',
 'palettes_tarball', 'table_ouput_output', 'stat_dist_traj',
 'transition_trajectory', 'verbose', 'config_dir', 'load_default_cfg']
```

(plus `sim.param` accepts and prints `*Bool`-suffixed physical-space flags).
**`update_maboss_parameters` port must use these exact keys.**

## P3 — conversion round-trip ✅

`python/probes/probe_p3_conversion.py`. `bnet_to_bnd_and_cfg(in, bnd, cfg)`
produces a minimal BND (node + logic) and a CFG with a
`$time_tick $max_time $sample_count` block and an empty initial state; the
pair loads back through `maboss.load`. Default CFG head:

```
# MaBoSS CFG file, version 1
include = .
time_tick = 0.100000
max_time = 10.000000
sample_count = 10000
```

An empty initial state means the model runs (P1 proved it) but every node is
randomized; **tasks that run must set explicit initial states** — the same
warning the MaBoSS README gives.

## P4 — NeKo bridge feasibility ✅

`python/probes/probe_p4_bridge.py` builds curated networks offline via
`neko.core.network.Network(sif_file=..., resources=<tiny DataFrame>)` (the
`resources` frame is required or the constructor tries to download OmniPath)
and calls `Exports(network).export_bnet(file_name=...)`.

- Signed-only network (A -| B, B -> C): prints
  `Created BNet file: .../curated_1.bnet`, `Generated 1 BNet files.`, and
  writes `curated_1.bnet` in BoolNet format
  (`# model in BoolNet format / targets, factors / B, !(A) / C, (B) / A, A`).
  **The output filename is `{stem}_{n}.bnet`, not the requested name.**
- That `.bnet` loads via `bnet_to_bnd_and_cfg` + `maboss.load` (nodes
  `['A','B','C']`) → the bridge is viable end-to-end.
- Bimodal network: prints a warning block listing the bimodal interactions and
  writes **2 files** (`bimo_1.bnet`, `bimo_2.bnet`) encoding the two
  modes. Any bridge task must handle a multi-file result deterministically:
  `neko_export_bnet` will return the first (`_1`) file and log the extras, or
  fail loudly if asked for a single deterministic model.
- `n=1` cap: still one file; the `_N` suffix is unconditional.

Task `neko_export_bnet` therefore takes a SIF path, builds the curated
network, exports, and returns the **single lowest-`_N`** `.bnet`, raising when
more than one file is produced (bimodal networks) with the alternatives listed
in the error. (A `--allow-multi` switch may be added later if the demo needs
it; noted as an open question.)

## P5 — bundle representation ✅ (decisive)

`python/probes/probe_p5_bundle.py` plus two scratch tasks run through
scout-rig's own `--scout-metadata` path.

- A `pathlib.Path`-annotated parameter is reported as
  `"type": "path"` and scout-rig passes scalar values through **verbatim**
  (`lib/scout/workflow/python/inputs.rb`: "if given a file path and the file
  exists, pass the path as-is"). A directory path is not special-cased and
  not rewritten — a task received `/tmp/tmp.4GTUUKD8Xj` and resolved
  `model.bnd`/`model.cfg` by fixed name inside its body.
- Both candidates work: a directory with fixed names, and a JSON manifest.
- **Gotcha (verified): the CLI runner passes a `path`-typed param as a
  `str`, not a `Path`** (`runner.py`: `py_caster = lambda s: str(Path(s))`).
  Tasks coerce `pathlib.Path(str(x))` at the top of the body — the
  annotation drives metadata only, never the runtime type.
  The **directory** is the decision (below).

## P6 — headless plotting ✅

`python/probes/probe_p6_plot.py` — `matplotlib.use("Agg")` before
`pyplot`, `result.plot_trajectory(until=10, axes=axes)` +
`fig.savefig(...)`: PNG magic `89504e470d0a1a0a`, 22910 bytes; the
no-`axes` default path also renders headlessly (21375 bytes). Tasks force the
backend in the body (`matplotlib.use("Agg")`) **and** the helper sets
`MPLBACKEND=Agg` defensively before import, so the env-var need not survive
scout's subprocess.

## Design decision: bundle representation

**Chosen: a model directory containing fixed names `model.bnd` and
`model.cfg`; the task returns the directory path.**

Evidence: P5 (scout-rig passes `path` params verbatim; directory inputs
resolve members fine), P3/P1 (BND+CFG pair is the native round-trip currency
and `maboss.load` needs both).

Rejected:

- **JSON manifest** — works (P5 proved member resolution), but adds a parsing
  layer between the scout result path and `maboss.load` for no benefit; the
  directory is directly inspectable and the members are the real artifacts.
- **Two explicit path inputs/outputs** — violates the one-path-per-task
  contract; only ever a documented fallback.

Consequences: bundle-returning tasks use `Extension: bnd` in the docstring so
scout-rig records a non-empty extension for the result (the directory path
itself has no suffix). Consumers always accept the directory as a
`pathlib.Path` and resolve `model.bnd`/`model.cfg` via
`maboss_common.load_bundle()`.`maboss_common.load_bundle()`.

One deliberate exception to a single, stable extension:
`maboss_update_parameters` keeps the MCP's dual behavior — an empty
`parameters` argument returns the inspect-only TSV
(`maboss_parameters.tsv`) instead of a bundle — so its return type varies
with that input while its `Extension: bnd` line describes the bundle case
(the dedicated, always-TSV inspector is `maboss_get_parameters`).

## Live-chain evidence (plan Step 6, work order B)

The 11-hop cross-family demo (NeKo SIF → MaBoSS simulation; transcript in
`README.md` §"Cross-family chaining demo") produced three new findings:

1. **The bridge needs no connectivity help at `max_len=2` on these seeds.**
   The README's fidelity note warned that `export_bnet` might need
   `neko_analyze_connectivity`/`neko_bridge_components` first; in practice
   the network was already fully connected enough for a 12-node `.bnet`
   (14 lines), so the anticipated curation hops were unnecessary. No
   bimodal/undefined edges survived hops 2–3 either: both were byte-identical
   no-ops (sha `fc488dab0170…`) because `only_signed=false,
   consensus=false` with these seeds already excluded them.
2. **`probabilities` rejects bare scalars.** A first attempt passed
   `probabilities='0.5'`; `parse_initial_state` correctly rejected it
   (`probabilities must be [P(OFF), P(ON)], a state->probability mapping, or
   a list of {'state': [...], 'probability': p} records`). The accepted
   string spellings are two numbers as JSON (`'[0.5, 0.5]'`), a JSON mapping,
   or JSON records. Documented in the README details.
3. **Bundle hops cost ~2 s each** (load + print + save of a 4-node model),
   dominated by the cmaboss engine start-up inside `sim.run()`; the
   conversion hop (`maboss_bnet_to_bnd_cfg`) is the only MaBoSS hop that
   shells out at all. Nothing pathological to act on.
