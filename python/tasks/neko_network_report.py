"""Summarize a SIF network as a markdown report.

Tier 1 task. Pure file-format handling of our own SIF artifact: the edge rows
are parsed directly from the file, without loading a neko Network.
"""

import os
import pathlib
import sys
from collections import Counter

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from scout import task


@task
def neko_network_report(sif_path: pathlib.Path) -> str:
    """Summarize a SIF network as a markdown report.

    Extension: md

    Parses the SIF file directly (no neko Network is loaded) and reports the
    node count, edge count, per-effect token counts, the top-10 nodes by total
    degree and whether reference PMIDs are present. Written to
    ``neko_report.md``.

    Args:
        sif_path: Path of the SIF network to summarize, as produced by a
            network-returning NeKo task.

    Returns:
        Absolute path of the written ``neko_report.md`` file (in
        ``$SCOUT_JOB_FILES_DIR`` when set, otherwise a temporary directory).
    """
    from neko_common import artifact_path, read_sif_rows, write_md

    rows = read_sif_rows(sif_path)

    nodes = set()
    degree = Counter()
    for source, _effect, target, _references in rows:
        nodes.add(source)
        nodes.add(target)
        degree[source] += 1
        degree[target] += 1
    effect_counts = Counter(effect for _s, effect, _t, _r in rows)
    references_present = any(references for _s, _e, _t, references in rows)
    top_degree = degree.most_common(10)

    lines = [f"**Source SIF:** `{sif_path}`", ""]
    lines.append("## Summary")
    lines.append("")
    lines.append(f"- Nodes (unique endpoints): {len(nodes)}")
    lines.append(f"- Edges: {len(rows)}")
    lines.append(f"- References present: {references_present}")
    lines.append("")
    lines.append("## Effect tokens")
    lines.append("")
    if effect_counts:
        lines.append("| effect | count |")
        lines.append("| --- | --- |")
        for effect, count in sorted(effect_counts.items()):
            lines.append(f"| {effect} | {count} |")
    else:
        lines.append("(no edges)")
    lines.append("")
    lines.append("## Top-10 nodes by degree")
    lines.append("")
    if top_degree:
        lines.append("| node | degree |")
        lines.append("| --- | --- |")
        for node, node_degree in top_degree:
            lines.append(f"| {node} | {node_degree} |")
    else:
        lines.append("(no edges)")
    lines.append("")
    return write_md(artifact_path("neko_report.md"), "NeKo network report", lines)
