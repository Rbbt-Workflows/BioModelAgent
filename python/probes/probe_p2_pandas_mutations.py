"""Step 1 probe P2: pandas 3.0.6 compatibility and the mutation path.

Checks ``DataFrame.to_csv(sep='\\t')`` on the trajectory tables and the full
``sim.copy().mutate(node, state).run()`` comparison path the MCP server uses.
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
        import pandas

        lines.append(f"P2 OK: pandas={pandas.__version__}")
        with tempfile.TemporaryDirectory(prefix="p2_") as tmp:
            tmp_path = Path(tmp)
            bnet = tmp_path / "tiny.bnet"
            bnet.write_text(BNET, encoding="utf-8")
            bnd, cfg = tmp_path / "m.bnd", tmp_path / "m.cfg"
            maboss.bnet_to_bnd_and_cfg(str(bnet), str(bnd), str(cfg))
            sim = maboss.load(str(bnd), str(cfg))
            sim.network.set_output(["A", "B", "C"])
            wt = sim.run()
            df = wt.get_last_states_probtraj()
            lines.append(f"  WT last probtraj: shape={df.shape} index_name={df.index.name} cols={list(df.columns)}")
            lines.append("  WT to_csv head:")
            for ln in df.to_csv(sep="\t").strip().splitlines()[:5]:
                lines.append("    " + ln)

            # get_state_probtraj (full trajectory) — used by plots and richer tables
            try:
                traj = wt.get_states_probtraj()
                lines.append(
                    f"  get_states_probtraj: type={type(traj).__name__} shape={traj.shape} cols={list(traj.columns)[:6]}"
                )
                lines.append("  trajectory to_csv head:")
                for ln in traj.to_csv(sep="\t").strip().splitlines()[:4]:
                    lines.append("    " + ln)
            except Exception as exc:  # noqa: BLE001
                lines.append(f"  get_states_probtraj FAILED: {type(exc).__name__}: {exc}")

            # Mutation path used by simulate_mutation (mutate() returns None:
            # it mutates in place, so the MCP pattern is copy -> mutate -> run)
            for state in ("ON", "OFF", "WT"):
                mut_sim = sim.copy()
                assert mut_sim is not None
                mut_sim.mutate("A", state)
                mut = mut_sim.run()
                mdf = mut.get_last_states_probtraj()
                lines.append(
                    f"  mutate(A,{state}) -> shape={mdf.shape} vals={list(mdf.iloc[0].round(4))}"
                )

            # get_mutations / param dict
            lines.append(f"  get_mutations: {sim.get_mutations()}")
            lines.append(
                f"  param max_time={sim.param['max_time']} time_tick={sim.param['time_tick']} sample_count={sim.param['sample_count']}"
            )

        write_probe_log("P2", "\n".join(lines))
        print("\n".join(lines))
        return 0
    except Exception:  # noqa: BLE001
        tb = traceback.format_exc()
        write_probe_log("P2", "P2 FAILED\n" + tb)
        print(tb, file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
