"""Compare a wild-type MaBoSS run against mutated node runs."""
import os
import pathlib
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import maboss  # noqa: F401  module load: scout-rig runs task bodies in atexit

from scout import task


@task
def maboss_simulate_mutation(
    bundle: pathlib.Path,
    nodes,
    state: str = "ON",
) -> str:
    """Compare the wild-type run against runs with given nodes mutated.

    Extension: tsv

    Ports the MCP ``simulate_mutation`` tool session-free. The MCP call ran
    WT and mutated simulations against one session model and reported both;
    here the comparison is materialized as one TSV artifact. P2 verified the
    pyMaBoSS mutation path: ``sim.copy()`` returns a new simulation and
    ``mutate(node, state)`` mutates it in place and returns ``None``
    (calling ``.run()`` on its result silently runs the WT model — the
    trap the MCP server's own code avoided).

    Args:
        bundle: Bundle directory (``model.bnd``/``model.cfg``).
        nodes: A single node name or a list of node names to mutate.
        state: Mutation state applied to every listed node: ``"ON"``,
            ``"OFF"`` or ``"WT"`` (the wild-type control).

    Returns:
        Absolute path of the TSV artifact (``maboss_mutation_comparison.tsv``)
        with columns: variant ('wild-type' or 'mutant'), node, state, and one
        column per tracked state at the final time point.

    Raises:
        FileNotFoundError: If the bundle is missing.
        ValueError: If a node is unknown or ``state`` is not ON/OFF/WT.
        RuntimeError: If either simulation run fails.
    """
    from maboss_common import (
        dataframe_to_tsv,
        load_bundle,
        log,
        parse_node_spec,
        require_nodes,
    )
    import pandas

    if str(state).upper() not in ("ON", "OFF", "WT"):
        raise ValueError("state must be 'ON', 'OFF' or 'WT'.")

    simulation = load_bundle(bundle)
    node_list = parse_node_spec(nodes)
    require_nodes(simulation, node_list)

    wild_type = simulation.run()
    wild_last = wild_type.get_last_states_probtraj()
    wild_last.index = ["wild-type"]
    log(f"[maboss_simulate_mutation] WT last-state shape={wild_last.shape}")

    mutant = simulation.copy()
    for node in node_list:
        mutated = mutant.mutate(node, str(state).upper())
        log(f"[maboss_simulate_mutation] mutate({node!r}, {state!r}) -> {mutated!r}")
    mutant_last = mutant.run().get_last_states_probtraj()
    mutant_last.index = ["mutant"]
    log(f"[maboss_simulate_mutation] mutant last-state shape={mutant_last.shape}")

    combined = pandas.concat([wild_last, mutant_last])
    combined.insert(0, "variant", combined.index)
    combined.insert(
        1, "nodes", "|".join(node_list)
    )
    combined.insert(2, "state", str(state).upper())
    return dataframe_to_tsv(combined, "maboss_mutation_comparison.tsv")
