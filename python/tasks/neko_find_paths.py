"""Find paths between two nodes of a SIF network with neko.

Tier 1 task. Loads a Network from the SIF artifact, captures the printed
output of ``print_my_paths`` and turns it into a scout TSV table.
"""

import ast
import os
import pathlib
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from scout import task


@task
def neko_find_paths(
    sif_path: pathlib.Path,
    source: str,
    target: str,
    maxlen: int = 3,
    database: str = "omnipath",
) -> str:
    """Find paths between two nodes of a SIF network and report them as a TSV.

    Extension: tsv

    Loads the network from ``sif_path``, validates that ``source`` and
    ``target`` are network nodes and captures the stdout of
    ``network.print_my_paths(source, target, maxlen)``.

    Each printed path line — the installed neko (1.10.1) prints every path as
    a Python list literal of gene symbols, e.g. ``['TP53', 'ESR1', 'MYC']`` —
    is parsed into one row of ``neko_paths.tsv`` with columns ``path_length``,
    ``path`` and ``nodes``: the edge count, the original line and the path
    nodes joined with ``;``. Lines that are not path lists (warnings, errors)
    are skipped; ``A -> B`` style lines are accepted as a fallback for other
    neko builds. When no path exists the table is written with its header
    only. This row-parsing (a pure file-format concern over our own artifact)
    is implemented here; the path search itself is neko's.

    Args:
        sif_path: Path of the SIF network to search, as produced by a previous
            network-returning NeKo task.
        source: Source node gene symbol, e.g. ``"TP53"``.
        target: Target node gene symbol, e.g. ``"MYC"``.
        maxlen: Maximum path length (edges) to search for.
        database: Resource universe consulted while loading the SIF;
            ``"omnipath"`` or ``"signor"``.

    Returns:
        Absolute path of the written ``neko_paths.tsv`` file (in
        ``$SCOUT_JOB_FILES_DIR`` when set, otherwise a temporary directory).

    Raises:
        ValueError: If ``source`` or ``target`` is not a node of the loaded
            network, or ``database`` is unsupported.
    """
    from neko_common import (
        artifact_path,
        capture_stdout,
        load_network,
        log,
        write_tsv,
    )

    network = load_network(sif_path, database=database)

    source = str(source).strip()
    target = str(target).strip()
    if not source or not target:
        raise ValueError("source and target must be non-empty node names")
    node_names = set(network.nodes["Genesymbol"].tolist())
    for name in (source, target):
        if name not in node_names:
            raise ValueError(
                f"Node {name!r} is not present in the network loaded from {sif_path}"
            )

    printed = capture_stdout(network.print_my_paths, source, target, maxlen)
    log(f"[neko_find_paths] captured output:\n{printed}")

    rows = []
    for line in printed.splitlines():
        line = line.strip()
        if not line:
            continue
        if line.startswith(("Warning:", "Error:")):
            log(f"[neko_find_paths] {line}")
            continue
        nodes = _parse_path_line(line)
        if len(nodes) < 2:
            continue
        rows.append((len(nodes) - 1, line, ";".join(nodes)))

    rows.sort(key=lambda row: (row[0], row[1]))
    return write_tsv(
        artifact_path("neko_paths.tsv"),
        ("path_length", "path", "nodes"),
        rows,
    )


def _parse_path_line(line: str) -> list:
    """Parse one ``print_my_paths`` line into its node symbols.

    The installed neko prints paths as Python list literals
    (``['A', 'B', 'C']``); a fallback handles ``A -> B -> C`` chains from
    other builds. Lines that parse to fewer than two nodes yield ``[]``.
    """
    if line.startswith("[") and line.endswith("]"):
        try:
            parsed = ast.literal_eval(line)
        except (ValueError, SyntaxError):
            return []
        if isinstance(parsed, (list, tuple)) and all(
            isinstance(item, str) for item in parsed
        ):
            return [item.strip() for item in parsed if item.strip()]
        return []
    return [part.strip() for part in line.split("->") if part.strip()]
