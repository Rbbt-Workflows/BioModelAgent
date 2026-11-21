"""Run a stochastic MaBoSS simulation over a model bundle."""
import os
import pathlib
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import maboss  # noqa: F401  module load: scout-rig runs task bodies in atexit

from scout import task


@task
def maboss_run_simulation(bundle: pathlib.Path) -> str:
    """Run the bundle's simulation and return the trajectory as TSV.

    Extension: tsv

    Ports the MCP ``run_simulation`` tool session-free and collapses the
    follow-up ``get_simulation_result`` extractor into the same task: the
    MCP server kept a result-object handle in a session and required a
    second call to read it, while here the result is materialized once.
    P1/P2 confirmed ``sim.run()`` works under cmaboss 1.0.0b32 with pandas
    3.0.6 and that ``get_last_states_probtraj()`` is a DataFrame.

    Args:
        bundle: Bundle directory (``model.bnd``/``model.cfg``) whose BND/CFG
            contain the simulation parameters and output nodes.

    Returns:
        Absolute path of the TSV artifact (``maboss_probtraj.tsv``): one row
        per time point, one column per tracked state. Includes the
        ``<nil>`` state column when the engine reports it.

    Raises:
        FileNotFoundError: If the bundle is missing.
        RuntimeError: If the simulation run fails.
    """
    from maboss_common import dataframe_to_tsv, load_bundle, log

    simulation = load_bundle(bundle)
    log(
        "[maboss_run_simulation] outputs="
        f"{[str(n) for n in simulation.network.get_output()]}"
    )
    try:
        result = simulation.run()
    except Exception as exc:  # noqa: BLE001 - surfaced as a task error
        raise RuntimeError(f"MaBoSS simulation run failed: {exc}") from exc

    probtraj = result.get_states_probtraj()
    log(f"[maboss_run_simulation] probtraj shape={probtraj.shape}")
    return dataframe_to_tsv(probtraj, "maboss_probtraj.tsv")
