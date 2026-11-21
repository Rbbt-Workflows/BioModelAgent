"""Plot the state-probability trajectories of a MaBoSS model bundle."""
import os
import pathlib
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import maboss  # noqa: F401  module load: scout-rig runs task bodies in atexit

from scout import task


@task
def maboss_plot_trajectories(bundle: pathlib.Path, until: float = 10.0) -> str:
    """Render the bundle's state trajectory plot to a PNG artifact.

    Extension: png

    Ports the MCP ``visualize_network_trajectories`` tool session-free. The
    MCP server saved a matplotlib figure into a session artifact directory;
    here the figure lands in the Scout job ``.files`` directory and the task
    returns its path. P6 verified ``result.plot_trajectory(until=...)``
    works headless: the task forces ``MPLBACKEND=Agg`` and calls
    ``matplotlib.use("Agg")`` after import, because the env var alone may
    not survive into scout's task subprocess.

    Args:
        bundle: Bundle directory (``model.bnd``/``model.cfg``).
        until: Plot time horizon; must be positive and no larger than the
            model's ``max_time`` parameter.

    Returns:
        Absolute path of the PNG artifact (``maboss_trajectories.png``).

    Raises:
        FileNotFoundError: If the bundle is missing.
        ValueError: If ``until`` is not a positive number.
        RuntimeError: If the simulation run fails.
    """
    from maboss_common import artifact_path, import_agg_matplotlib, load_bundle, log

    try:
        horizon = float(until)
    except (TypeError, ValueError) as exc:
        raise ValueError("until must be a positive number of time units.") from exc
    if horizon <= 0:
        raise ValueError("until must be a positive number of time units.")

    simulation = load_bundle(bundle)
    max_time = float(simulation.param.get("max_time", horizon))
    if horizon > max_time:
        raise ValueError(
            f"until ({horizon}) must not exceed the model max_time "
            f"({max_time})."
        )

    result = simulation.run()
    _matplotlib, plt = import_agg_matplotlib()
    figure, axes = plt.subplots()
    result.plot_trajectory(until=horizon, axes=axes)
    figure.tight_layout()
    target = artifact_path("maboss_trajectories.png")
    pathlib.Path(str(target)).parent.mkdir(parents=True, exist_ok=True)
    figure.savefig(target, dpi=150)
    plt.close(figure)
    if not pathlib.Path(str(target)).is_file():
        raise RuntimeError(f"Plot file was not created: {target}")
    log(f"[maboss_plot_trajectories] png written: {target}")
    return str(pathlib.Path(str(target)).resolve())
