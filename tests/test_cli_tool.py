import json
import os
import sys
import subprocess
from pathlib import Path
import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
MAIN = REPO_ROOT / "main.py"
ENV = dict(os.environ)
# Ensure in-subprocess imports like "from src.sindi..." work the same as CI
ENV["PYTHONPATH"] = "src:."

def run_cli(*args, check=True):
    """Run the CLI and return (returncode, stdout, stderr)."""
    proc = subprocess.run(
        [sys.executable, str(MAIN), *args],
        cwd=str(REPO_ROOT),
        env=ENV,
        text=True,
        capture_output=True,
    )
    if check and proc.returncode != 0:
        raise AssertionError(f"CLI failed: {' '.join(args)}\nstdout:\n{proc.stdout}\nstderr:\n{proc.stderr}")
    return proc.returncode, proc.stdout, proc.stderr


# ------------------------
# rewrite
# ------------------------
def test_cli_rewrite_now_to_block_timestamp():
    rc, out, _ = run_cli("rewrite", "now >= 0 && a > b")
    assert rc == 0
    assert out.strip() == "block.timestamp >= 0 && a > b"


# ------------------------
# tokenize
# ------------------------
def test_cli_tokenize_json_after_rewrite():
    # We rely on existing tokenizer behavior; we only assert key tags appear.
    rc, out, _ = run_cli("tokenize", "now >= 0 && a > b", "--json")
    toks = json.loads(out)
    tags = [t["tag"] for t in toks]
    vals = [t["value"] for t in toks]
    # After rewrite, "now" becomes "block.timestamp"
    assert "GREATER_EQUAL" in tags
    assert "AND" in tags
    assert "block" in vals or "block.timestamp" in vals  # parser splits on DOT


# ------------------------
# parse
# ------------------------
def test_cli_parse_json_tree_with_rewrites():
    # Based on rewriter smoke: isOwner() -> msg.sender == owner()
    rc, out, _ = run_cli("parse", "isOwner() && x > 0", "--json")
    ast = json.loads(out)
    assert ast["value"] == "&&"
    # children contain an equality and a '>'
    child_vals = {c["value"] for c in ast["children"]}
    assert "==" in child_vals
    assert ">" in child_vals
    # Ensure owner() shows up on the equality side
    eq_nodes = [c for c in ast["children"] if c["value"] == "=="]
    assert eq_nodes, "Expected an equality node after rewrite"
    eq_leaf_vals = []
    def _collect(n):
        eq_leaf_vals.append(n["value"])
        for ch in n.get("children", []):
            _collect(ch)
    _collect(eq_nodes[0])
    assert "owner()" in eq_leaf_vals


# ------------------------
# simplify (SymPy-backed)
# ------------------------
def test_cli_simplify_returns_expected_symbols_json():
    # Mirrors tests/test_simplifier.py but via CLI
    rc, out, _ = run_cli("simplify", "msg.sender == msg.origin", "--json", "--show-sympy")
    data = json.loads(out)
    simp = data["simplified_ast"]
    assert simp["value"] == "=="
    leafs = []
    def _walk(n):
        if not n.get("children"):
            leafs.append(n["value"])
        for ch in n.get("children", []):
            _walk(ch)
    _walk(simp)
    # Simplifier maps msg.sender -> msg_sender, msg.origin -> msg_origin
    assert "msg_sender" in leafs
    assert "msg_origin" in leafs


# ------------------------
# compare (full comparator)
# ------------------------
@pytest.mark.parametrize(
    "p1,p2,expected",
    [
        ("a > b", "a >= b", "The first predicate is stronger."),
        ("msg.sender == msg.origin", "msg.origin == msg.sender", "The predicates are equivalent."),
        ("a > b", "a < b", "The predicates are not equivalent and neither is stronger."),
    ],
)
def test_cli_compare_full(p1, p2, expected):
    rc, out, _ = run_cli("compare", p1, p2)
    assert rc == 0
    assert out.strip() == expected


def test_cli_compare_from_files(tmp_path: Path):
    p1 = tmp_path / "p1.txt"
    p2 = tmp_path / "p2.txt"
    p1.write_text("a + 1 <= b")
    p2.write_text("a + 1 < b")
    rc, out, _ = run_cli("compare", str(p1), str(p2), "--p1-file", "--p2-file")
    assert rc == 0
    assert out.strip() == "The second predicate is stronger."


def test_cli_compare_verbose_json_payload():
    rc, out, _ = run_cli("compare", "isOwner()", "msg.sender == owner()", "--json")
    data = json.loads(out)
    assert data["verdict"] == "The predicates are equivalent."
    assert "rewritten" in data and "ast" in data
    assert "p1" in data["rewritten"] and "p2" in data["rewritten"]
