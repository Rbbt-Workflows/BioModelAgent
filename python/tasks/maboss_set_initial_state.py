"""Set the initial-state probabilities of a MaBoSS model bundle."""
import os
import pathlib
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import maboss  # noqa: F401  module load: scout-rig runs task bodies in atexit

from scout import task


@task
def maboss_set_initial_state(
    bundle: pathlib.Path,
    nodes,
    probabilities: str,
) -> str:
    """Set initial-state probabilities and return a NEW bundle.

    Extension: bnd

    Ports the MCP ``set_maboss_initial_state`` tool session-free, including
    the normalization semantics from
    ``mcp-biomodelling-servers/MaBoSS/services/normalization.py``:

    - Single node: ``probabilities`` is ``"[P(OFF), P(ON)]"``.
    - Many nodes (joint states): ``probabilities`` is a JSON list of
      ``{"state": [0/1, ...], "probability": p}`` records or an equivalent
      ``{"[0, 1]": p}`` mapping. The tuple of nodes shares one
      distribution; per-node marginals can be set by calling the task once
      per node.
    - Values must sum to 1 (within tolerance) before they reach
      ``network.set_istate``.

    Args:
        bundle: Bundle directory (``model.bnd``/``model.cfg``).
        nodes: A single node name or a list of node names.
        probabilities: JSON string with the initial-state specification
            (see above).

    Returns:
        Absolute path of the new bundle directory (``model.bnd``/``model.cfg``).

    Raises:
        FileNotFoundError: If the bundle is missing.
        ValueError: If nodes are unknown, the JSON is malformed, state
            lengths disagree with ``nodes``, or probabilities do not sum to 1.
    """
    from maboss_common import (
        load_bundle,
        parse_initial_state,
        parse_node_spec,
        require_nodes,
        save_bundle,
    )

    simulation = load_bundle(bundle)
    node_list = parse_node_spec(nodes)
    require_nodes(simulation, node_list)
    parsed = parse_initial_state(probabilities)

    if isinstance(parsed, dict):
        for state in parsed:
            length = len(state) if isinstance(state, tuple) else 1
            if length != len(node_list):
                raise ValueError(
                    f"Initial state {state!r} has {length} value(s), but "
                    f"{len(node_list)} node(s) were specified."
                )
    simulation.network.set_istate(node_list[0] if len(node_list) == 1 else node_list, parsed)
    return save_bundle(simulation)
