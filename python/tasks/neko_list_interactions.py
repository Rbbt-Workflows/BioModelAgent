"""List the interactions of a SIF network as a scout TSV.

Tier 1 task. Pure file-format handling of our own SIF artifact: the edge rows
and their paired reference comments are parsed directly from the file.
"""

import os
import pathlib
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from scout import task


@task
def neko_list_interactions(sif_path: pathlib.Path) -> str:
    """List all interactions of a SIF network as a TSV table.

    Extension: tsv

    Parses the SIF file directly (no neko Network is loaded) and writes one row
    per interaction to ``neko_interactions.tsv`` with columns ``source``,
    ``effect``, ``target`` and ``references``; ``references`` holds the content
    of the ``# Reference PMID:`` comment line paired with the row, or an empty
    string when there is none. The first line of the file is the
    scout-convention ``#``-prefixed tab-separated header.

    Args:
        sif_path: Path of the SIF network to inspect, as produced by a
            network-returning NeKo task.

    Returns:
        Absolute path of the written ``neko_interactions.tsv`` file (in
        ``$SCOUT_JOB_FILES_DIR`` when set, otherwise a temporary directory).
    """
    from neko_common import artifact_path, read_sif_rows, write_tsv

    rows = read_sif_rows(sif_path)
    return write_tsv(
        artifact_path("neko_interactions.tsv"),
        ("source", "effect", "target", "references"),
        rows,
    )
