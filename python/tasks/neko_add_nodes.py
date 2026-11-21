"""Add genes to an existing SIF network with neko.

Tier 1 task. Loads a network from a SIF artifact, adds the requested genes and
optionally connects them to the rest of the network.
"""

import os
import pathlib
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from scout import task


@task
def neko_add_nodes(
    sif_path: pathlib.Path,
    genes: list[str],
    database: str = "omnipath",
    autoconnect: bool = True,
    only_signed: bool = True,
    consensus: bool = True,
) -> str:
    """Add genes to a SIF network and optionally connect them, exporting a new SIF.

    Extension: sif

    Loads the network from ``sif_path``, calls ``add_node`` for each gene and —
    when ``autoconnect`` is True — connects the added nodes to the network with
    ``connect_nodes``, then writes the updated network to ``neko_network.sif``.

    Args:
        sif_path: Path of the SIF network to extend, as produced by a previous
            network-returning NeKo task.
        genes: Gene symbols to add, e.g. ``["PTEN"]``. Must be non-empty.
        database: Resource universe consulted to resolve nodes and connections;
            ``"omnipath"`` or ``"signor"``.
        autoconnect: If True, run ``connect_nodes`` after adding the genes so
            the new nodes are linked to the existing network.
        only_signed: If True and ``autoconnect``, only signed interactions are
            used while connecting.
        consensus: If True and ``autoconnect``, only consensus interactions are
            used while connecting.

    Returns:
        Absolute path of the written ``neko_network.sif`` file (in
        ``$SCOUT_JOB_FILES_DIR`` when set, otherwise a temporary directory).
    """
    from neko_common import capture_stdout, load_network, log, write_sif

    genes = [str(gene).strip() for gene in genes]
    if not genes or any(not gene for gene in genes):
        raise ValueError("genes must be a non-empty list of gene symbols")

    network = load_network(sif_path, database=database)

    added = []
    for gene in genes:
        # add_node prints to stdout on translation failure; stdout carries the
        # task result, so its output is captured and logged to stderr instead.
        notes = capture_stdout(network.add_node, gene)
        if notes.strip():
            log(f"[neko_add_nodes] add_node({gene}): {notes.strip()}")
        if gene in set(network.nodes["Genesymbol"].tolist()):
            added.append(gene)
    log(f"[neko_add_nodes] added nodes: {added}")

    if autoconnect:
        log("[neko_add_nodes] connecting nodes")
        network.connect_nodes(only_signed=only_signed, consensus_only=consensus)
    return write_sif(network)
