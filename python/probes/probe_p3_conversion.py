"""Step 1 probe P3: BNET -> BND/CFG conversion round-trip.

Converts a tiny BNET, shows the generated BND/CFG, and confirms a re-load
works and preserves the logical rules.
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

sys.path.insert(0, str(Path(__file__).resolve().parent))


def main() -> int:
    from maboss_probe_common import write_probe_log

    lines = []
    try:
        import maboss

        with tempfile.TemporaryDirectory(prefix="p3_") as tmp:
            tmp_path = Path(tmp)
            bnet = tmp_path / "tiny.bnet"
            bnet.write_text(BNET, encoding="utf-8")
            bnd, cfg = tmp_path / "model.bnd", tmp_path / "model.cfg"
            maboss.bnet_to_bnd_and_cfg(str(bnet), str(bnd), str(cfg))
            lines.append("P3 OK")
            lines.append(f"  BND ({bnd.stat().st_size} B):")
            lines.extend("    " + ln for ln in bnd.read_text().strip().splitlines())
            lines.append(f"  CFG ({cfg.stat().st_size} B):")
            lines.extend("    " + ln for ln in cfg.read_text().strip().splitlines())

            sim = maboss.load(str(bnd), str(cfg))
            rules = sim.get_logical_rules()
            lines.append(f"  reload get_logical_rules type={type(rules).__name__}")
            lines.append(f"    {rules!r}")

        write_probe_log("P3", "\n".join(lines))
        print("\n".join(lines))
        return 0
    except Exception:  # noqa: BLE001
        tb = traceback.format_exc()
        write_probe_log("P3", "P3 FAILED\n" + tb)
        print(tb, file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
