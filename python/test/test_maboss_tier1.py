"""Tier 1 tests for the MaBoSS Scout python tasks (plan Step 5).

Covers the shared bundle helpers and every inspection-side task:

- bundle helpers: ``validate_bundle_path`` / ``load_bundle`` / ``save_bundle``
  round-trip; member missing -> ``FileNotFoundError``; bad BND/CFG pair ->
  ``ValueError``.
- spec parsers: ``parse_node_spec``, ``parse_initial_state`` (all accepted
  forms plus every failure mode) and ``parse_state_string``.
- ``neko_export_bnet``: signed hand-written SIF -> ``.bnet``; bimodal SIF ->
  ``ValueError`` (both fixtures are plain files, no OmniPath).
- ``maboss_bnet_to_bnd_cfg``: BNET -> bundle directory with both members;
  the pair loads through ``maboss.load``.
- inspection tasks (``maboss_list_nodes``, ``maboss_get_initial_state``,
  ``maboss_get_logical_rules``, ``maboss_get_mutations``,
  ``maboss_get_parameters``): well-formed scout TSV.
- ``maboss_check``: Markdown artifact.

Run with the pymaboss python (scout runner on PYTHONPATH):

  env -u SCOUT_JOB_FILES_DIR \\
    PYTHONPATH="$HOME/.rvm/gems/ruby-3.3.1/gems/scout-rig-0.2.6/python" \\
    /home/mvazque2/software/micromamba/envs/pymaboss/bin/python \\
    python/test/test_maboss_tier1.py

``SCOUT_JOB_FILES_DIR`` is popped so every task falls back to the tempfile
artifact directory. Unit tests never touch OmniPath: the bridge fixtures are
hand-written SIF files and the network object is injected through a patched
``neko_common.load_network`` (the P4 probe's offline trick, formalized).
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
from maboss_check import maboss_check  # noqa: E402
from maboss_get_initial_state import maboss_get_initial_state  # noqa: E402
from maboss_get_logical_rules import maboss_get_logical_rules  # noqa: E402
from maboss_get_mutations import maboss_get_mutations  # noqa: E402
from maboss_get_parameters import maboss_get_parameters  # noqa: E402
from maboss_list_nodes import maboss_list_nodes  # noqa: E402
from neko_export_bnet import neko_export_bnet  # noqa: E402

#: The tiny 3-node BNET from probe P1/P3 (A<->B oscillator, C depends on A&B).
TINY_BNET = "targets, factors\nA, B\nB, A\nC, A & B\n"

#: Signed 3-node SIF: A -| B -> C (export_bnet's happy path).
SIGNED_SIF = "A\tinhibition\tB\nB\tstimulation\tC\n"

#: Same shape but the A->B edge is bimodal (export must refuse: 2 files).
BIMODAL_SIF = "A\tbimodal\tB\nB\tstimulation\tC\n"


def write_file(path: Path, text: str) -> Path:
    path.write_text(text, encoding="utf-8")
    return path


def read_tsv(path):
    """Return ``(fields, rows)`` from a scout-convention TSV artifact."""
    lines = [ln for ln in Path(path).read_text(encoding="utf-8").splitlines()
             if ln.strip()]
    if not lines:
        return (), []
    header = lines[0].lstrip("#")
    return tuple(header.split("\t")), [tuple(ln.split("\t")) for ln in lines[1:]]


def dir_sha256(directory: Path) -> dict:
    """sha256 of every file in a bundle directory (member -> digest)."""
    return {
        member.name: hashlib.sha256(member.read_bytes()).hexdigest()
        for member in sorted(Path(directory).iterdir())
        if member.is_file()
    }


def offline_network(sif_path, database: str = "omnipath"):
    """``neko_common.load_network`` replacement that never hits OmniPath.

    Builds the ``Network`` from the hand-written SIF with a tiny resources
    frame (the P4 probe trick), so the bridge task runs fully offline.
    """
    import pandas

    from neko.core.network import Network

    rows = [
        line.split("\t")
        for line in Path(sif_path).read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    return Network(
        sif_file=str(sif_path),
        resources=pandas.DataFrame(
            {"source": [row[0] for row in rows], "target": [row[2] for row in rows]}
        ),
    )


class MabossTier1TestCase(unittest.TestCase):
    """Shared fixture: one bundle converted from ``TINY_BNET``."""

    @classmethod
    def setUpClass(cls):
        os.environ.pop("SCOUT_JOB_FILES_DIR", None)
        cls.tmpdir = Path(tempfile.mkdtemp(prefix="maboss_tier1_"))
        cls.bnet = write_file(cls.tmpdir / "tiny.bnet", TINY_BNET)

    def setUp(self):
        # Fresh bundle per test: task calls may not share artifact dirs.
        self.bundle = Path(maboss_bnet_to_bnd_cfg(bnet_path=self.bnet))

    def assertTsv(self, path, expected_fields):
        path = Path(path)
        self.assertTrue(path.is_file(), f"missing TSV artifact {path}")
        fields, rows = read_tsv(path)
        self.assertTrue(path.read_text(encoding="utf-8").splitlines()[0].startswith("#"),
                        "TSV header line must start with '#'")
        self.assertEqual(fields, tuple(expected_fields))
        self.assertGreaterEqual(len(rows), 1, "TSV must contain at least one row")
        for row in rows:
            self.assertEqual(len(row), len(fields), f"ragged row {row}")
        return rows


class TestBundleHelpers(MabossTier1TestCase):
    """maboss_common bundle lifecycle (plan Step 5, first bullet)."""

    def test_validate_bundle_path_accepts_bundle(self):
        path = maboss_common.validate_bundle_path(self.bundle)
        self.assertEqual(path, self.bundle)

    def test_validate_missing_member_raises_filenotfound(self):
        broken = self.tmpdir / "broken_bundle"
        broken.mkdir(exist_ok=True)
        write_file(broken / "model.bnd", "bnd")
        with self.assertRaises(FileNotFoundError):
            maboss_common.validate_bundle_path(broken)

    def test_validate_missing_directory_raises_filenotfound(self):
        with self.assertRaises(FileNotFoundError):
            maboss_common.validate_bundle_path(self.tmpdir / "no_such_bundle")

    def test_load_bundle_returns_simulation(self):
        import maboss

        simulation = maboss_common.load_bundle(self.bundle)
        self.assertIsInstance(simulation, maboss.Simulation)

    def test_load_bundle_bad_pair_raises_valueerror(self):
        bad = self.tmpdir / "bad_pair"
        bad.mkdir(exist_ok=True)
        write_file(bad / "model.bnd", "this is not a bnd file")
        write_file(bad / "model.cfg", "max_time = 10;")
        with self.assertRaises(ValueError):
            maboss_common.load_bundle(bad)

    def test_save_bundle_round_trip(self):
        simulation = maboss_common.load_bundle(self.bundle)
        before = {str(node) for node in simulation.network.keys()}
        out = Path(maboss_common.save_bundle(simulation))
        self.assertTrue((out / "model.bnd").is_file())
        self.assertTrue((out / "model.cfg").is_file())
        reloaded = maboss_common.load_bundle(out)
        self.assertEqual(before, {str(node) for node in reloaded.network.keys()})

    def test_save_bundle_does_not_touch_input(self):
        simulation = maboss_common.load_bundle(self.bundle)
        before = dir_sha256(self.bundle)
        maboss_common.save_bundle(simulation)
        self.assertEqual(before, dir_sha256(self.bundle))


class TestSpecParsers(MabossTier1TestCase):
    """parse_node_spec / parse_initial_state / parse_state_string."""

    def test_parse_node_spec_single_string(self):
        self.assertEqual(maboss_common.parse_node_spec("C"), ["C"])

    def test_parse_node_spec_comma_list(self):
        self.assertEqual(maboss_common.parse_node_spec("A,B"), ["A", "B"])

    def test_parse_node_spec_list(self):
        self.assertEqual(maboss_common.parse_node_spec(["A", "B"]), ["A", "B"])

    def test_parse_node_spec_empty_fails(self):
        for bad in ("", "   ", [], ["", ""]):
            with self.assertRaises(ValueError):
                maboss_common.parse_node_spec(bad)

    def test_parse_initial_state_two_number_form(self):
        self.assertEqual(maboss_common.parse_initial_state("[0.25, 0.75]"),
                         [0.25, 0.75])

    def test_parse_initial_state_records_form(self):
        parsed = maboss_common.parse_initial_state(
            '[{"state": [0, 0], "probability": 0.5},'
            ' {"state": [1, 1], "probability": 0.5}]'
        )
        self.assertEqual(parsed, {(0, 0): 0.5, (1, 1): 0.5})

    def test_parse_initial_state_mapping_form(self):
        parsed = maboss_common.parse_initial_state('{"[0, 1]": 1.0}')
        self.assertEqual(parsed, {(0, 1): 1.0})

    def test_parse_initial_state_native_dict(self):
        self.assertEqual(maboss_common.parse_initial_state({0: 0.5, 1: 0.5}),
                         {0: 0.5, 1: 0.5})

    def test_parse_initial_state_wrong_length(self):
        with self.assertRaises(ValueError):
            maboss_common.parse_initial_state("[0.5]")

    def test_parse_initial_state_non_binary(self):
        with self.assertRaises(ValueError):
            maboss_common.parse_initial_state('{"[0, 2]": 1.0}')

    def test_parse_initial_state_duplicate_state(self):
        spec = ('[{"state": [0, 0], "probability": 0.5},'
                ' {"state": [0, 0], "probability": 0.5}]')
        with self.assertRaises(ValueError):
            maboss_common.parse_initial_state(spec)

    def test_parse_initial_state_probabilities_not_summing_to_one(self):
        with self.assertRaises(ValueError):
            maboss_common.parse_initial_state("[0.3, 0.3]")
        with self.assertRaises(ValueError):
            maboss_common.parse_initial_state('{"[0, 0]": 0.5, "[1, 1]": 0.2}')

    def test_parse_initial_state_out_of_range(self):
        with self.assertRaises(ValueError):
            maboss_common.parse_initial_state("[1.5, -0.5]")

    def test_parse_initial_state_bad_json(self):
        with self.assertRaises(ValueError):
            maboss_common.parse_initial_state("[0.5, ")

    def test_parse_state_string(self):
        self.assertEqual(maboss_common.parse_state_string("[0, 1]"), (0, 1))
        self.assertEqual(maboss_common.parse_state_string("0"), 0)
        self.assertIsNone(maboss_common.parse_state_string("not json"))
        self.assertIsNone(maboss_common.parse_state_string('{"a": 1}'))


class TestNekoExportBnet(MabossTier1TestCase):
    """neko_export_bnet on hand-written SIF fixtures (offline)."""

    def setUp(self):
        # No bundle needed; override MabossTier1TestCase.setUp.
        os.environ.pop("SCOUT_JOB_FILES_DIR", None)

    def test_signed_sif_exports_bnet(self):
        import neko_common

        sif = write_file(self.tmpdir / "signed.sif", SIGNED_SIF)
        original = neko_common.load_network
        neko_common.load_network = offline_network
        try:
            out = Path(neko_export_bnet(sif_path=sif))
        finally:
            neko_common.load_network = original

        self.assertTrue(out.is_file())
        self.assertEqual(out.suffix, ".bnet")
        text = out.read_text(encoding="utf-8")
        self.assertIn("targets, factors", text)
        self.assertIn("A", text)
        self.assertIn("B", text)

    def test_bimodal_sif_raises_value_error(self):
        import neko_common

        sif = write_file(self.tmpdir / "bimodal.sif", BIMODAL_SIF)
        original = neko_common.load_network
        neko_common.load_network = offline_network
        try:
            with self.assertRaises(ValueError) as caught:
                neko_export_bnet(sif_path=sif)
        finally:
            neko_common.load_network = original
        self.assertIn("Bimodal", str(caught.exception))

    def test_missing_sif_raises_file_not_found(self):
        with self.assertRaises(FileNotFoundError):
            neko_export_bnet(sif_path=self.tmpdir / "no_such.sif")


class TestBnetToBundle(MabossTier1TestCase):
    """maboss_bnet_to_bnd_cfg."""

    def test_converts_to_bundle_directory(self):
        self.assertTrue(self.bundle.is_dir())
        self.assertTrue((self.bundle / "model.bnd").is_file())
        self.assertTrue((self.bundle / "model.cfg").is_file())

    def test_pair_loads_with_maboss(self):
        simulation = maboss_common.load_bundle(self.bundle)
        nodes = {str(node) for node in simulation.network.keys()}
        self.assertEqual(nodes, {"A", "B", "C"})

    def test_missing_bnet_raises_file_not_found(self):
        from maboss_bnet_to_bnd_cfg import maboss_bnet_to_bnd_cfg as convert

        with self.assertRaises(FileNotFoundError):
            convert(bnet_path=self.tmpdir / "no_such.bnet")


class TestInspectionTasks(MabossTier1TestCase):
    """The five inspection tasks + maboss_check produce scout artifacts."""

    def test_list_nodes_tsv(self):
        rows = self.assertTsv(
            maboss_list_nodes(bundle=self.bundle),
            ["node", "is_output", "mutation_state"],
        )
        self.assertEqual({row[0] for row in rows}, {"A", "B", "C"})

    def test_get_initial_state_tsv(self):
        rows = self.assertTsv(
            maboss_get_initial_state(bundle=self.bundle),
            ["nodes", "state", "probability"],
        )
        probabilities = [float(row[2]) for row in rows]
        self.assertTrue(all(0.0 <= p <= 1.0 for p in probabilities))

    def test_get_logical_rules_tsv(self):
        rows = self.assertTsv(
            maboss_get_logical_rules(bundle=self.bundle),
            ["node", "rule", "is_output"],
        )
        rules = {row[0]: row[1] for row in rows}
        # bnet_to_bnd_and_cfg canonicalizes the rule into update form
        # ("(!C & (A & B)) | (C & (A & B))"); assert both operands survive.
        self.assertIn("A", rules["C"])
        self.assertIn("B", rules["C"])
        self.assertIn("&", rules["C"])

    def test_get_mutations_tsv(self):
        rows = self.assertTsv(
            maboss_get_mutations(bundle=self.bundle),
            ["node", "state"],
        )
        self.assertEqual(rows, [("- none -", "")])

    def test_get_parameters_tsv(self):
        rows = self.assertTsv(
            maboss_get_parameters(bundle=self.bundle),
            ["parameter", "value"],
        )
        parameters = dict(rows)
        self.assertIn("max_time", parameters)
        self.assertIn("time_tick", parameters)
        self.assertIn("sample_count", parameters)

    def test_check_writes_markdown(self):
        out = Path(maboss_check(bundle=self.bundle))
        self.assertTrue(out.is_file())
        self.assertEqual(out.suffix, ".md")
        text = out.read_text(encoding="utf-8")
        self.assertTrue(text.startswith("# "), "markdown must start with a heading")

    def test_all_tasks_take_bundle_directory(self):
        # Every inspection task resolves members from ONE returned path.
        for task_function in (
            maboss_list_nodes,
            maboss_get_initial_state,
            maboss_get_logical_rules,
            maboss_get_mutations,
            maboss_get_parameters,
        ):
            out = Path(task_function(bundle=self.bundle))
            self.assertTrue(out.is_file(), f"{task_function.__name__} wrote nothing")


if __name__ == "__main__":
    unittest.main(verbosity=2)
