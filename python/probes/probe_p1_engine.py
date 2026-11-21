"""Step 1 probe P1: engine runability.

Tiny 3-node Boolean network written as a real ``.bnet`` fixture, loaded via
``maboss.load`` after ``maboss.bnet_to_bnd_and_cfg``, run with the cmaboss
engine, and read through ``get_last_states_probtraj``.

Run: pymaboss python, plain function (no scout).
"""
import sys
import tempfile
import traceback
from pathlib import Path

BNET = """targets, factors
A, B
B, A
C, A & !B
"""

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "tasks"))
sys.path.insert(0, str(Path(__file__).resolve().parent))


def main() -> int:
    from maboss_probe_common import write_probe_log

    try:
        import maboss

        with tempfile.TemporaryDirectory(prefix="p1_") as tmp:
            tmp_path = Path(tmp)
            bnet = tmp_path / "tiny.bnet"
            bnet.write_text(BNET, encoding="utf-8")
            bnd = tmp_path / "model.bnd"
            cfg = tmp_path / "model.cfg"
            maboss.bnet_to_bnd_and_cfg(str(bnet), str(bnd), str(cfg))
            sim = maboss.load(str(bnd), str(cfg))
            nodes = list(sim.network.keys())
            sim.network.set_output(["C"])
            result = sim.run()
            err = getattr(result, "_err", 0)
            df = result.get_last_states_probtraj()
            csv = df.to_csv(sep="\t")
            lines = [
                f"P1 OK: maboss={maboss.__name__} file={maboss.__file__}",
                f"  bnet fixture: {bnet}",
                f"  bnd bytes: {bnd.stat().st_size}; cfg bytes: {cfg.stat().st_size}",
                f"  nodes: {nodes}",
                f"  run() -> {type(result).__name__}; _err={err}",
                f"  get_last_states_probtraj type={type(df).__name__} shape={df.shape}",
                f"  columns={list(df.columns)}",
                f"  tab-separated CSV head:\\n" + "\\n".join("    " + ln for ln in csv.strip().splitlines()[:6]),
            ]
            write_probe_log("P1", "\n".join(lines))
            print("\n".join(lines))
            return 0
    except Exception:  # noqa: BLE001 - probe records verbatim failure
        tb = traceback.format_exc()
        write_probe_log("P1", "P1 FAILED\n" + tb)
        print(tb, file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
