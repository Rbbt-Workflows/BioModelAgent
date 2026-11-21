"""Complete the connection between all disconnected nodes of a SIF network.
"""
import sys
import os
import pathlib

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from scout import task


@task
def neko_complete_connection(sif_path: pathlib.Path, database: str = "omnipath",
                             max_len: int = 2, path_policy: str = "one_shortest",
                             reuse_policy: str = "discovered_paths",
                             only_signed: bool = True,
                             consensus: bool = True) -> str:
    """Complete the connection of an existing SIF network (session-free).

    Extension: sif

    This is the ``complete`` strategy of the former MCP
    ``apply_global_connection`` tool, expressed as an explicit chain step: it
    loads the network from the SIF file and calls
    ``complete_connection`` with the given policies.

    Args:
        sif_path: Path to a previously written SIF artifact.
        database: Resource universe used to rebuild the network object;
            'omnipath' or 'signor'.
        max_len: Maximum path length allowed while connecting.
        path_policy: Path selection policy for the connector
            ('one_shortest' or 'all_shortest').
        reuse_policy: Whether already discovered paths may be reused
            ('discovered_paths' or 'new_paths').
        only_signed: When True, keep only signed interactions.
        consensus: When True, require consensus across sources.

    Returns:
        Absolute path of the written SIF file (``neko_network.sif``).
    """
    from neko_common import load_network, write_sif

    network = load_network(sif_path, database)
    network.complete_connection(maxlen=max_len, path_policy=path_policy,
                                reuse_policy=reuse_policy,
                                only_signed=only_signed, consensus=consensus)
    return write_sif(network)
