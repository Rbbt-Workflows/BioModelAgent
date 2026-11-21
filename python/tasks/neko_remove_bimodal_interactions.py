"""Remove bimodal interactions from an existing SIF network with neko.

Tier 1 task. Loads a network from a SIF artifact, drops every interaction whose
neighbours report contradictory effects, and exports the cleaned network.
"""

import os
import pathlib
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from scout import task


@task
def neko_remove_bimodal_interactions(
    sif_path: pathlib.Path, database: str = "omnipath"
) -> str:
    """Remove bimodal (contradictory-effect) interactions from a SIF network.

    Extension: sif

    Loads the network from ``sif_path`` and calls
    ``remove_bimodal_interactions``, which removes interactions whose partners
    show both activating and inhibiting effects, then writes the cleaned
    network to ``neko_network.sif``. The number of removed edges is logged to
    stderr.

    Args:
        sif_path: Path of the SIF network to clean, as produced by a previous
            network-returning NeKo task.
        database: Resource universe consulted to resolve nodes while loading
            the SIF; ``"omnipath"`` or ``"signor"``.

    Returns:
        Absolute path of the written ``neko_network.sif`` file (in
        ``$SCOUT_JOB_FILES_DIR`` when set, otherwise a temporary directory).
    """
    from neko_common import load_network, log, write_sif

    network = load_network(sif_path, database=database)
    edges_before = len(network.edges)
    network.remove_bimodal_interactions()
    edges_after = len(network.edges)
    log(
        "[neko_remove_bimodal_interactions] "
        f"{edges_before - edges_after} bimodal edge(s) removed"
    )
    return write_sif(network)
