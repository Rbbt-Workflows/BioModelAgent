"""Step 1 probe P6: headless trajectory plotting.

Confirms ``result.plot_trajectory(until=...)`` renders to a PNG with the
``Agg`` backend forced from inside the task body (both ``matplotlib.use`` and
``MPLBACKEND``), i.e. no display, no Tk, file artifact only.
"""
import os
import sys
import tempfile
import traceback
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))


def main() -> int:
    from maboss_probe_common import write_probe_log

    lines = []
    try:
        import matplotlib

        matplotlib.use("Agg")
        import maboss

        with tempfile.TemporaryDirectory(prefix="p6_") as tmp:
            tmp_path = Path(tmp)
            bnet = tmp_path / "tiny.bnet"
            bnet.write_text("targets, factors\nA, B\nB, A\nC, A & !B\n", encoding="utf-8")
            bnd, cfg = tmp_path / "m.bnd", tmp_path / "m.cfg"
            maboss.bnet_to_bnd_and_cfg(str(bnet), str(bnd), str(cfg))
            sim = maboss.load(str(bnd), str(cfg))
            sim.network.set_output(("A", "B", "C"))
            result = sim.run()
            png = tmp_path / "traj.png"
            import matplotlib.pyplot as plt

            fig, axes = plt.subplots(figsize=(6, 4))
            result.plot_trajectory(until=10, axes=axes)  # axes= per API
            fig.savefig(str(png), dpi=100, bbox_inches="tight")
            plt.close(fig)
            lines.append(f"P6 OK: backend={matplotlib.get_backend()}")
            lines.append(f"  png exists={png.is_file()} bytes={png.stat().st_size if png.is_file() else 0}")
            head = png.read_bytes()[:8]
            lines.append(f"  png magic={head.hex()!r} (89504e47... = PNG)")

            # Also verify the default (no axes) path: plot_trajectory without
            # axes must not require a display when Agg is set first.
            png2 = tmp_path / "traj2.png"
            result.plot_trajectory(until=10)
            fig2 = plt.gcf()
            fig2.savefig(str(png2), dpi=100)
            plt.close(fig2)
            lines.append(f"  default-axes png exists={png2.is_file()} bytes={png2.stat().st_size if png2.is_file() else 0}")

        write_probe_log("P6", "\n".join(lines))
        print("\n".join(lines))
        return 0
    except Exception:  # noqa: BLE001
        tb = traceback.format_exc()
        write_probe_log("P6", "P6 FAILED\n" + tb)
        print(tb, file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
