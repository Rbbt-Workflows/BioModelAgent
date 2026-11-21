"""Step 1 probe P4: NeKo bridge feasibility (Exports.export_bnet).

Builds a small curated NeKo network (3 nodes, explicit signed interactions, no
OmniPath download) by adding interactions directly, exports BNet, and checks
the resulting ``.bnet`` loads through ``maboss.bnet_to_bnd_and_cfg`` +
``maboss.load``. Also exercises the bimodal multi-file case.
"""
import contextlib
import io
import sys
import tempfile
import traceback
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))


def capture_lines(callable_, *args, **kwargs):
    buffer = io.StringIO()
    with contextlib.redirect_stdout(buffer):
        callable_(*args, **kwargs)
    return buffer.getvalue().strip().splitlines()


def write_sif(path, rows):
    """Write the plain 3-column SIF rows our tasks read/write."""
    with open(path, "w", encoding="utf-8") as handle:
        for source, effect, target in rows:
            handle.write(f"{source}\t{effect}\t{target}\n")


def curated_network(tmp_path, name="curated"):
    """A -| B -> C, all signed: export_bnet's happy path."""
    from neko.core.network import Network

    sif = tmp_path / f"{name}.sif"
    rows = [("A", "inhibition", "B"), ("B", "stimulation", "C")]
    write_sif(sif, rows)
    return Network(sif_file=str(sif), resources=_offline_resources(rows))


def bimodal_network(tmp_path, name="bimo"):
    """Same shape but A->B is bimodal: export_bnet must emit 2 files."""
    from neko.core.network import Network

    sif = tmp_path / f"{name}.sif"
    rows = [("A", "bimodal", "B"), ("B", "stimulation", "C")]
    write_sif(sif, rows)
    return Network(sif_file=str(sif), resources=_offline_resources(rows))


def _offline_resources(rows):
    """Tiny OmniPath-shaped frame so Network needs no download."""
    import pandas as pd

    return pd.DataFrame({"source": [r[0] for r in rows], "target": [r[2] for r in rows]})


def main() -> int:
    from maboss_probe_common import write_probe_log

    lines = []
    try:
        from neko._outputs.exports import Exports

        lines.append("P4 OK (imports)")
        with tempfile.TemporaryDirectory(prefix="p4_") as tmp:
            tmp_path = Path(tmp)

            # --- curated (signed-only) network ---
            network = curated_network(tmp_path)
            lines.append(
                f"  curated network: nodes={len(network.nodes)} edges={len(network.edges)}"
            )
            target = tmp_path / "curated.bnet"
            printed = capture_lines(Exports(network).export_bnet, file_name=str(target))
            lines.append(f"  export_bnet stdout ({len(printed)} lines):")
            lines.extend("    " + ln for ln in printed[:6])
            produced = sorted(tmp_path.glob("curated*.bnet"))
            lines.append(f"  produced: {[p.name for p in produced]}")
            for path in produced:
                lines.append(f"  --- {path.name}:")
                lines.extend("    " + ln for ln in path.read_text().strip().splitlines())

            # --- round-trip into MaBoSS ---
            import maboss

            bnd, cfg = tmp_path / "m.bnd", tmp_path / "m.cfg"
            maboss.bnet_to_bnd_and_cfg(str(produced[0]), str(bnd), str(cfg))
            sim = maboss.load(str(bnd), str(cfg))
            lines.append(f"  maboss.load OK; nodes={list(sim.network)}")

            # --- bimodal network -> multiple files ---
            bimo_dir = tmp_path / "bimodal"
            bimo_dir.mkdir()
            btarget = bimo_dir / "bimo.bnet"
            bprinted = capture_lines(
                Exports(bimodal_network(tmp_path)).export_bnet, file_name=str(btarget)
            )
            bproduced = sorted(bimo_dir.glob("bimo*.bnet"))
            lines.append(f"  bimodal stdout ({len(bprinted)} lines):")
            lines.extend("    " + ln for ln in bprinted[:10])
            lines.append(f"  bimodal produced {len(bproduced)} files: {[p.name for p in bproduced]}")
            for path in bproduced:
                body = [ln for ln in path.read_text().strip().splitlines() if ln.startswith(("A,", "B,", "C,"))]
                lines.append(f"    {path.name}: {body}")

            # --- n= cap on permutations ---
            cap_dir = tmp_path / "cap"
            cap_dir.mkdir()
            capture_lines(
                Exports(bimodal_network(tmp_path)).export_bnet,
                file_name=str(cap_dir / "cap.bnet"),
                n=1,
            )
            capped = sorted(cap_dir.glob("cap*.bnet"))
            lines.append(f"  n=1 cap produced {len(capped)} files: {[p.name for p in capped]}")

        write_probe_log("P4", "\n".join(lines))
        print("\n".join(lines))
        return 0
    except Exception:  # noqa: BLE001
        tb = traceback.format_exc()
        write_probe_log("P4", "P4 FAILED\n" + tb)
        print(tb, file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
