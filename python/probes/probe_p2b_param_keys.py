"""Step 1 probe P2b: enumerate the real ``sim.param`` keys."""
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))


def main() -> int:
    from maboss_probe_common import write_probe_log

    import maboss

    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        bnet = tmp_path / "m.bnet"
        bnet.write_text("targets, factors\nA, B\nB, A\nC, A & !B\n")
        maboss.bnet_to_bnd_and_cfg(str(bnet), str(tmp_path / "m.bnd"), str(tmp_path / "m.cfg"))
        sim = maboss.load(str(tmp_path / "m.bnd"), str(tmp_path / "m.cfg"))
        keys = sorted(sim.param.keys())
        lines = ["P2b param keys:"] + [f"  {k} = {sim.param[k]!r}" for k in keys]
        write_probe_log("P2", "\n".join(lines))
        print("\n".join(lines))
    return 0


if __name__ == "__main__":
    sys.exit(main())
