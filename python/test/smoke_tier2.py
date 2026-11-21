"""Functional smoke for the nine Tier 2 NeKo tasks (direct invocation).

Run with the pymaboss python; SCOUT_JOB_FILES_DIR unset so the tempfile
fallback is exercised. Fixture: the Tier 1 chain artifact on 4 seeds.
"""
import os
import pathlib
import sys
import tempfile

TASKS = pathlib.Path(__file__).resolve().parents[1] / "tasks"
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


def tsv_head(path):
    text = pathlib.Path(path).read_text().splitlines()
    assert text[0].startswith("#"), f"{path}: missing # header"
    return [c for c in text[0][1:].split("\t")]


def main():
    os.environ.pop("SCOUT_JOB_FILES_DIR", None)
    results = []

    print("building fixture network (~15 s) ...", file=sys.stderr)
    base = neko_create_sif.neko_create_sif(["TP53", "MDM2", "MYC", "AKT1"],
                                           max_len=2, only_signed=False,
                                           consensus=False)
    n_edges = len(sif_rows(base))
    print(f"fixture: {base} ({n_edges} edges)", file=sys.stderr)
    assert n_edges >= 2, "fixture degenerate"

    p = neko_remove_undefined_interactions.neko_remove_undefined_interactions(base)
    assert pathlib.Path(p).exists() and sif_rows(p), "undefined removal empty"
    results.append(("neko_remove_undefined_interactions", p, "sif"))

    p = neko_complete_connection.neko_complete_connection(base, max_len=2)
    assert pathlib.Path(p).exists() and sif_rows(p), "complete_connection empty"
    results.append(("neko_complete_connection", p, "sif"))

    p = neko_connect_targeted_nodes.neko_connect_targeted_nodes(
        base, ["TP53", "MYC"], strategy="connect_subgroup")
    assert pathlib.Path(p).exists() and sif_rows(p), "connect_subgroup empty"
    results.append(("neko_connect_targeted_nodes", p, "sif"))

    p = neko_bridge_components.neko_bridge_components(
        base, ["TP53"], ["MYC"], max_len=2)
    assert pathlib.Path(p).exists() and sif_rows(p), "bridge empty"
    results.append(("neko_bridge_components", p, "sif"))

    p = neko_filter_interactions.neko_filter_interactions(
        base, effect=["stimulation"])
    assert tsv_head(p) == ["source", "effect", "target", "references"], "filter header"
    results.append(("neko_filter_interactions", p, "tsv"))

    p = neko_get_references.neko_get_references(base, "TP53")
    assert tsv_head(p) == ["source", "effect", "target", "references"], "refs header"
    results.append(("neko_get_references", p, "tsv"))

    p = neko_analyze_connectivity.neko_analyze_connectivity(base)
    assert tsv_head(p) == ["component_id", "node_count", "nodes", "isolated"], "conn header"
    results.append(("neko_analyze_connectivity", p, "tsv"))

    p = neko_analyze_gene_set.neko_analyze_gene_set(
        base, ["TP53", "MDM2", "MYC", "ZZZ9"], connectivity="strong")
    assert pathlib.Path(p).read_text().strip(), "gene set empty"
    results.append(("neko_analyze_gene_set", p, "md"))

    p = neko_preview_connection_impact.neko_preview_connection_impact(
        base, method="hubs", top_k=5)
    assert pathlib.Path(p).read_text().strip(), "preview hubs empty"
    results.append(("neko_preview_connection_impact(hubs)", p, "md"))

    sha_before = pathlib.Path(base).read_bytes()
    p = neko_preview_connection_impact.neko_preview_connection_impact(
        base, method="unsigned")
    assert pathlib.Path(base).read_bytes() == sha_before, "preview mutated input!"
    results.append(("neko_preview_connection_impact(unsigned)", p, "md"))

    print("\n== Tier 2 smoke: all %d checks passed ==" % len(results), file=sys.stderr)
    for name, path, kind in results:
        print(f"  {name:44s} {kind}  {path}", file=sys.stderr)


if __name__ == "__main__":
    main()
