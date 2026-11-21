"""Set the output nodes of a MaBoSS model bundle."""
import os
import pathlib
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import maboss  # noqa: F401  module load: scout-rig runs task bodies in atexit

from scout import task


@task
def maboss_set_output_nodes(bundle: pathlib.Path, nodes) -> str:
    """Set the network's output nodes and return a NEW bundle.

    Extension: bnd

    Ports the MCP ``set_maboss_output_nodes`` tool session-free. In MaBoSS
    output nodes define which state combinations are tracked: an N-output
    model can enumerate up to ``2^N`` states, so keep N small. The MCP
    server used this setting to guide the demo workflow; here it is the
    prerequisite for ``maboss_run_simulation``/``maboss_plot_trajectories``.

    Args:
        bundle: Bundle directory (``model.bnd``/``model.cfg``).
        nodes: A single node name (``str``) or a list of node names. Pass an
            empty list to clear the outputs.

    Returns:
        Absolute path of the new bundle directory (``model.bnd``/``model.cfg``).

    Raises:
        FileNotFoundError: If the bundle is missing.
        ValueError: If any node name is unknown or empty.
    """
    from maboss_common import load_bundle, parse_node_spec, require_nodes, save_bundle

    simulation = load_bundle(bundle)
    node_list = parse_node_spec(nodes) if nodes else []
    if node_list:
        require_nodes(simulation, node_list)
    simulation.network.set_output(node_list)
    return save_bundle(simulation)
