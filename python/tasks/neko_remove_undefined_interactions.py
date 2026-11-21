"""Remove interactions whose effect token is undefined from a SIF network.
"""
import sys
import os
import pathlib

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from scout import task


@task
def neko_remove_undefined_interactions(sif_path: pathlib.Path, database: str = "omnipath") -> str:
    """Remove all interactions whose effect is 'undefined' from a SIF network.

    Extension: sif

    Loads the network from ``sif_path`` via neko, drops every edge whose sign
    token is undefined, and writes the cleaned network back to a new SIF file.

    Args:
        sif_path: Path to a previously written SIF artifact (e.g. the output
            of neko_create_sif).
        database: Resource universe used to rebuild the network object from
            the SIF file; 'omnipath' or 'signor'.

    Returns:
        Absolute path of the written SIF file. Networks always write
        ``neko_network.sif`` into the job artifact directory.
    """
    from neko_common import load_network, write_sif, capture_stdout

    network = load_network(sif_path, database)
    before = len(network.edges)
    captured = capture_stdout(network.remove_undefined_interactions)
    after = len(network.edges)
    sys.stderr.write(f"[neko_remove_undefined_interactions] removed {before - after} "
                     f"undefined edge(s); captured output:\n{captured}")
    return write_sif(network)
