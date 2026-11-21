"""Remove a single interaction from an existing SIF network with neko.

Tier 1 task. Loads a network from a SIF artifact, removes every edge between
two nodes regardless of direction or effect, and exports the result.
"""

import os
import pathlib
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from scout import task


@task
def neko_remove_interaction(
    sif_path: pathlib.Path, node_a: str, node_b: str, database: str = "omnipath"
) -> str:
    """Remove the interaction between two nodes from a SIF network.

    Extension: sif

    Loads the network from ``sif_path`` and calls ``remove_edge(node_a,
    node_b)``, which drops the edges between the two nodes in either
    direction, then writes the updated network to ``neko_network.sif``.

    Args:
        sif_path: Path of the SIF network to modify, as produced by a previous
            network-returning NeKo task.
        node_a: First endpoint of the interaction to remove.
        node_b: Second endpoint of the interaction to remove.
        database: Resource universe consulted to resolve nodes while loading
            the SIF; ``"omnipath"`` or ``"signor"``.

    Returns:
        Absolute path of the written ``neko_network.sif`` file (in
        ``$SCOUT_JOB_FILES_DIR`` when set, otherwise a temporary directory).
    """
    from neko_common import capture_stdout, load_network, log, write_sif

    node_a = str(node_a).strip()
    node_b = str(node_b).strip()
    if not node_a or not node_b:
        raise ValueError("node_a and node_b must be non-empty node names")

    network = load_network(sif_path, database=database)
    edges_before = len(network.edges)
    # remove_edge prints a warning to stdout when the edge is absent; capture
    # it so stdout stays reserved for the task result.
    notes = capture_stdout(network.remove_edge, node_a, node_b)
    if notes.strip():
        log(f"[neko_remove_interaction] {notes.strip()}")
    edges_after = len(network.edges)
    log(
        f"[neko_remove_interaction] {node_a}-{node_b}: "
        f"{edges_before - edges_after} edge(s) removed"
    )
    return write_sif(network)
