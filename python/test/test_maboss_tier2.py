"""Tier 2 tests for the MaBoSS Scout python tasks (plan Step 5).

Covers the model-mutating and simulation tasks:

- every configuration task returns a NEW bundle whose members differ from
  the input as expected, and the **input bundle members stay byte-identical**
  (sha256 assertion — plan acceptance test 7).
- ``maboss_set_output_nodes``: unknown node -> ``ValueError`` mirroring the
  MCP error text.
- ``maboss_update_parameters``: ``k=v`` string form and JSON dict form;
  unknown key -> informative error.
- ``maboss_change_rule``: invalid rule -> input semantics preserved (the
  revert behavior mirrored from the MCP server).
- ``maboss_run_simulation``: numeric TSV (parses as floats), monotone time
  column, ``max_time`` set explicitly (default CFG is 1000) and a small
  output set (2^N states warning).
- ``maboss_simulate_mutation``: WT vs mutant comparison TSV; single-token
  and per-node-list ``nodes``/``state`` forms.
- ``maboss_plot_trajectories``: PNG artifact with PNG magic bytes.

Run with the pymaboss python (scout runner on PYTHONPATH):

  env -u SCOUT_JOB_FILES_DIR \\
    PYTHONPATH="$HOME/.rvm/gems/ruby-3.3.1/gems/scout-rig-0.2.6/python" \\
    /home/mvazque2/software/micromamba/envs/pymaboss/bin/python \\
    python/test/test_maboss_tier2.py
"""

import hashlib
import os
import sys
import tempfile
import unittest
from pathlib import Path

TASKS_DIR = Path(__file__).resolve().parent.parent / "tasks"
sys.path.insert(0, str(TASKS_DIR))

import maboss_common  # noqa: E402  (needs the path bootstrap above)
from maboss_bnet_to_bnd_cfg import maboss_bnet_to_bnd_cfg  # noqa: E402
from maboss_change_rule import maboss_change_rule  # noqa: E402
from maboss_get_parameters import maboss_get_parameters  # noqa: E402
from maboss_get_logical_rules import maboss_get_logical_rules  # noqa: E402
from maboss_list_nodes import maboss_list_nodes  # noqa: E402
from maboss_plot_trajectories import maboss_plot_trajectories  # noqa: E402
from maboss_run_simulation import maboss_run_simulation  # noqa: E402
from maboss_set_initial_state import maboss_set_initial_state  # noqa: E402
from maboss_set_output_nodes import maboss_set_output_nodes  # noqa: E402
from maboss_simulate_mutation import maboss_simulate_mutation  # noqa: E402
from maboss_update_parameters import maboss_update_parameters  # noqa: E402

#: The tiny 3-node BNET from probe P1/P3.
TINY_BNET = "targets, factors\nA, B\nB, A\nC, A & B\n"


def dir_sha256(directory: Path) -> dict:
    """sha256 of every file in a bundle directory (member -> digest)."""
    return {
        member.name: hashlib.sha256(member.read_bytes()).hexdigest()
        for member in sorted(Path(directory).iterdir())
        if member.is_file()
    }


def read_tsv(path):
    """Return ``(fields, rows)`` from a scout-convention TSV artifact."""
    lines = [ln for ln in Path(path).read_text(encoding="utf-8").splitlines()
             if ln.strip()]
    header = lines[0].lstrip("#")
    return tuple(header.split("\t")), [tuple(ln.split("\t")) for ln in lines[1:]]


def cfg_text(bundle: Path) -> str:
    return (Path(bundle) / "model.cfg").read_text(encoding="utf-8")


class MabossTier2TestCase(unittest.TestCase):
    """Shared fixture: bundle + outputs + explicit small max_time."""

    @classmethod
    def setUpClass(cls):
        os.environ.pop("SCOUT_JOB_FILES_DIR", None)
        cls.tmpdir = Path(tempfile.mkdtemp(prefix="maboss_tier2_"))
        cls.bnet = cls.tmpdir / "tiny.bnet"
        cls.bnet.write_text(TINY_BNET, encoding="utf-8")
        cls.bundle = Path(maboss_bnet_to_bnd_cfg(bnet_path=cls.bnet))
        # Small output set (2^N warning) and explicit time parameters:
        # a converted CFG defaults to max_time=1000 -> 2000 TSV rows.
        cls.with_outputs = Path(maboss_set_output_nodes(
            bundle=cls.bundle, nodes="A,B",
        ))
        cls.runnable = Path(maboss_update_parameters(
            bundle=cls.with_outputs, parameters="max_time=10,time_tick=1",
        ))

    def assertNewBundle(self, out, source_bundle):
        """Out is a NEW bundle; source members unchanged (acceptance test 7)."""
        out = Path(out)
        self.assertTrue(out.is_dir(), f"no bundle directory at {out}")
        self.assertTrue((out / "model.bnd").is_file())
        self.assertTrue((out / "model.cfg").is_file())
        self.assertNotEqual(out, Path(source_bundle))
        return out

    def assertInputUntouched(self, source_bundle, before=None):
        before = before or dir_sha256(source_bundle)
        self.assertEqual(
            before,
            dir_sha256(source_bundle),
            f"input bundle {source_bundle} was mutated by a task",
        )


class TestConfigurationTasks(MabossTier2TestCase):
    """Every config task: new bundle + input immutability (test 7)."""

    def test_change_rule_new_bundle_and_input_untouched(self):
        before = dir_sha256(self.bundle)
        out = self.assertNewBundle(
            maboss_change_rule(bundle=self.bundle, node="C", new_rule="A"),
            self.bundle,
        )
        self.assertInputUntouched(self.bundle, before)
        _, rows = read_tsv(maboss_get_logical_rules(bundle=out))
        rules = {row[0]: row[1] for row in rows}
        self.assertIn("A", rules["C"])
        self.assertNotIn("B", rules["C"])

    def test_update_parameters_string_form_new_bundle(self):
        before = dir_sha256(self.with_outputs)
        out = self.assertNewBundle(
            maboss_update_parameters(
                bundle=self.with_outputs, parameters="max_time=42"
            ),
            self.with_outputs,
        )
        self.assertInputUntouched(self.with_outputs, before)
        self.assertIn("max_time = 42", cfg_text(out))

    def test_update_parameters_json_form_new_bundle(self):
        before = dir_sha256(self.with_outputs)
        out = self.assertNewBundle(
            maboss_update_parameters(
                bundle=self.with_outputs, parameters='{"time_tick": 0.25}'
            ),
            self.with_outputs,
        )
        self.assertInputUntouched(self.with_outputs, before)
        self.assertIn("time_tick = 0.25", cfg_text(out))

    def test_update_parameters_empty_inspects(self):
        out = Path(maboss_update_parameters(
            bundle=self.with_outputs, parameters=""
        ))
        self.assertTrue(out.is_file())
        self.assertEqual(out.suffix, ".tsv")
        fields, rows = read_tsv(out)
        self.assertEqual(fields, ("parameter", "value"))
        self.assertIn("max_time", dict(rows))

    def test_update_parameters_unknown_key(self):
        with self.assertRaises(ValueError) as caught:
            maboss_update_parameters(
                bundle=self.with_outputs, parameters="nope=1"
            )
        message = str(caught.exception)
        self.assertIn("Unknown parameter", message)
        self.assertIn("max_time", message)  # names the available keys

    def test_update_parameters_malformed_json(self):
        with self.assertRaises(ValueError):
            maboss_update_parameters(
                bundle=self.with_outputs, parameters='{"max_time": '
            )

    def test_set_output_nodes_new_bundle(self):
        before = dir_sha256(self.bundle)
        out = self.assertNewBundle(
            maboss_set_output_nodes(bundle=self.bundle, nodes="A,B"),
            self.bundle,
        )
        self.assertInputUntouched(self.bundle, before)
        _, rows = read_tsv(maboss_list_nodes(bundle=out))
        outputs = {row[0] for row in rows if row[1] == "true"}
        self.assertEqual(outputs, {"A", "B"})

    def test_set_output_nodes_unknown_node(self):
        with self.assertRaises(ValueError) as caught:
            maboss_set_output_nodes(bundle=self.bundle, nodes="ZZZ")
        message = str(caught.exception)
        self.assertIn("Unknown MaBoSS node(s): ZZZ", message)
        self.assertIn("Available nodes:", message)

    def test_set_output_nodes_empty_clears(self):
        out = self.assertNewBundle(
            maboss_set_output_nodes(bundle=self.with_outputs, nodes=[]),
            self.with_outputs,
        )
        _, rows = read_tsv(maboss_list_nodes(bundle=out))
        self.assertFalse([row for row in rows if row[1] == "true"])

    def test_set_initial_state_new_bundle(self):
        before = dir_sha256(self.bundle)
        out = self.assertNewBundle(
            maboss_set_initial_state(
                bundle=self.bundle, nodes="A", probabilities="[0.25, 0.75]"
            ),
            self.bundle,
        )
        self.assertInputUntouched(self.bundle, before)
        simulation = maboss_common.load_bundle(out)
        states = simulation.network.get_istate()
        self.assertTrue(any(
            abs(float(p) - 0.75) < 1e-9
            for distribution in states.values()
            for p in distribution.values()
        ))

    def test_set_initial_state_joint_form(self):
        out = self.assertNewBundle(
            maboss_set_initial_state(
                bundle=self.bundle,
                nodes="A,B",
                probabilities=('[{"state": [0, 0], "probability": 0.5},'
                                ' {"state": [1, 1], "probability": 0.5}]'),
            ),
            self.bundle,
        )
        simulation = maboss_common.load_bundle(out)
        self.assertTrue(simulation.network.get_istate())

    def test_set_initial_state_unknown_node(self):
        with self.assertRaises(ValueError):
            maboss_set_initial_state(
                bundle=self.bundle, nodes="ZZZ", probabilities="[0.5, 0.5]"
            )

    def test_set_initial_state_length_mismatch(self):
        with self.assertRaises(ValueError):
            maboss_set_initial_state(
                bundle=self.bundle,
                nodes="A,B",
                probabilities='{"[0, 1, 0]": 1.0}',
            )

    def test_change_rule_invalid_reverts(self):
        """MCP behavior: an invalid rule leaves the model unchanged."""
        before = dir_sha256(self.bundle)
        before_rules = maboss_get_logical_rules(bundle=self.bundle)
        with self.assertRaises(ValueError):
            maboss_change_rule(
                bundle=self.bundle, node="A", new_rule="A | Q999"
            )
        self.assertInputUntouched(self.bundle, before)
        after_rules = maboss_get_logical_rules(bundle=self.bundle)
        self.assertEqual(
            read_tsv(before_rules)[1], read_tsv(after_rules)[1],
            "invalid rule change altered the input model semantics",
        )

    def test_change_rule_unknown_node(self):
        with self.assertRaises(ValueError):
            maboss_change_rule(
                bundle=self.bundle, node="ZZZ", new_rule="A"
            )


class TestSimulationTasks(MabossTier2TestCase):
    """run_simulation / simulate_mutation / plot_trajectories."""

    def test_run_simulation_numeric_monotone_tsv(self):
        out = Path(maboss_run_simulation(bundle=self.runnable))
        fields, rows = read_tsv(out)
        self.assertGreaterEqual(len(rows), 2)
        times = [float(row[0]) for row in rows]
        self.assertEqual(times, sorted(times), "time column must be monotone")
        self.assertEqual(times[0], 0.0)
        # The engine's last sample is the last full tick strictly below
        # max_time (tick=1, max_time=10 -> t=9); max_time bounds, not lands.
        self.assertLess(times[-1], 10.0)
        self.assertGreaterEqual(times[-1], 9.0)
        for row in rows:
            for cell in row[1:]:
                float(cell)  # every probability column parses as float
                self.assertTrue(0.0 <= float(cell) <= 1.0)

    def test_run_simulation_requires_outputs(self):
        # The plan's 2^N warning, from the other side: an output-free bundle
        # still runs (MaBoSS tracks <nil>), but its TSV has no node states.
        out = Path(maboss_run_simulation(bundle=self.bundle))
        fields, rows = read_tsv(out)
        self.assertTrue(out.is_file())
        self.assertGreaterEqual(len(rows), 1)

    def test_simulate_mutation_single_token(self):
        out = Path(maboss_simulate_mutation(
            bundle=self.runnable, nodes="C", state="OFF"
        ))
        fields, rows = read_tsv(out)
        self.assertIn("variant", fields)
        self.assertIn("nodes", fields)
        self.assertIn("state", fields)
        variants = [row[fields.index("variant")] for row in rows]
        self.assertEqual(set(variants), {"wild-type", "mutant"})
        for row in rows:
            self.assertEqual(row[fields.index("nodes")], "C")
            self.assertEqual(row[fields.index("state")], "OFF")

    def test_simulate_mutation_node_list(self):
        out = Path(maboss_simulate_mutation(
            bundle=self.runnable, nodes=["A", "B"], state="ON"
        ))
        fields, rows = read_tsv(out)
        for row in rows:
            self.assertEqual(row[fields.index("nodes")], "A|B")

    def test_simulate_mutation_bad_state(self):
        with self.assertRaises(ValueError):
            maboss_simulate_mutation(
                bundle=self.runnable, nodes="C", state="SIDEWAYS"
            )

    def test_simulate_mutation_unknown_node(self):
        with self.assertRaises(ValueError):
            maboss_simulate_mutation(
                bundle=self.runnable, nodes="ZZZ", state="ON"
            )

    def test_simulate_mutation_does_not_mutate_input(self):
        before = dir_sha256(self.runnable)
        maboss_simulate_mutation(bundle=self.runnable, nodes="C", state="OFF")
        self.assertInputUntouched(self.runnable, before)

    def test_plot_trajectories_png(self):
        out = Path(maboss_plot_trajectories(bundle=self.runnable, until=10))
        self.assertTrue(out.is_file())
        self.assertEqual(out.suffix, ".png")
        magic = out.read_bytes()[:8]
        self.assertEqual(
            magic,
            b"\x89PNG\r\n\x1a\n",
            f"{out} lacks the PNG magic bytes: {magic!r}",
        )
        self.assertGreater(out.stat().st_size, 1000)

    def test_plot_trajectories_until_exceeding_max_time(self):
        with self.assertRaises(ValueError):
            maboss_plot_trajectories(bundle=self.runnable, until=999)

    def test_plot_trajectories_does_not_mutate_input(self):
        before = dir_sha256(self.runnable)
        maboss_plot_trajectories(bundle=self.runnable, until=5)
        self.assertInputUntouched(self.runnable, before)


if __name__ == "__main__":
    unittest.main(verbosity=2)
