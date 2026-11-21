"""Filter interactions of a SIF network by effect, source or target.
"""
import sys
import os
import pathlib

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from scout import task


@task
def neko_filter_interactions(sif_path: pathlib.Path,
                             effect: list[str] | None = None,
                             source: str | None = None,
                             target: str | None = None) -> str:
    """Filter the interaction table of a SIF network.

    Extension: tsv

    Parses the SIF file directly (no neko network object is needed) and
    keeps the rows matching ALL supplied filters. Omitted filters are
    ignored. Filters are case-insensitive on the effect token.

    The MCP variant additionally filtered by ``nodes``/``node_scope`` (all
    edges touching a node); that variant needs the network node table and is
    intentionally not ported — use neko_get_references for edges touching a
    node instead.

    Args:
        sif_path: Path to a previously written SIF artifact.
        effect: Effect tokens to keep (e.g. ['stimulation']); None keeps all.
        source: Keep only rows whose source node equals this gene.
        target: Keep only rows whose target node equals this gene.

    Returns:
        Absolute path of the written TSV file (``neko_filtered.tsv``) with
        the scout ``#``-header convention and columns source, effect,
        target, references.
    """
    from neko_common import read_sif_rows, artifact_path, write_tsv

    rows = read_sif_rows(sif_path)
    wanted_effects = None if effect is None else {e.lower() for e in effect}
    kept = []
    for source_node, eff, target_node, refs in rows:
        if wanted_effects is not None and eff.lower() not in wanted_effects:
            continue
        if source is not None and source_node != source:
            continue
        if target is not None and target_node != target:
            continue
        kept.append([source_node, eff, target_node, refs])
    sys.stderr.write(f"[neko_filter_interactions] {len(kept)} of {len(rows)} interactions match\n")
    return write_tsv(artifact_path("neko_filtered.tsv"),
                     ["source", "effect", "target", "references"], kept)
