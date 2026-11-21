"""Analyse the weak-component partition of a SIF network.
"""
import sys
import os
import pathlib

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from scout import task


@task
def neko_analyze_connectivity(sif_path: pathlib.Path) -> str:
    """Partition the network into weakly connected components.

    Extension: tsv

    Builds an undirected graph from the SIF edge list with networkx and
    reports every weak component with its member nodes; single-node
    components (nodes that appear in the node list but have no edge) are
    flagged as isolated. Graph work is delegated to networkx — no neko
    logic is reimplemented.

    Args:
        sif_path: Path to a previously written SIF artifact.

    Returns:
        Absolute path of the written TSV file
        (``neko_connectivity.tsv``) with the scout ``#``-header convention.
        Columns: component_id, node_count, nodes (pipe-joined), isolated
        ('true' when node_count == 1). Rows are sorted by node_count
        descending.
    """
    import networkx as nx

    from neko_common import read_sif_rows, artifact_path, write_tsv

    edges = [(s, t) for s, _e, t, _r in read_sif_rows(sif_path)]
    graph = nx.Graph()
    graph.add_edges_from(edges)

    out_rows = []
    for idx, comp in enumerate(sorted(nx.connected_components(graph),
                                      key=lambda c: (-len(c), sorted(c)[0])), start=1):
        members = sorted(comp)
        out_rows.append([str(idx), str(len(members)), "|".join(members),
                         "true" if len(members) == 1 else "false"])
    sys.stderr.write(f"[neko_analyze_connectivity] {len(out_rows)} component(s)\n")
    return write_tsv(artifact_path("neko_connectivity.tsv"),
                     ["component_id", "node_count", "nodes", "isolated"], out_rows)
