"""Replace one node's logical rule in a MaBoSS model bundle."""
import os
import pathlib
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import maboss  # noqa: F401  module load: scout-rig runs task bodies in atexit

from scout import task


@task
def maboss_change_rule(bundle: pathlib.Path, node: str, new_rule: str) -> str:
    """Replace a node's Boolean rule and return a NEW bundle.

    Extension: bnd

    Ports the MCP ``change_maboss_rule`` tool session-free. The MCP call
    rewrote a session's in-memory model and dumped it to files; here the
    loaded simulation is mutated in memory and immediately persisted as a
    new bundle, leaving the input bundle untouched.

    Args:
        bundle: Bundle directory (``model.bnd``/``model.cfg``).
        node: Node whose rule is replaced.
        new_rule: Boolean expression in MaBoSS syntax, e.g. ``"A & B"``,
            ``"!C | D"``. Referencing the node itself creates a self-loop
            constraint that pyMaBoSS rejects at load time.

    Returns:
        Absolute path of the new bundle directory (``model.bnd``/``model.cfg``).

    Raises:
        FileNotFoundError: If the bundle is missing.
        ValueError: If ``node`` is unknown, or ``new_rule`` is empty, or the
            mutated model fails to reload.
    """
    from maboss_common import load_bundle, require_nodes, save_bundle

    simulation = load_bundle(bundle)
    if not node or not str(node).strip():
        raise ValueError("Node name must be a non-empty string.")
    if not new_rule or not str(new_rule).strip():
        raise ValueError("New rule must be a non-empty Boolean expression.")
    require_nodes(simulation, [str(node)])

    target_node = simulation.network[str(node)]
    old_rule = getattr(target_node, "logExp", "")
    target_node.logExp = str(new_rule)
    try:
        check_result = simulation.check()
    except Exception as exc:  # noqa: BLE001 - mirrored from the MCP spec
        target_node.logExp = old_rule
        raise ValueError(
            f"Rule change aborted for '{node}': validation failed: {exc}"
        ) from exc
    if check_result:
        target_node.logExp = old_rule
        raise ValueError(
            f"Rule change rejected for '{node}'; previous rule restored. "
            f"Previous: {old_rule!r} Proposed: {new_rule!r} "
            f"Validation errors: {check_result}"
        )
    return save_bundle(simulation)
