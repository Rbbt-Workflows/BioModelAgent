"""Connect a set of targeted nodes inside a SIF network.
"""
import sys
import os
import pathlib

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from scout import task


@task
def neko_connect_targeted_nodes(sif_path: pathlib.Path, nodes: list[str],
                                strategy: str = "connect_subgroup",
                                max_len: int = 1, database: str = "omnipath",
                                only_signed: bool = True,
                                consensus: bool = True) -> str:
    """Connect the given nodes to each other within the network.

    Extension: sif

    Two strategies are supported, both taken from the neko API:

    - ``connect_subgroup``: ``network.connect_subgroup(group=nodes,
      maxlen=max_len, only_signed=..., consensus=...)`` — interconnects the
      listed genes among themselves.
    - ``connect_to_upstream_nodes``:
      ``network.connect_to_upstream_nodes(nodes_to_connect=nodes,
      only_signed=..., consensus=...)`` — pulls each listed gene's upstream
      regulators into the network. (The neko signature exposes ``depth`` and
      ``rank`` knobs too; they are not exposed here to keep the input
      surface small.)

    Args:
        sif_path: Path to a previously written SIF artifact.
        nodes: Gene symbols to connect.
        strategy: 'connect_subgroup' or 'connect_to_upstream_nodes'.
        max_len: Maximum path length for the connect_subgroup strategy.
        database: Resource universe used to rebuild the network object;
            'omnipath' or 'signor'.
        only_signed: When True, keep only signed interactions.
        consensus: When True, require consensus across sources.

    Returns:
        Absolute path of the written SIF file (``neko_network.sif``).
    """
    from neko_common import load_network, write_sif, capture_stdout

    if strategy not in ("connect_subgroup", "connect_to_upstream_nodes"):
        raise ValueError(f"unknown strategy '{strategy}'; expected "
                         "'connect_subgroup' or 'connect_to_upstream_nodes'")
    if not nodes:
        raise ValueError("nodes must not be empty")

    network = load_network(sif_path, database)
    if strategy == "connect_subgroup":
        captured = capture_stdout(network.connect_subgroup, group=nodes,
                                  maxlen=max_len, only_signed=only_signed,
                                  consensus=consensus)
    else:
        captured = capture_stdout(network.connect_to_upstream_nodes,
                                  nodes_to_connect=nodes,
                                  only_signed=only_signed,
                                  consensus=consensus)
    sys.stderr.write(f"[neko_connect_targeted_nodes] {strategy} captured output:\n{captured}")
    return write_sif(network)
