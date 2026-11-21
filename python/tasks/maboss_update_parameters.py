"""Update simulation parameters of a MaBoSS model bundle."""
import os
import pathlib
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import maboss  # noqa: F401  module load: scout-rig runs task bodies in atexit

from scout import task


@task
def maboss_update_parameters(
    bundle: pathlib.Path,
    parameters: str = "",
) -> str:
    """Update simulation parameters and return a NEW bundle, or inspect.

    Extension: bnd

    Ports the MCP ``update_maboss_parameters`` tool session-free, including
    its dual behavior:

    - With a ``parameters`` JSON mapping, the task applies each parameter to
      ``simulation.param`` and returns a new bundle (inspect + update).
    - With ``parameters`` empty, no model is written; the task returns an
      inspect-only parameter report artifact (``maboss_parameters.tsv``).

    Args:
        bundle: Bundle directory (``model.bnd``/``model.cfg``).
        parameters: JSON object string ``{"param": value}`` with the known
            keys ``time_tick``, ``max_time``, ``sample_count``, ``seed``.
            Numbers for the first three; ``seed`` must be an integer. An
            empty value means inspect-only.

    Returns:
        Absolute path of the new bundle directory, or (inspect-only) the
        TSV report path.

    Raises:
        FileNotFoundError: If the bundle is missing.
        ValueError: If the JSON is malformed, a parameter name is unknown,
            or a value has the wrong type.
    """
    import json

    from maboss_common import artifact_path, load_bundle, log, save_bundle, write_tsv

    simulation = load_bundle(bundle)
    if not parameters or not str(parameters).strip():
        rows = [[str(k), str(v)] for k, v in sorted(simulation.param.items())]
        log("[maboss_update_parameters] no parameters: inspect-only report")
        return write_tsv(
            artifact_path("maboss_parameters.tsv"),
            ["parameter", "value"],
            rows,
        )

    raw = str(parameters).strip()
    if raw.startswith("{"):
        try:
            updates = json.loads(raw)
        except json.JSONDecodeError as exc:
            raise ValueError(f"Error parsing parameters JSON: {exc}") from exc
        if not isinstance(updates, dict) or not updates:
            raise ValueError("parameters must be a non-empty JSON object of name→value.")
    else:
        # scout passes string params as one shell token: "max_time=10,seed=1".
        updates = {}
        for token in [part for part in raw.replace(";", ",").split(",") if part.strip()]:
            name, sep, value = token.partition("=")
            if not sep:
                raise ValueError(
                    f"Bad parameters token {token!r}: expected key=value pairs "
                    "(e.g. max_time=20,seed=1) or a JSON object."
                )
            text = value.strip()
            try:
                updates[name.strip()] = int(text)
            except ValueError:
                try:
                    updates[name.strip()] = float(text)
                except ValueError:
                    updates[name.strip()] = text

    numeric_names = {"time_tick", "max_time", "sample_count"}
    for name, value in updates.items():
        name = str(name)
        if name not in simulation.param:
            known = ", ".join(sorted(str(k) for k in simulation.param))
            raise ValueError(
                f"Unknown parameter: {name}. Available: {known}"
            )
        if name == "seed":
            if isinstance(value, bool) or not isinstance(value, int):
                raise ValueError("Parameter 'seed' must be an integer.")
            simulation.param[name] = value
            log(f"[maboss_update_parameters] {name}={value}")
            continue
        if name in numeric_names:
            if isinstance(value, bool) or not isinstance(value, (int, float)):
                raise ValueError(f"Parameter '{name}' must be numeric.")
            simulation.param[name] = value
            log(f"[maboss_update_parameters] {name}={value}")
            continue
        raise ValueError(
            f"Parameter '{name}' cannot be updated from this task."
        )
    return save_bundle(simulation)
