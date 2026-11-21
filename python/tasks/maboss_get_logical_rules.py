"""Report the Boolean logical rules of a model bundle."""
import os
import pathlib
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import maboss  # noqa: F401  module load: scout-rig runs task bodies in atexit

from scout import task


@task
def maboss_get_logical_rules(bundle: pathlib.Path) -> str:
    """List the bundle's Boolean logical rules as TSV.

    Extension: tsv

    Ports the MCP ``get_maboss_logical_rules`` tool session-free. The rule
    strings come straight from ``simulation.get_logical_rules()``; this task
    adds the ``is_output`` flag so the report doubles as the reference for
    ``maboss_change_rule`` and output-node selection.

    Args:
        bundle: Bundle directory (``model.bnd``/``model.cfg``).

    Returns:
        Absolute path of the TSV artifact (``maboss_rules.tsv``) with
        columns: node, rule, is_output.

    Raises:
        FileNotFoundError: If the bundle is missing.
        ValueError: If the bundle fails to load.
    """
    from maboss_common import artifact_path, load_bundle, write_tsv

    simulation = load_bundle(bundle)
    rules = simulation.get_logical_rules()
    outputs = {str(node) for node in simulation.network.get_output()}
    rows = [
        [
            str(node),
            str(rule),
            "true" if str(node) in outputs else "false",
        ]
        for node, rule in rules.items()
    ]
    sys.stderr.write(f"[maboss_get_logical_rules] {len(rows)} rule(s)\n")
    return write_tsv(
        artifact_path("maboss_rules.tsv"),
        ["node", "rule", "is_output"],
        rows,
    )
