"""Analyse how a gene set sits inside a SIF network.
"""
import sys
import os
import pathlib

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from scout import task


@task
def neko_analyze_gene_set(sif_path: pathlib.Path, genes: list[str],
                          connectivity: str = "weak") -> str:
    """Report presence, induced edges and components for a gene set.

    Extension: md

    Checks which requested genes are present in the network, splits the
    edges among them into internal (both endpoints in the set) and boundary
    (exactly one endpoint in the set), lists induced isolates (present
    genes with no induced edge) and partitions the induced subgraph into
    weak or strong components with networkx. No neko logic is
    reimplemented.

    Args:
        sif_path: Path to a previously written SIF artifact.
        genes: Gene symbols to analyse.
        connectivity: 'weak' or 'strong'; selects the component partition
            of the induced subgraph.

    Returns:
        Absolute path of the written Markdown report
        (``neko_gene_set.md``).
    """
    import networkx as nx

    from neko_common import read_sif_rows, artifact_path, write_md

    if connectivity not in ("weak", "strong"):
        raise ValueError(f"connectivity must be 'weak' or 'strong', got '{connectivity}'")

    rows = read_sif_rows(sif_path)
    wanted = set(genes)
    present = {s for s, _e, t, _r in rows} | {t for s, _e, t, _r in rows}
    present_wanted = sorted(wanted & present)
    absent_wanted = sorted(wanted - present)

    internal, boundary = [], []
    for s, e, t, _r in rows:
        if s in wanted and t in wanted:
            internal.append((s, e, t))
        elif s in wanted or t in wanted:
            boundary.append((s, e, t))

    induced = nx.DiGraph()
    induced.add_nodes_from(present_wanted)
    for s, _e, t in internal:
        induced.add_edge(s, t)
    comp_fn = nx.weakly_connected_components if connectivity == "weak" \
        else nx.strongly_connected_components
    components = [sorted(c) for c in comp_fn(induced)]
    components.sort(key=lambda c: (-len(c), c[0]))
    isolates = sorted(nx.isolates(induced))

    lines = ["",
             f"- Requested genes: {len(genes)}",
             f"- Present in network: {len(present_wanted)}"
             + (f" ({', '.join(present_wanted)})" if present_wanted else ""),
             f"- Absent from network: {len(absent_wanted)}"
             + (f" ({', '.join(absent_wanted)})" if absent_wanted else ""),
             f"- Internal edges (both endpoints in the set): {len(internal)}",
             f"- Boundary edges (exactly one endpoint in the set): {len(boundary)}",
             f"- Induced isolates: {len(isolates)}"
             + (f" ({', '.join(map(str, isolates))})" if isolates else ""),
             "",
             f"## {connectivity.title()} components of the induced subgraph",
             "",
             "| # | size | genes |",
             "| --- | --- | --- |"]
    for idx, comp in enumerate(components, start=1):
        lines.append(f"| {idx} | {len(comp)} | {', '.join(comp)} |")

    if internal:
        lines += ["", "## Internal edges", "", "| source | effect | target |",
                  "| --- | --- | --- |"]
        lines += [f"| {s} | {e} | {t} |" for s, e, t in internal]

    sys.stderr.write(f"[neko_analyze_gene_set] {len(present_wanted)} present, "
                     f"{len(internal)} internal, {len(boundary)} boundary edges\n")
    return write_md(artifact_path("neko_gene_set.md"),
                    f"NeKo gene-set analysis ({connectivity} components)", lines)
