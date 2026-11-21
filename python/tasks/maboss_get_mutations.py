"""Report the node mutations carried by a model bundle."""
import os
import pathlib
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import maboss  # noqa: F401  module load: scout-rig runs task bodies in atexit

from scout import task


@task
def maboss_get_mutations(bundle: pathlib.Path) -> str:
    """List the bundle's node mutations (ON/OFF) as TSV.

    Extension: tsv

    Ports the MCP ``get_maboss_mutations`` tool session-free. pyMaBoSS
    represents mutations as ``{node: 'ON'|'OFF'}`` in
    ``simulation.get_mutations()``; nodes absent from the dict are
    wild-type. The MCP tool answered empty when nothing was mutated — here
    the artifact still has the header plus a zero-count marker so a chained
    task never has to special-case an empty file.

    Args:
        bundle: Bundle directory (``model.bnd``/``model.cfg``).

    Returns:
        Absolute path of the TSV artifact (``maboss_mutations.tsv``) with
        columns: node, state. Wild-type bundles produce a single row
        ``(node='- none -', state='')``.

    Raises:
        FileNotFoundError: If the bundle is missing.
        ValueError: If the bundle fails to load.
    """
    from maboss_common import artifact_path, load_bundle, write_tsv

    simulation = load_bundle(bundle)
    mutations = simulation.get_mutations()
    rows = [[str(node), str(state)] for node, state in sorted(mutations.items())]
    if not rows:
        rows = [["- none -", ""]]
    sys.stderr.write(f"[maboss_get_mutations] {len(mutations)} mutation(s)\n")
    return write_tsv(
        artifact_path("maboss_mutations.tsv"),
        ["node", "state"],
        rows,
    )
