import json
import os
import sys
import subprocess
from pathlib import Path
import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
MAIN = REPO_ROOT / "main.py"
ENV = dict(os.environ)
ENV["PYTHONPATH"] = "src:."

# Skip the whole module if light comparator isn't present
RULES_ONLY_IMPL = (REPO_ROOT / "src" / "sindi" / "comparator_light.py")
pytestmark = pytest.mark.skipif(
    not RULES_ONLY_IMPL.exists(),
    reason="light comparator not present (src/sindi/comparator_light.py missing)",
)

def run_cli(*args, check=True):
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


@pytest.mark.parametrize(
    "p1,p2,expected",
    [
        ("a > b", "a >= b", "The first predicate is stronger."),
        ("(a + 1) < b", "(a + 1) <= b", "The first predicate is stronger."),
        ("used[salt] == false", "!used[salt]", "The predicates are equivalent."),
        ("balanceOf(to) <= holdLimitAmount - amount", "balanceOf(to) + amount <= holdLimitAmount",
         "The predicates are equivalent."),
        ("a > b * 2", "a > b * 1", "The first predicate is stronger."),
        ("a > b / 2", "a > b", "The second predicate is stronger."),
        ("isOwner()", "msg.sender == owner()", "The predicates are equivalent."),
    ],
)
def test_cli_compare_rules_only(p1, p2, expected):
    rc, out, _ = run_cli("compare", p1, p2, "--light")
    assert rc == 0
    assert out.strip() == expected
