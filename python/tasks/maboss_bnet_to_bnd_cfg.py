"""Convert a BoolNet .bnet file into a MaBoSS model bundle (BND + CFG)."""
import os
import pathlib
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import maboss  # noqa: F401  module load: scout-rig runs task bodies in atexit

from scout import task


@task
def maboss_bnet_to_bnd_cfg(bnet_path: pathlib.Path) -> str:
    """Convert a .bnet file to a MaBoSS bundle directory (model.bnd/model.cfg).

    Extension: bnd

    Ports the MCP ``bnet_to_bnd_and_cfg`` tool session-free: the session's
    two output files become a single bundle directory that every other
    MaBoSS task accepts as its ``bundle`` input. The MCP server's follow-up
    ``build_simulation`` call is collapsed into the shared
    ``maboss_common.load_bundle`` helper used by all consuming tasks.

    Args:
        bnet_path: Path to a BoolNet ``.bnet`` file (e.g. the output of
            ``neko_export_bnet``).

    Returns:
        Absolute path of the bundle directory containing ``model.bnd`` and
        ``model.cfg``.

    Raises:
        FileNotFoundError: If ``bnet_path`` does not exist or conversion
            produced no BND/CFG.
        ValueError: If ``maboss.bnet_to_bnd_and_cfg`` fails.
    """
    from maboss_common import log, save_bundle  # noqa: F401  pre-imports maboss at module load

    path = pathlib.Path(str(bnet_path))
    if not path.is_file():
        raise FileNotFoundError(f"BNET file not found: {path}")

    import maboss

    import tempfile

    with tempfile.TemporaryDirectory(prefix="bnet2bnd_") as tmp:
        bnd = pathlib.Path(tmp) / "model.bnd"
        cfg = pathlib.Path(tmp) / "model.cfg"
        try:
            maboss.bnet_to_bnd_and_cfg(str(path), str(bnd), str(cfg))
        except Exception as exc:  # noqa: BLE001 - re-raised with context
            raise ValueError(f"Error converting .bnet file {path}: {exc}") from exc
        for member, label in ((bnd, "BND"), (cfg, "CFG")):
            if not member.is_file():
                raise FileNotFoundError(
                    f"Expected {label} file was not created during conversion."
                )
        # Validate the pair loads before handing the bundle downstream.
        try:
            simulation = maboss.load(str(bnd), str(cfg))
        except Exception as exc:  # noqa: BLE001
            raise ValueError(
                f"Converted BND/CFG pair does not load: {exc}"
            ) from exc
        if not simulation:
            raise ValueError("maboss.load returned no simulation for the converted pair.")
        log(f"[maboss_bnet_to_bnd_cfg] nodes={len(list(simulation.network.keys()))}")
        return save_bundle(simulation)
