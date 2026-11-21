"""Shared helpers for the MaBoSS Scout python tasks.

This module is NOT a scout task file: it defines no ``@task`` functions and is
never registered in ``workflow.rb``. It holds the session-free "model bundle"
representation decided in ``doc/maboss_investigation.md`` (P5) plus thin
wrappers around the installed ``maboss`` API. All simulation logic lives in
the installed ``maboss`` package; nothing here reimplements it.

Bundle contract (plan Step 2 decision):

- A **bundle** is a directory containing exactly the two fixed member names
  ``model.bnd`` and ``model.cfg``.
- Bundle-producing tasks return the **directory** path (one path, always).
- Bundle-consuming tasks accept the directory as their ``pathlib.Path``
  input (the scout runner passes it as a ``str`` — always coerce with
  ``pathlib.Path(str(...))``) and resolve the members via :func:`load_bundle`.

Top-level imports are stdlib only plus **one deliberate heavy import**:
``maboss`` itself. scout-rig runs every ``@task`` body inside an
``atexit.register`` callback (``scout/runner.py``: ``atexit.register(
_scout_run_deferred)``), i.e. **after** ``threading._shutdown()``. CPython
3.12 then raises ``RuntimeError: can't register atexit after shutdown``
inside ``concurrent.futures``/``threading._register_atexit`` the moment any
still-unimported heavy package (pandas → concurrent.futures, sklearn →
joblib → loky) is imported. Importing ``maboss`` here at module load —
normal interpreter time — warms the whole chain (pandas, numpy, sklearn)
into ``sys.modules`` so the atexit body only takes cache hits. Verified:
with the module-level import the atexit body runs fine; without it every
task fails with the RuntimeError above. Cost: ~2 s per task subprocess
(measured), acceptable for simulation-grade tasks. This is a **deviation
from convention 2's "lazy imports inside the function body"** — recorded
in ``doc/maboss_investigation.md`` and required for the tasks to run at
all under scout-rig 0.2.6 / CPython 3.12.
"""
import json
import os
import sys
from pathlib import Path

# Reuse the NeKo shared helpers instead of duplicating them (work-order
# convention 3): files_dir/artifact_path/logging/TSV/MD writers are identical.
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import maboss  # noqa: E402,F401  heavy import AT MODULE LOAD — see module docstring

from neko_common import (  # noqa: E402  (path bootstrap above is required)
    artifact_path,
    capture_stdout,
    files_dir,
    log,
    write_md,
    write_tsv,
)

#: Fixed member names inside a model bundle directory.
BUNDLE_BND = "model.bnd"
BUNDLE_CFG = "model.cfg"

#: File name used for every new bundle directory created by :func:`save_bundle`.
BUNDLE_DIR_NAME = "maboss_bundle"


def validate_bundle_path(bundle) -> Path:
    """Return ``bundle`` as a ``Path`` after checking the fixed members exist.

    Args:
        bundle: Bundle directory (``Path`` or ``str``) previously returned by a
            bundle-producing task.

    Returns:
        The validated directory ``Path``.

    Raises:
        FileNotFoundError: If the directory or either fixed member is missing.
    """
    path = Path(str(bundle))
    if not path.is_dir():
        raise FileNotFoundError(f"Bundle directory not found: {path}")
    for member in (path / BUNDLE_BND, path / BUNDLE_CFG):
        if not member.is_file():
            raise FileNotFoundError(f"Bundle member missing: {member}")
    return path


def load_bundle(bundle):
    """Load a model bundle into a pyMaBoSS ``Simulation``.

    Args:
        bundle: Bundle directory (``Path`` or ``str``).

    Returns:
        The ``maboss`` simulation object.

    Raises:
        FileNotFoundError: If the bundle or a fixed member is missing.
        ValueError: If ``maboss.load`` fails on the BND/CFG pair.
    """
    path = validate_bundle_path(bundle)
    try:
        return maboss.load(str(path / BUNDLE_BND), str(path / BUNDLE_CFG))
    except Exception as exc:  # noqa: BLE001 - re-raised with context
        raise ValueError(f"Failed to load MaBoSS bundle {path}: {exc}") from exc


def save_bundle(simulation, bundle_name: str = BUNDLE_DIR_NAME) -> str:
    """Persist a simulation as a NEW bundle directory and return its path.

    Writes ``model.bnd``/``model.cfg`` through ``sim.print_bnd``/``print_cfg``
    into a fresh directory under the task artifact directory. Input bundles are
    never mutated: the caller's model files stay byte-identical (asserted by
    the Step 5 tests).

    Args:
        simulation: A pyMaBoSS ``Simulation``.
        bundle_name: Directory name inside the artifact directory.

    Returns:
        Absolute path (``str``) of the new bundle directory.
    """
    target = Path(artifact_path(bundle_name))
    target.mkdir(parents=True, exist_ok=True)
    bnd, cfg = target / BUNDLE_BND, target / BUNDLE_CFG
    with open(bnd, "w", encoding="utf-8") as handle:
        simulation.print_bnd(out=handle)
    with open(cfg, "w", encoding="utf-8") as handle:
        simulation.print_cfg(out=handle)
    for member in (bnd, cfg):
        if not member.is_file():
            raise FileNotFoundError(f"Bundle member not written: {member}")
    log(f"[maboss_common] bundle written: {target}")
    return str(target.resolve())


def import_agg_matplotlib():
    """Import matplotlib with the Agg backend forced and return the modules.

    Sets ``MPLBACKEND=Agg`` *before* importing (the env var may not survive
    into scout's task subprocess), then calls ``matplotlib.use("Agg")``
    defensively after import.

    Returns:
        Tuple ``(matplotlib, pyplot)`` with the backend pinned to ``Agg``.
    """
    os.environ.setdefault("MPLBACKEND", "Agg")
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    return matplotlib, plt


def dataframe_to_tsv(dataframe, filename: str) -> str:
    """Write a pandas DataFrame as a scout-convention TSV artifact.

    The DataFrame index (simulation time for MaBoSS results) is preserved as
    the first column named after ``df.index.name`` or ``time``.

    Args:
        dataframe: A pandas DataFrame.
        filename: Artifact file name.

    Returns:
        Absolute path of the written TSV file.
    """
    frame = dataframe.copy()
    index_name = frame.index.name or "time"
    frame.index = frame.index.map(str)
    frame.index.name = index_name
    return write_tsv(
        artifact_path(filename),
        [index_name] + [str(column) for column in frame.columns],
        (list(row) for row in frame.itertuples(index=True, name=None)),
    )


def parse_node_spec(nodes) -> list:
    """Normalize a node argument to a list of node name strings.

    Mirrors the MCP ``simulate_mutation``/``set_maboss_initial_state``
    schema: a single string becomes a one-element list; lists/tuples pass
    through as strings.

    Args:
        nodes: Node name (``str``) or list of node names.

    Returns:
        List of node names.

    Raises:
        ValueError: If ``nodes`` is empty.
    """
    if isinstance(nodes, str):
        node_list = [part.strip() for part in nodes.split(",")]
        node_list = [part for part in node_list if part]
        if node_list:
            return node_list
        raise ValueError("nodes must be a non-empty string or a non-empty list")
    if isinstance(nodes, (list, tuple)):
        node_list = [str(node).strip() for node in nodes]
        if node_list and all(node_list):
            return node_list
    raise ValueError(
        "nodes must be a non-empty node name or a non-empty list of node names"
    )


def parse_initial_state(probabilities):
    """Parse a JSON-string or native initial-state specification.

    Accepted forms (mirroring the MCP ``set_maboss_initial_state`` schema):

    - ``[P_OFF, P_ON]`` — two numbers, single node.
    - ``[{"state": [0, 1, ...], "probability": p}, ...]`` — JSON-native
      joint-state records for one or many nodes.
    - ``{"0": p0, "1": p1}`` / ``{"[0, 1]": p, ...}`` — a state→probability
      mapping, as JSON requires string keys.

    Args:
        probabilities: Specification (JSON text, list or dict).

    Returns:
        A ``dict[int | tuple[int, ...], float]`` or a two-element
        ``[P_OFF, P_ON]`` list ready for ``network.set_istate``.

    Raises:
        ValueError: If the specification is malformed or probabilities do not
            sum to 1.
    """
    import json as _json

    if isinstance(probabilities, str):
        text = probabilities.strip()
        if not text:
            raise ValueError("probabilities must not be empty")
        try:
            probabilities = _json.loads(text)
        except _json.JSONDecodeError as exc:
            raise ValueError(f"probabilities is not valid JSON: {exc}") from exc

    if isinstance(probabilities, (list, tuple)):
        values = list(probabilities)
        if all(
            isinstance(value, (int, float)) and not isinstance(value, bool)
            for value in values
        ):
            if len(values) != 2:
                raise ValueError(
                    "A single-node probability list must be exactly "
                    "[P(OFF), P(ON)]."
                )
            return [_initial_probability(value, state=index)
                    for index, value in enumerate(values)]
        records = []
        for entry in values:
            if not isinstance(entry, dict) or set(entry) != {
                "state",
                "probability",
            }:
                raise ValueError(
                    "Joint-state probabilities must be records with exactly "
                    "'state' and 'probability' fields."
                )
            records.append((entry["state"], entry["probability"]))
        return _joint_mapping(records)
    if isinstance(probabilities, dict):
        if not probabilities:
            raise ValueError("At least one initial-state probability is required.")
        return _joint_mapping(list(probabilities.items()))
    raise ValueError(
        "probabilities must be [P(OFF), P(ON)], a state->probability mapping, "
        "or a list of {'state': [...], 'probability': p} records."
    )


def _initial_probability(value, *, state) -> float:
    """Validate one probability value."""
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(
            f"Probability for state {state!r} must be a finite number "
            "between 0 and 1."
        )
    number = float(value)
    if not 0.0 <= number <= 1.0:
        raise ValueError(
            f"Probability for state {state!r} must be a finite number "
            "between 0 and 1."
        )
    return number


def parse_state_string(text: str):
    """Parse a JSON-ish Boolean state string like ``"[0, 1]"`` or ``"0"``.

    Returns:
        The parsed state (``int`` or ``tuple`` of ints), or ``None`` when the
        text does not encode a state.
    """
    try:
        value = json.loads(text)
    except (TypeError, ValueError):
        return None
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value
    if isinstance(value, list):
        return tuple(int(item) for item in value)
    return None


def _joint_mapping(entries) -> dict:
    """Validate state/probability entries and return the native mapping."""
    mapping = {}
    for state, probability in entries:
        if isinstance(state, str):
            state = parse_state_string(state)
        if isinstance(state, (list, tuple)):
            key = tuple(int(item) for item in state)
            if any(item not in (0, 1) for item in key):
                raise ValueError(
                    f"Initial state {state!r} must contain only 0/1 values."
                )
        elif isinstance(state, int) and not isinstance(state, bool):
            key = int(state)
        else:
            raise ValueError(
                "Each initial state must be 0/1 or a list/tuple of 0/1 values."
            )
        if key in mapping:
            raise ValueError(f"Initial state {state!r} is specified more than once.")
        mapping[key] = _initial_probability(probability, state=state)
    if abs(sum(mapping.values()) - 1.0) > 1e-9:
        raise ValueError("Initial-state probabilities must sum to 1.")
    return mapping


def require_nodes(simulation, node_names) -> None:
    """Raise ``ValueError`` naming the unknown nodes against the network.

    Mirrors the MCP node-existence error messages so failures read the same
    on both sides of the port.
    """
    try:
        available = [str(node) for node in simulation.network.keys()]
    except Exception as list_error:  # noqa: BLE001
        raise ValueError("Could not enumerate network nodes.") from list_error
    unknown = [node for node in node_names if node not in available]
    if unknown:
        raise ValueError(
            f"Unknown MaBoSS node(s): {', '.join(unknown)}. "
            f"Available nodes: {', '.join(available)}"
        )


__all__ = [
    "BUNDLE_BND",
    "BUNDLE_CFG",
    "BUNDLE_DIR_NAME",
    "artifact_path",
    "capture_stdout",
    "dataframe_to_tsv",
    "files_dir",
    "import_agg_matplotlib",
    "load_bundle",
    "log",
    "parse_initial_state",
    "parse_node_spec",
    "require_nodes",
    "save_bundle",
    "validate_bundle_path",
    "write_md",
    "write_tsv",
]
