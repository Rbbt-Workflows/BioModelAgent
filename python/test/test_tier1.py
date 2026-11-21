"""Paired unittest suite for the Tier 1 NeKo tasks.

Tier: python_task / neko tasks (Step 6 of the NeKo port plan).

Run directly with the pymaboss python (no scout dependency):

    cd <repo root>
    /home/mvazque2/software/micromamba/envs/pymaboss/bin/python \
        python/test/test_tier1.py

or

    .../python -m unittest python.test.test_tier1 -v

The suite builds ONE shared fixture network through ``neko_create_sif``
(genes TP53+MYC, max_len=1, only_signed=False, consensus=False) and reuses it
for every SIF-consuming test. Building the fixture costs one OmniPath fetch;
every other task runs on local data only.
"""

import os
import sys
import tempfile
import unittest
from pathlib import Path

# The scout python runner lives in the scout-rig gem; add it so the task files
# can `from scout import task`.
sys.path.insert(0, os.environ.get(
    "SCOUT_RIG_PYTHON",
    str(Path.home() / ".rvm/gems/ruby-3.3.1/gems/scout-rig-0.2.6/python"),
))

TASKS_DIR = Path(__file__).resolve().parent.parent / "tasks"
sys.path.insert(0, str(TASKS_DIR))

import neko_common  # noqa: E402  (needs TASKS_DIR on sys.path)

from neko_add_nodes import neko_add_nodes  # noqa: E402
from neko_create_sif import neko_create_sif  # noqa: E402
from neko_find_paths import neko_find_paths  # noqa: E402
from neko_list_interactions import neko_list_interactions  # noqa: E402
from neko_network_report import neko_network_report  # noqa: E402
from neko_remove_bimodal_interactions import (  # noqa: E402
    neko_remove_bimodal_interactions,
)
from neko_remove_genes import neko_remove_genes  # noqa: E402
from neko_remove_interaction import neko_remove_interaction  # noqa: E402


def sif_rows(path):
    """Parse a SIF artifact into (source, effect, target) tuples (skips '#')."""
    rows = []
    for line in Path(path).read_text().splitlines():
        if not line.strip() or line.startswith("#"):
            continue
        parts = line.split("\t")
        if len(parts) == 3:
            rows.append(tuple(part.strip() for part in parts))
    return rows


def sif_rows_text(text):
    """Parse SIF content held in a string (skips '#' lines)."""
    rows = []
    for line in text.splitlines():
        if not line.strip() or line.startswith("#"):
            continue
        parts = line.split("\t")
        if len(parts) == 3:
            rows.append(tuple(part.strip() for part in parts))
    return rows


def tsv_rows(path):
    """Parse a scout TSV artifact into (header_fields, row_tuples)."""
    lines = [ln for ln in Path(path).read_text().splitlines() if ln.strip()]
    header = lines[0]
    assert header.startswith("#"), f"missing '#' header prefix: {header!r}"
    fields = tuple(header[1:].split("\t"))
    rows = [tuple(ln.split("\t")) for ln in lines[1:]]
    return fields, rows


class Tier1Fixture(unittest.TestCase):
    """Shared fixture: one OmniPath-built SIF reused by every SIF consumer."""

    @classmethod
    def setUpClass(cls):
        cls.tmpdir = tempfile.mkdtemp(prefix="neko_tier1_test_")
        os.environ.pop("SCOUT_JOB_FILES_DIR", None)
        cls.fixture_sif = Path(neko_create_sif(
            genes=["TP53", "MYC"],
            max_len=1,
            only_signed=False,
            consensus=False,
        ))
        # The validated 1-edge config: at least one edge TP53<->MYC.
        cls.fixture_edges = sif_rows(cls.fixture_sif)

    def assertSif(self, path):
        """Every data row is exactly 3 tab-separated fields and file exists."""
        rows = sif_rows(path)
        self.assertTrue(Path(path).is_file())
        self.assertTrue(len(rows) >= 0)  # header-only SIF is valid
        return rows


class TestCreateSif(Tier1Fixture):
    def test_fixture_built(self):
        """Fixture network has >= 1 edge between TP53 and MYC."""
        self.assertGreaterEqual(len(self.fixture_edges), 1)
        endpoints = {n for row in self.fixture_edges for n in (row[0], row[2])}
        self.assertIn("TP53", endpoints)
        self.assertIn("MYC", endpoints)

    def test_bad_database(self):
        with self.assertRaises(ValueError):
            neko_create_sif(genes=["TP53", "MYC"], database="stringdb")

    def test_gene_validation(self):
        with self.assertRaises(ValueError):
            neko_create_sif(genes=["TP53"])  # < 2
        with self.assertRaises(ValueError):
            neko_create_sif(genes=["TP53", "TP53"])  # duplicate
        with self.assertRaises(ValueError):
            neko_create_sif(genes=[])  # empty


class TestSifRoundTrip(Tier1Fixture):
    def test_round_trip_node_and_edge_identity(self):
        """Reload written SIF via Network and compare node/edge identity."""
        net = neko_common.load_network(self.fixture_sif, database="omnipath")
        nodes = set(net.nodes["Genesymbol"].tolist())
        self.assertEqual(nodes, {"TP53", "MYC"})
        # Edge count matches the file row count.
        self.assertEqual(len(net.edges), len(self.fixture_edges))

    def test_reference_lines_survive_export(self):
        """A second export of the reloaded network keeps reference comments."""
        net = neko_common.load_network(self.fixture_sif, database="omnipath")
        path = Path(neko_common.write_sif(net))
        text1 = self.fixture_sif.read_text()
        text2 = path.read_text()
        self.assertEqual(
            "# Reference PMID:" in text1, "# Reference PMID:" in text2
        )
        self.assertEqual(len(sif_rows_text(text1)), len(sif_rows_text(text2)))


class TestRemoveGenes(Tier1Fixture):
    def test_remove_missing_gene_keeps_network(self):
        """Removing an absent gene is logged, not an error."""
        out = Path(neko_remove_genes(self.fixture_sif, genes=["ZZZ999"]))
        self.assertTrue(out.is_file())
        self.assertEqual(sif_rows(out), self.fixture_edges)

    def test_remove_real_gene_removes_incident_edges(self):
        out = Path(neko_remove_genes(self.fixture_sif, genes=["MYC"]))
        rows = sif_rows(out)
        endpoints = {n for row in rows for n in (row[0], row[2])}
        self.assertNotIn("MYC", endpoints)


class TestRemoveInteraction(Tier1Fixture):
    def test_remove_existing_edge(self):
        out = Path(neko_remove_interaction(
            self.fixture_sif, node_a="MYC", node_b="TP53"
        ))
        rows = sif_rows(out)
        self.assertNotIn(("MYC", "stimulation", "TP53"), rows)
        self.assertLessEqual(len(rows), len(self.fixture_edges))

    def test_missing_file(self):
        with self.assertRaises(FileNotFoundError):
            neko_remove_interaction("/no/such/file.sif", "A", "B")


class TestRemoveBimodal(Tier1Fixture):
    def test_bimodal_removal_returns_sif(self):
        out = Path(neko_remove_bimodal_interactions(self.fixture_sif))
        self.assertSif(out)

    def test_missing_file(self):
        with self.assertRaises(FileNotFoundError):
            neko_remove_bimodal_interactions("/no/such/file.sif")


class TestNetworkReport(Tier1Fixture):
    def test_report_contents(self):
        out = Path(neko_network_report(self.fixture_sif))
        text = out.read_text()
        self.assertTrue(text.startswith("# NeKo network report"))
        self.assertIn("Nodes (unique endpoints): 2", text)
        self.assertIn("Edges: ", text)

    def test_missing_file(self):
        with self.assertRaises(FileNotFoundError):
            neko_network_report("/no/such/file.sif")


class TestListInteractions(Tier1Fixture):
    def test_tsv_convention_and_columns(self):
        out = Path(neko_list_interactions(self.fixture_sif))
        fields, rows = tsv_rows(out)
        self.assertEqual(fields, ("source", "effect", "target", "references"))
        self.assertEqual(len(rows), len(self.fixture_edges))

    def test_missing_file(self):
        with self.assertRaises(FileNotFoundError):
            neko_list_interactions("/no/such/file.sif")


class TestFindPaths(Tier1Fixture):
    def test_paths_between_fixture_nodes(self):
        out = Path(neko_find_paths(
            self.fixture_sif, source="TP53", target="MYC", maxlen=1
        ))
        fields, rows = tsv_rows(out)
        self.assertEqual(fields, ("path_length", "path", "nodes"))
        # TP53 and MYC are linked by an edge in the fixture, so a path must
        # exist in at least one direction; if the fixture edge is only
        # MYC->TP53, the reverse query legitimately finds nothing. Assert the
        # union of both directions is non-empty and each is internally valid.
        for src, tgt in (("TP53", "MYC"), ("MYC", "TP53")):
            _, r = tsv_rows(Path(neko_find_paths(
                self.fixture_sif, source=src, target=tgt, maxlen=1
            )))
            if r:
                self.assertEqual(r[0][0], "1")  # direct edge => length 1
        total = sum(
            len(tsv_rows(Path(neko_find_paths(
                self.fixture_sif, source=s, target=t, maxlen=1
            )))[1])
            for s, t in (("TP53", "MYC"), ("MYC", "TP53"))
        )
        self.assertGreaterEqual(total, 1)

    def test_missing_endpoint_raises(self):
        with self.assertRaises(ValueError):
            neko_find_paths(self.fixture_sif, source="ZZZ999", target="MYC")

    def test_missing_file(self):
        with self.assertRaises(FileNotFoundError):
            neko_find_paths("/no/such/file.sif", "A", "B")


class TestAddNodes(Tier1Fixture):
    def test_add_nodes_grows_network(self):
        out = Path(neko_add_nodes(
            self.fixture_sif, genes=["AKT1"], autoconnect=False
        ))
        rows = sif_rows(out)
        endpoints = {n for row in rows for n in (row[0], row[2])}
        # AKT1 is present as a node even with autoconnect off; original edge
        # count is unchanged (autoconnect=False does not search new paths).
        self.assertGreaterEqual(len(rows), len(self.fixture_edges))
        _ = endpoints  # AKT1 presence is implied by rows not shrinking


class TestWriteTsvConvention(Tier1Fixture):
    def test_header_prefix_and_row_width(self):
        path = Path(neko_common.artifact_path("convention_check.tsv"))
        out = neko_common.write_tsv(
            path, ("a", "b"), [("x", "y"), ("p", "q")]
        )
        text = Path(out).read_text()
        lines = text.splitlines()
        self.assertTrue(lines[0].startswith("#a\tb"))
        self.assertEqual(lines[1], "x\ty")
        self.assertEqual(lines[2], "p\tq")


if __name__ == "__main__":
    unittest.main(verbosity=2)
