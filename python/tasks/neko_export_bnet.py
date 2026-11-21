"""Export a NeKo SIF network as a BoolNet .bnet file (MaBoSS bridge).

Ports the deferred "NeKo → MaBoSS handoff" idea from the NeKo round into a
single-path Scout task: it is the NeKo-side half of what the MCP server's
``import_neko_handoff`` did across servers, with no manifest bookkeeping —
the returned ``.bnet`` feeds straight into ``maboss_bnet_to_bnd_cfg``.
"""
import os
import pathlib
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from scout import task


@task
def neko_export_bnet(sif_path: pathlib.Path, database: str = "omnipath") -> str:
    """Export a curated SIF network to BoolNet .bnet for MaBoSS conversion.

    Extension: bnet

    Loads the SIF as a curated ``neko`` network and delegates to
    ``neko._outputs.exports.Exports.export_bnet``. ``Exports`` writes
    ``{stem}_{n}.bnet`` files; with bimodal interactions present it produces
    one file per mode, which cannot be collapsed into a single deterministic
    model — the task then fails loudly, listing the produced files, after the
    SIF has already been de-bimodaled upstream
    (``neko_remove_bimodal_interactions``).

    Args:
        sif_path: Path to a SIF artifact from a network-returning NeKo task.
        database: Resource universe used while loading the curated network;
            ``"omnipath"`` or ``"signor"``.

    Returns:
        Absolute path of the written ``.bnet`` file
        (``neko_network.bnet`` in the task artifact directory).

    Raises:
        FileNotFoundError: If ``sif_path`` does not exist.
        ValueError: If the export produces no file or more than one file
            (bimodal interactions present).
    """
    from neko_common import artifact_path, capture_stdout, load_network, log

    if not pathlib.Path(str(sif_path)).is_file():
        raise FileNotFoundError(f"SIF file not found: {sif_path}")

    network = load_network(sif_path, database)
    target = pathlib.Path(artifact_path("neko_network.bnet"))
    target.parent.mkdir(parents=True, exist_ok=True)

    from neko._outputs.exports import Exports

    printed = capture_stdout(
        Exports(network).export_bnet, file_name=str(target)
    )
    log(f"[neko_export_bnet] neko said: {printed.strip()}")

    produced = sorted(target.parent.glob(f"{target.stem}_*.bnet"))
    if not produced:
        raise ValueError(
            f"export_bnet produced no .bnet file in {target.parent} "
            f"(neko output: {printed.strip()!r}). Check that the network has "
            "nodes and interactions."
        )
    if len(produced) > 1:
        names = ", ".join(path.name for path in produced)
        for path in produced:
            path.unlink()
        raise ValueError(
            "Bimodal interactions produce multiple .bnet files "
            f"({names}); run neko_remove_bimodal_interactions on the SIF "
            "first to get one deterministic Boolean model."
        )
    produced[0].rename(target)
    log(f"[neko_export_bnet] bnet written: {target}")
    return str(target.resolve())
