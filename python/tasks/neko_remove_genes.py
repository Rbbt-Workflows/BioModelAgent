"""Remove genes from an existing SIF network with neko.

Tier 1 task. Loads a network from a SIF artifact, drops the requested genes and
their edges, and exports the reduced network.
"""

import os
import pathlib
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from scout import task


@task
def neko_remove_genes(
    sif_path: pathlib.Path, genes: list[str], database: str = "omnipath"
) -> str:
    """Remove genes from a SIF network and export the reduced SIF.

    Extension: sif

    Loads the network from ``sif_path``, removes each gene present in the
    network with ``remove_node`` (genes already absent are ignored and
    reported on stderr), then writes the reduced network to
    ``neko_network.sif``.

    Args:
        sif_path: Path of the SIF network to modify, as produced by a previous
            network-returning NeKo task.
        genes: Gene symbols to remove, e.g. ``["TP53"]``. Must be non-empty.
        database: Resource universe consulted to resolve nodes while loading
            the SIF; ``"omnipath"`` or ``"signor"``.

    Returns:
        Absolute path of the written ``neko_network.sif`` file (in
        ``$SCOUT_JOB_FILES_DIR`` when set, otherwise a temporary directory).
    """
    from neko_common import load_network, log, write_sif

    genes = [str(gene).strip() for gene in genes]
    if not genes or any(not gene for gene in genes):
        raise ValueError("genes must be a non-empty list of gene symbols")

    network = load_network(sif_path, database=database)
    present = set(network.nodes["Genesymbol"].tolist())
    to_remove = [gene for gene in genes if gene in present]
    missing = [gene for gene in genes if gene not in present]
    for gene in to_remove:
        network.remove_node(gene)
    log(f"[neko_remove_genes] removed {len(to_remove)} genes: {to_remove}")
    log(f"[neko_remove_genes] missing (not removed): {missing}")
    return write_sif(network)
