"""Inspect the simulation parameters of a MaBoSS model bundle."""
import os
import pathlib
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import maboss  # noqa: F401  module load: scout-rig runs task bodies in atexit

from scout import task


@task
def maboss_get_parameters(bundle: pathlib.Path) -> str:
    """Report the bundle's simulation parameters as TSV.

    Extension: tsv

    Extracts the inspect-only half of the MCP ``update_maboss_parameters``
    tool so parameter review never needs a write. The companion write task
    (:mod:`~BioModelAgent.maboss_update_parameters`) writes a new bundle;
    with its ``parameters`` argument empty it degrades to this same report.

    Args:
        bundle: Bundle directory (``model.bnd``/``model.cfg``).

    Returns:
        Absolute path of the TSV artifact (``maboss_parameters.tsv``) with
        columns: parameter, value.

    Raises:
        FileNotFoundError: If the bundle is missing.
        ValueError: If the bundle fails to load.
    """
    from maboss_common import artifact_path, load_bundle, write_tsv

    simulation = load_bundle(bundle)
    rows = [[str(name), str(value)] for name, value in sorted(simulation.param.items())]
    sys.stderr.write(f"[maboss_get_parameters] {len(rows)} parameter(s)\n")
    return write_tsv(
        artifact_path("maboss_parameters.tsv"),
        ["parameter", "value"],
        rows,
    )
