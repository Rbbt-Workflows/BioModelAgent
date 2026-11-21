"""Build a signed PPI network from a gene list with neko.

Tier 1 task. Creates a neko ``Network`` from a seed gene list and completes the
connections between them, then exports the result as a SIF artifact.
"""

import os
import pathlib
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from scout import task


@task
def neko_create_sif(
    genes: list[str],
    database: str = "omnipath",
    max_len: int = 1,
    path_policy: str = "one_shortest",
    reuse_policy: str = "discovered_paths",
    only_signed: bool = True,
    consensus: bool = True,
) -> str:
    """Build a signed interaction network from a seed gene list and export it as SIF.

    Extension: sif

    Creates a neko Network over ``genes`` and calls ``complete_connection`` to
    link the seeds through the chosen resource universe, then writes the
    resulting network to ``neko_network.sif``.

    Note: unlike the earlier proof-of-concept task, this task does NOT remove
    bimodal or undefined interactions automatically. Curation is performed by
    explicit follow-up tasks (``neko_remove_bimodal_interactions`` and
    ``neko_remove_undefined_interactions``) so the raw build is inspectable.

    Args:
        genes: Seed gene symbols, e.g. ``["TP53", "MYC"]``. Must contain
            between 2 and 20 unique non-empty symbols.
        database: Resource universe consulted for interactions;
            ``"omnipath"`` or ``"signor"``.
        max_len: Maximum path length used by ``complete_connection`` when
            searching for connections between seed genes.
        path_policy: How candidate paths are selected;
            ``"one_shortest"``, ``"all_shortest"`` or ``"all_bounded"``.
        reuse_policy: Whether paths discovered for one seed pair may be reused
            for other pairs; ``"none"``, ``"discovered_paths"`` or
            ``"induced_subgraph"``.
        only_signed: If True, only signed (activate/inhibit) interactions are
            accepted while completing connections.
        consensus: If True, only interactions reported by multiple resources
            are accepted while completing connections.

    Returns:
        Absolute path of the written ``neko_network.sif`` file (in
        ``$SCOUT_JOB_FILES_DIR`` when set, otherwise a temporary directory).
    """
    from neko_common import log, validate_database, write_sif

    genes = list(genes)
    genes = [str(gene).strip() for gene in genes]
    if not genes or any(not gene for gene in genes):
        raise ValueError("genes must be a non-empty list of gene symbols")
    unique = list(dict.fromkeys(genes))
    if len(unique) != len(genes):
        raise ValueError("genes must not contain duplicate symbols")
    if not (2 <= len(unique) <= 20):
        raise ValueError(
            f"genes must contain between 2 and 20 unique symbols; got {len(unique)}"
        )
    validate_database(database)

    log(f"[neko_create_sif] building network: genes={unique} database={database}")
    from neko.core.network import Network

    network = Network(unique, resources=database)
    network.complete_connection(
        maxlen=max_len,
        path_policy=path_policy,
        reuse_policy=reuse_policy,
        only_signed=only_signed,
        consensus=consensus,
    )
    return write_sif(network)
