"""Report the initial-state probability configuration of a model bundle."""
import os
import pathlib
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import maboss  # noqa: F401  module load: scout-rig runs task bodies in atexit

from scout import task


@task
def maboss_get_initial_state(bundle: pathlib.Path) -> str:
    """Report the bundle's initial-state probabilities as TSV.

    Extension: tsv

    Ports the MCP ``get_maboss_initial_state`` tool session-free. pyMaBoSS
    exposes ``network.get_istate()`` as an ``OrderedDict`` binding
    (node or node tuple) → (state or state tuple) → probability; this task
    flattens it to one row per (binding, state) pair.

    Args:
        bundle: Bundle directory (``model.bnd``/``model.cfg``).

    Returns:
        Absolute path of the TSV artifact (``maboss_initial_state.tsv``)
        with columns: nodes (pipe-joined when the binding covers several
        nodes), state (dash-joined 0/1 values), probability.

    Raises:
        FileNotFoundError: If the bundle is missing.
        ValueError: If the bundle fails to load.
    """
    from maboss_common import artifact_path, load_bundle, write_tsv

    simulation = load_bundle(bundle)
    initial_state = simulation.network.get_istate()

    rows = []
    for binding, distribution in initial_state.items():
        node_names = (
            [str(node) for node in binding]
            if isinstance(binding, (list, tuple))
            else [str(binding)]
        )
        for state, probability in distribution.items():
            state_values = (
                [int(value) for value in state]
                if isinstance(state, (list, tuple))
                else [int(state)]
            )
            rows.append(
                [
                    "|".join(node_names),
                    "-".join(str(value) for value in state_values),
                    str(float(probability)),
                ]
            )
    sys.stderr.write(f"[maboss_get_initial_state] {len(rows)} state row(s)\n")
    return write_tsv(
        artifact_path("maboss_initial_state.tsv"),
        ["nodes", "state", "probability"],
        rows,
    )
