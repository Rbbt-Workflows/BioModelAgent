# Environment notes

Facts an agent or developer needs that are not obvious from the code.

## Interpreter and versions

- Python tasks execute under the **pymaboss micromamba environment**:
  `/home/mvazque2/software/micromamba/envs/pymaboss/bin/python`
  (CPython 3.12.12).
- `neko` 1.10.1, `maboss` 0.8.16 (drives the **cmaboss** 1.0.0b32 engine
  out-of-process), `matplotlib` 3.10.8, `pandas` 3.0.6, `networkx`.
- Ruby side: scout-rig 0.2.6 + scout-gear 10.13.1 on Ruby 3.3.1.
- PYTHONPATH for standalone python-suite runs:
  `$HOME/.rvm/gems/ruby-3.3.1/gems/scout-rig-0.2.6/python`.

## scout-rig 0.2.6 gotchas (both fixed by the current pattern)

1. **Python tasks load automatically.** The latest commit ("Remove cruft.
   Python tasks should load automatically") moved registration away from
   explicit `file:` entries in `workflow.rb` to automatic loading of
   `python/tasks/*.py`. Keep new task files in that directory; no wiring
   needed. If a task does not register, confirm the file lives there and the
   module-level `scout.task` decorator is present.
2. **Task bodies run in an `atexit` handler.** CPython 3.12 has already
   torn down `sys.modules` by then, so a *first-time* `import maboss`
   inside a task body dies with `AttributeError: 'NoneType' object has no
   attribute 'thread_count'` (cmaboss registers an atexit hook importing
   `concurrent.futures.thread`). **Every MaBoSS task therefore imports
   `maboss` at module level.** `neko` imports stay lazy — only `maboss`
   needs this.

## OmniPath caching

Network-building NeKo tasks query OmniPath (default) or SIGNOR
(`database="signor"`) through pypath. First use on a cold cache downloads
tens of MB (10 s+); afterwards a local cache makes rebuilds fast (1–2 s).
The cache lives outside the repo (`pypath_log/` in the repo root is build
log output, not the cache). `neko_create_sif` and friends are therefore
network-dependent on first use only.

## Plotting

`maboss_plot_trajectories` forces the matplotlib `Agg` backend
(`matplotlib.use("Agg")` before pyplot, plus `MPLBACKEND=Agg`) — tasks run
headless; the artifact is a PNG.

## Artifact locations

- When scout runs a task, artifacts go to `$SCOUT_JOB_FILES_DIR` (a job's
  `.files` directory under `~/.scout/var/jobs/BioModelAgent/<task>/`).
- Standalone (tests, direct python) falls back to `tempfile.mkdtemp()`.
- **A sandboxed shell cannot read `~/.scout/var/jobs`** — inspect job
  artifacts through the job record or an unsandboxed probe, not plain `cat`.

## Sandboxes and the submodules

The workflow root is the sandbox root. `mcp-biomodelling-servers/` and
`agentic_system_for_modelling/` are submodules kept as the *specification*
of the ported behaviour (read-only reference); nothing imports them at
runtime. Note `mcp-biomodelling-servers` may show as deleted in `git
status` when the submodule is not initialized; initialize with
`git submodule update --init` if you need to consult it.
