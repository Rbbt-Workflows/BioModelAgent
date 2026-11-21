"""List the reference evidence of one node or a node pair in a SIF network.
"""
import sys
import os
import pathlib

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from scout import task


@task
def neko_get_references(sif_path: pathlib.Path, node1: str,
                        node2: str | None = None) -> str:
    """Collect references for edges involving a node (or a node pair).

    Extension: tsv

    Parses the SIF file directly. With only ``node1`` every edge where the
    node appears on either side is kept. With ``node2`` as well, only edges
    directly between the two nodes are kept (either direction).

    Args:
        sif_path: Path to a previously written SIF artifact.
        node1: Gene symbol of the node whose edges are inspected.
        node2: Optional second gene symbol; restricts the result to edges
            between the two nodes.

    Returns:
        Absolute path of the written TSV file (``neko_references.tsv``)
        with the scout ``#``-header convention and columns source, effect,
        target, references.
    """
    from neko_common import read_sif_rows, artifact_path, write_tsv

    rows = read_sif_rows(sif_path)
    kept = []
    for source_node, eff, target_node, refs in rows:
        if node2 is None:
            if node1 in (source_node, target_node):
                kept.append([source_node, eff, target_node, refs])
        else:
            if {source_node, target_node} == {node1, node2}:
                kept.append([source_node, eff, target_node, refs])
    sys.stderr.write(f"[neko_get_references] {len(kept)} edge(s) matched\n")
    return write_tsv(artifact_path("neko_references.tsv"),
                     ["source", "effect", "target", "references"], kept)
