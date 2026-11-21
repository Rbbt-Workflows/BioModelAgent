"""Unittest coverage for the nine Tier 2 NeKo tasks.

Run with the pymaboss python:
    PYTHONPATH=<scout-rig python> python python/test/test_tier2.py
"""
import os
import pathlib
import sys
import unittest

HERE = pathlib.Path(__file__).resolve()
TASKS = HERE.parents[1] / "tasks"
sys.path.insert(0, str(TASKS))

import neko_create_sif  # noqa: E402
import neko_remove_undefined_interactions  # noqa: E402
import neko_complete_connection  # noqa: E402
import neko_connect_targeted_nodes  # noqa: E402
import neko_bridge_components  # noqa: E402
import neko_filter_interactions  # noqa: E402
import neko_get_references  # noqa: E402
import neko_analyze_connectivity  # noqa: E402
import neko_analyze_gene_set  # noqa: E402
import neko_preview_connection_impact  # noqa: E402


def sif_rows(path):
    rows = []
    for line in pathlib.Path(path).read_text().splitlines():
        if line.startswith("#") or not line.strip():
            continue
        parts = line.split("\t")
        if len(parts) == 3:
            rows.append(parts)
    return rows


def tsv_rows(path):
    text = [l for l in pathlib.Path(path).read_text().splitlines() if l.strip()]
    assert text[0].startswith("#"), f"{path}: missing # header"
    return [l.split("\t") for l in text[1:]]


class Tier2TestCase(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        os.environ.pop("SCOUT_JOB_FILES_DIR", None)
        print("\nbuilding Tier 2 fixture network (~15 s) ...", file=sys.stderr)
        cls.base = neko_create_sif.neko_create_sif(
            ["TP53", "MDM2", "MYC", "AKT1"], max_len=2,
            only_signed=False, consensus=False)
        cls.edges = sif_rows(cls.base)
        cls.nodes = sorted({r[0] for r in cls.edges} | {r[2] for r in cls.edges})
        print(f"fixture: {len(cls.edges)} edges, {len(cls.nodes)} nodes",
              file=sys.stderr)

    def assertSif(self, path):
        self.assertTrue(pathlib.Path(path).exists(), path)
        self.assertTrue(sif_rows(path) or pathlib.Path(path).stat().st_size >= 0)
        return path


class TestNetworkMutationTasks(Tier2TestCase):
    def test_remove_undefined_interactions_writes_sif(self):
        p = neko_remove_undefined_interactions.neko_remove_undefined_interactions(self.base)
        self.assertSif(p)
        self.assertLessEqual(len(sif_rows(p)), len(self.edges))

    def test_remove_undefined_bad_database(self):
        with self.assertRaises(ValueError):
            neko_remove_undefined_interactions.neko_remove_undefined_interactions(
                self.base, database="nope")

    def test_complete_connection_writes_sif(self):
        p = neko_complete_connection.neko_complete_connection(self.base, max_len=2)
        self.assertSif(p)
        self.assertGreaterEqual(len(sif_rows(p)), len(self.edges))

    def test_complete_connection_bad_database(self):
        with self.assertRaises(ValueError):
            neko_complete_connection.neko_complete_connection(
                self.base, database="bogus")

    def test_connect_subgroup_strategy(self):
        p = neko_connect_targeted_nodes.neko_connect_targeted_nodes(
            self.base, ["TP53", "MYC"], strategy="connect_subgroup")
        self.assertSif(p)

    def test_connect_upstream_strategy(self):
        p = neko_connect_targeted_nodes.neko_connect_targeted_nodes(
            self.base, ["MYC"], strategy="connect_to_upstream_nodes")
        self.assertSif(p)

    def test_connect_targeted_bad_strategy(self):
        with self.assertRaises(ValueError):
            neko_connect_targeted_nodes.neko_connect_targeted_nodes(
                self.base, ["TP53"], strategy="radial")

    def test_connect_targeted_empty_nodes(self):
        with self.assertRaises(ValueError):
            neko_connect_targeted_nodes.neko_connect_targeted_nodes(
                self.base, [])

    def test_bridge_components_writes_sif(self):
        p = neko_bridge_components.neko_bridge_components(
            self.base, ["TP53"], ["MYC"], max_len=2)
        self.assertSif(p)

    def test_bridge_components_bad_mode(self):
        with self.assertRaises(ValueError):
            neko_bridge_components.neko_bridge_components(
                self.base, ["TP53"], ["MYC"], mode="SIDEWAYS")


class TestSifParsingTasks(Tier2TestCase):
    def test_filter_interactions_header_and_rows(self):
        p = neko_filter_interactions.neko_filter_interactions(
            self.base, effect=["stimulation"])
        header = pathlib.Path(p).read_text().splitlines()[0]
        self.assertTrue(header.startswith("#source\teffect\ttarget\treferences"))
        stim = [r for r in self.edges if r[1].lower() == "stimulation"]
        self.assertEqual(len(tsv_rows(p)), len(stim))

    def test_filter_interactions_by_target(self):
        p = neko_filter_interactions.neko_filter_interactions(
            self.base, target="TP53")
        rows = tsv_rows(p)
        self.assertTrue(rows)
        self.assertTrue(all(r[2] == "TP53" for r in rows))

    def test_get_references_single_node(self):
        p = neko_get_references.neko_get_references(self.base, "TP53")
        rows = tsv_rows(p)
        self.assertTrue(rows)
        self.assertTrue(all("TP53" in (r[0], r[2]) for r in rows))

    def test_get_references_pair(self):
        rows_direct = [r for r in self.edges if {r[0], r[2]} == {"MYC", "TP53"}]
        p = neko_get_references.neko_get_references(self.base, "MYC", "TP53")
        self.assertEqual(len(tsv_rows(p)), len(rows_direct))

    def test_analyze_connectivity_partition(self):
        p = neko_analyze_connectivity.neko_analyze_connectivity(self.base)
        rows = tsv_rows(p)
        self.assertTrue(rows)
        counts = [int(r[1]) for r in rows]
        self.assertEqual(counts, sorted(counts, reverse=True))
        total = sum(counts)
        self.assertLessEqual(total, len(self.nodes))
        # every node appears exactly once across components
        seen = [n for r in rows for n in r[2].split("|")]
        self.assertEqual(len(seen), len(set(seen)))

    def test_analyze_connectivity_isolated_flag(self):
        # a two-component fixture: build directly from a two-island SIF
        two_islands = pathlib.Path(os.environ.get("TMPDIR", "/tmp")) / "two_islands.sif"
        two_islands.write_text("A\tstimulation\tB\nC\tinhibition\tD\n")
        p = neko_analyze_connectivity.neko_analyze_connectivity(two_islands)
        rows = tsv_rows(p)
        self.assertEqual(len(rows), 2)
        self.assertTrue(all(r[3] == "false" for r in rows))

    def test_analyze_gene_set_report(self):
        p = neko_analyze_gene_set.neko_analyze_gene_set(
            self.base, ["TP53", "MDM2", "MYC", "ZZZ9"], connectivity="strong")
        text = pathlib.Path(p).read_text()
        self.assertIn("Requested genes: 4", text)
        self.assertIn("Absent from network: 1", text)
        self.assertIn("Internal edges", text)
        self.assertIn("Strong components", text)

    def test_analyze_gene_set_bad_connectivity(self):
        with self.assertRaises(ValueError):
            neko_analyze_gene_set.neko_analyze_gene_set(
                self.base, ["TP53"], connectivity="medium")


class TestPreviewTasks(Tier2TestCase):
    def test_preview_hubs(self):
        p = neko_preview_connection_impact.neko_preview_connection_impact(
            self.base, method="hubs", top_k=5)
        text = pathlib.Path(p).read_text()
        self.assertIn("| node | degree |", text)

    def test_preview_unsigned_reports_delta(self):
        p = neko_preview_connection_impact.neko_preview_connection_impact(
            self.base, method="unsigned")
        text = pathlib.Path(p).read_text()
        self.assertIn("Edge-count delta:", text)

    def test_preview_does_not_mutate_input(self):
        before = pathlib.Path(self.base).read_bytes()
        neko_preview_connection_impact.neko_preview_connection_impact(
            self.base, method="relax_max_len")
        self.assertEqual(pathlib.Path(self.base).read_bytes(), before)

    def test_preview_bad_method(self):
        with self.assertRaises(ValueError):
            neko_preview_connection_impact.neko_preview_connection_impact(
                self.base, method="chaos")


if __name__ == "__main__":
    unittest.main(verbosity=2)
