"""Preview, without mutating it, what a connection change would do.
"""
import sys
import os
import pathlib

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from scout import task


@task
def neko_preview_connection_impact(sif_path: pathlib.Path,
                                   method: str = "hubs",
                                   top_k: int = 10) -> str:
    """Preview the impact of a connection change without altering the network.

    Extension: md

    Non-mutating: this task never writes a SIF. The three methods are:

    - ``hubs``: rank nodes by degree (in+out) from the SIF edge list and
      report the top ``top_k``.
    - ``relax_max_len``: load a *fresh* Network built from the SIF file
      (that in-memory copy is the only thing mutated) and run
      ``complete_connection`` with a relaxed maxlen, reporting the edge
      count before and after.
    - ``unsigned``: same, but with ``only_signed=False`` / ``consensus=False``
      to show the effect of dropping sign and consensus filters.

    Args:
        sif_path: Path to a previously written SIF artifact. Never modified.
        method: 'hubs', 'relax_max_len' or 'unsigned'.
        top_k: Number of hub nodes to list (hubs method) or relaxed path
            length context (relax/unsigned methods use min(maxlen+1, 3)).

    Returns:
        Absolute path of the written Markdown report
        (``neko_impact_preview.md``). The input network is never modified
        and no SIF is written.
    """
    from neko_common import read_sif_rows, artifact_path, write_md, load_network

    if method not in ("hubs", "relax_max_len", "unsigned"):
        raise ValueError(f"unknown method '{method}'; expected 'hubs', "
                         "'relax_max_len' or 'unsigned'")

    title = "NeKo connection impact preview"
    if method == "hubs":
        degree = {}
        for s, _e, t, _r in read_sif_rows(sif_path):
            degree[s] = degree.get(s, 0) + 1
            degree[t] = degree.get(t, 0) + 1
        ranked = sorted(degree.items(), key=lambda kv: (-kv[1], kv[0]))[:top_k]
        lines = ["",
                 "Method: hubs — degree ranking of the current edge list "
                 "(no network object is loaded; nothing can change).",
                 "",
                 "| rank | node | degree |",
                 "| --- | --- | --- |"]
        lines += [f"| {i} | {n} | {d} |" for i, (n, d) in enumerate(ranked, 1)]
    else:
        network = load_network(sif_path)
        before = len(network.edges)
        max_len = min(top_k + 1, 3)
        if method == "relax_max_len":
            network.complete_connection(maxlen=max_len)
            note = (f"Method: relax_max_len — complete_connection re-run on a "
                    f"fresh in-memory copy with maxlen={max_len} "
                    f"(default policies: only_signed=True, consensus=True).")
        else:
            network.complete_connection(maxlen=2, only_signed=False, consensus=False)
            note = ("Method: unsigned — complete_connection re-run on a fresh "
                    "in-memory copy with only_signed=False, consensus=False "
                    "(maxlen=2).")
        after = len(network.edges)
        lines = ["", note,
                 f"- Edges in the source network: {before}",
                 f"- Edges after the simulated change: {after}",
                 f"- Edge-count delta: {after - before:+d}",
                 "",
                 "The input SIF was never modified and no SIF was written; "
                 "only this report is produced."]

    sys.stderr.write(f"[neko_preview_connection_impact] method={method}\n")
    return write_md(artifact_path("neko_impact_preview.md"), title, lines)
