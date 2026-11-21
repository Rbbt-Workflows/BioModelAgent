"""Bridge two components of a SIF network with connecting paths.
"""
import sys
import os
import pathlib

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from scout import task


@task
def neko_bridge_components(sif_path: pathlib.Path, comp_a: list[str],
                           comp_b: list[str], max_len: int = 2,
                           mode: str = "OUT", database: str = "omnipath",
                           only_signed: bool = True,
                           consensus: bool = True) -> str:
    """Connect two node sets of a network to each other (component bridging).

    Extension: sif

    Wraps ``network.connect_component(comp_A, comp_B, maxlen, mode,
    only_signed, consensus)``. The neko semantics are: paths are searched
    from ``comp_A`` to ``comp_B`` for mode 'OUT', the reverse for 'IN' and
    both directions for 'ALL'; afterwards every remaining node (in neither
    component) is interconnected through the ``connect_subgroup`` strategy.

    Args:
        sif_path: Path to a previously written SIF artifact.
        comp_a: Gene symbols of the first component.
        comp_b: Gene symbols of the second component.
        max_len: Maximum path length allowed while bridging.
        mode: Path direction between the components: 'OUT', 'IN' or 'ALL'.
        database: Resource universe used to rebuild the network object;
            'omnipath' or 'signor'.
        only_signed: When True, keep only signed interactions.
        consensus: When True, require consensus across sources.

    Returns:
        Absolute path of the written SIF file (``neko_network.sif``).
    """
    from neko_common import load_network, write_sif, capture_stdout

    if mode not in ("OUT", "IN", "ALL"):
        raise ValueError(f"unknown mode '{mode}'; expected 'OUT', 'IN' or 'ALL'")
    if not comp_a or not comp_b:
        raise ValueError("comp_a and comp_b must both be non-empty")

    network = load_network(sif_path, database)
    captured = capture_stdout(network.connect_component, comp_a, comp_b,
                              maxlen=max_len, mode=mode,
                              only_signed=only_signed, consensus=consensus)
    sys.stderr.write(f"[neko_bridge_components] captured output:\n{captured}")
    return write_sif(network)
