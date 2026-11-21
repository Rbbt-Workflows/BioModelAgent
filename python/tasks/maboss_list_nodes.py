"""List the nodes of a MaBoSS model bundle with output-node flags."""
import os
import pathlib
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import maboss  # noqa: F401  module load: scout-rig runs task bodies in atexit

from scout import task


@task
def maboss_list_nodes(bundle: pathlib.Path) -> str:
    """List every node in the bundle's MaBoSS network.

    Extension: tsv

    Ports the MCP ``get_maboss_nodes`` tool session-free. The MCP call's job
    was "call this before set_maboss_output_nodes/set_maboss_initial_state to
    avoid referencing non-existent nodes"; here the node list also carries
    the current output flag so the next configuration step can be made
    without a second inspection round.

    Args:
        bundle: Bundle directory (``model.bnd``/``model.cfg``) from a
            bundle-producing task.

    Returns:
        Absolute path of the TSV artifact (``maboss_nodes.tsv``) with
        columns: node, is_output ('true'/'false'), mutation_state (empty when
        the node is wild-type).

    Raises:
        FileNotFoundError: If the bundle is missing.
        ValueError: If the bundle fails to load.
    """
    from maboss_common import artifact_path, load_bundle, write_tsv

    simulation = load_bundle(bundle)
    nodes = [str(node) for node in simulation.network.keys()]
    outputs = {str(node) for node in simulation.network.get_output()}
    mutations = {str(k): str(v) for k, v in simulation.get_mutations().items()}
    rows = [
        [
            node,
            "true" if node in outputs else "false",
            mutations.get(node, ""),
        ]
        for node in sorted(nodes)
    ]
    sys.stderr.write(f"[maboss_list_nodes] {len(rows)} node(s)\n")
    return write_tsv(
        artifact_path("maboss_nodes.tsv"),
        ["node", "is_output", "mutation_state"],
        rows,
    )
