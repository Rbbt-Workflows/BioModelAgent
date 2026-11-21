# BioModelAgent developer documentation

Docs for people changing this workflow: how the tasks are structured and
registered, the inventory and provenance of the port, and the environment
notes that are not obvious from the code.

- [Task authoring](TaskAuthoring.md) — the PythonWorkflow task pattern used
  here (registration, docstring contract, artifact writing, error handling),
  and how to add a task.
- [Task inventory](TaskInventory.md) — all 32 tasks with their files,
  extensions and one-line purposes, plus the disposition of every upstream
  MCP tool (ported / split / collapsed / folded / dropped / deferred).
- [Environment notes](EnvironmentNotes.md) — interpreter, versions, the
  scout-rig 0.2.6 gotchas (explicit `file:` registration; module-level
  `import maboss`), OmniPath caching, plotting headless.

Port investigation and per-task design records live one level up in
`doc/neko_investigation.md`, `doc/neko_python_tasks.md`,
`doc/maboss_investigation.md`, `doc/maboss_python_tasks.md` — they document
how the port was decided and probed; nothing there is needed to use the
workflow.
