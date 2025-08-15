# Δ SInDi — Semantic Invariant Differencing for Solidity Smart Contracts

SInDi compares two Solidity boolean predicates (e.g., the guards in `require`/`assert`) and decides whether they are **equivalent**, **one is stronger**, or **unrelated**. It’s designed to survive real-world Solidity syntax variations across versions and frameworks (e.g., OpenZeppelin patterns) by normalizing source, tokenizing, parsing to an AST, and reasoning over the structure.

---

## Why SInDi?

* **Contract evolution:** When you refactor or upgrade a contract (proxy patterns, library changes, Solidity version bumps), the *same* invariant often appears in a different syntactic form. SInDi checks whether behavior is preserved.
* **Invariant denoising:** Auto-mined invariants can be redundant or weak. SInDi helps find equivalences and strength relationships to keep only the strongest set.
* **Fast iteration:** A rich **CLI** lets you run individual stages (rewrite → tokenize → parse → simplify → compare), so you can see what SInDi “understands” at each step.

---

## What it does

* **Rewrite & Normalize (cross-version)**
  Canonicalizes common Solidity constructs before parsing. Examples:

  * `now` → `block.timestamp`
  * `_msgSender()` → `msg.sender`
  * `isOwner()` → `msg.sender == owner()`
  * Zero address hex → `address(0)`
  * Ether/gwei units → raw wei integer
  * `SafeMath.add(x,y)` / `a.add(b)` → `(x) + (y)`
  * `type(IERC721).interfaceId` ↔ the equivalent hex ID

* **Tokenize → Parse (AST)**
  Converts the normalized predicate into an AST that captures expressions, calls, indexing, logical/relational ops, etc.

* **Simplify (symbolic)**
  Converts to SymPy expressions and simplifies (with careful mappings for Solidity-like expressions).

* **Compare (semantic differencing)**
  Checks implication relationships and returns one of:

  * `The predicates are equivalent.`
  * `The first predicate is stronger.`
  * `The second predicate is stronger.`
  * `The predicates are not equivalent and neither is stronger.`

> By default, the comparator uses symbolic reasoning with selective SMT (Z3) for tricky numeric/logical cases. You can also plug in a **light** comparator (no SMT) as an optional module (details below).

---

## Installation

### From PyPI

```bash
pip install sindi
```

### From source (this repo)

```bash
# Clone, then in repo root:
python -m pip install -r requirements.txt
# Optional: editable install
python -m pip install -e .
```

**Requirements:** Python 3.8+
We pin SymPy in `requirements.txt`. The full comparator uses `z3-solver` (already listed).

---

## Quick start (CLI)

The new CLI is exposed by `main.py` with subcommands:

```
sindi rewrite   <predicate> [--from-file]
sindi tokenize  <predicate> [--from-file] [--skip-rewrite] [--json]
sindi parse     <predicate> [--from-file] [--skip-rewrite] [--tree|--json]
sindi simplify  <predicate> [--from-file] [--skip-rewrite] [--show-sympy] [--json]
sindi compare   <p1> <p2> [--p1-file] [--p2-file] [--light] [--verbose|--json] [--debug-logs]
```

Run via Python:

```bash
python main.py rewrite "isOwner() && msg.value >= 1 ether"
# => msg.sender == owner() && msg.value >= 1000000000000000000
```

**Tokenize:**

```bash
python main.py tokenize "now >= 0 && _msgSender() != address(0)" --json
```

**Parse (pretty tree):**

```bash
python main.py parse "balanceOf(to)+amount<=holdLimitAmount" --tree
```

**Simplify (show SymPy expressions):**

```bash
python main.py simplify "a - 1 < b" --show-sympy
```

**Compare (full comparator):**

```bash
python main.py compare "msg.sender == msg.origin && a >= b" "msg.sender == msg.origin"
# -> The first predicate is stronger.
```

**Compare (light, solver-free)**

```bash
python main.py compare "a > b * 2" "a > b * 1" --light
```

**Verbose/JSON output:**

```bash
python main.py compare "isOwner()" "msg.sender == owner()" --json
# Prints verdict + rewritten forms + ASTs as JSON
```

### Logging

By default, the CLI silences internal debug prints.
Enable logs with:

* `--debug-logs` (per-command), or
* `SINDI_QUIET=0` (environment variable)

---

## Python API

If you installed from PyPI:

```python
from sindi.comparator import Comparator

cmp = Comparator()
print(cmp.compare("a < b", "a <= b"))
# The first predicate is stronger.
```

From source (without installing the package), set your `PYTHONPATH` or use relative imports:

```bash
PYTHONPATH=src:. python -c 'from src.sindi.comparator import Comparator; \
print(Comparator().compare("a > b", "a < b"))'
# The predicates are not equivalent and neither is stronger.
```

You can also use building blocks:

```python
from sindi.rewriter import Rewriter
from sindi.tokenizer import Tokenizer
from sindi.parser import Parser
from sindi.simplifier import Simplifier

rw, tk, sp = Rewriter(), Tokenizer(), Simplifier()

s = rw.apply("SafeMath.add(a,b) > c")
tokens = tk.tokenize(s)
ast = Parser(tokens).parse()
simplified_ast = sp.simplify(ast)
```

---

## The pipeline (architecture at a glance)

1. **Rewriting / Normalization** (string → string)
   Fixes cross-version and library-specific surface differences.

2. **Tokenization & Parsing** (string → tokens → AST)
   Produces a structured AST (`ASTNode`) for logical/relational/arithmetic forms, calls, indexing, etc.

3. **Simplification** (AST → SymPy → simplified AST)
   Uses symbolic math to normalize and simplify expressions (e.g., `a - b` modeled as `a + (-1*b)`).

4. **Comparison** (AST/SymPy → verdict)

   * Symbolic checks + satisfiability where needed (Z3).
   * Verdict reflects implication relationships between predicates.

---

## Light Comparator (solver-free)

A lightweight comparator (no Z3, purely structural/rewrites/AST reasoning) can be provided at:

```
src/sindi/comparator_rules.py
```

If present, the CLI gains `--light`. Some **light** tests (`tests/test_cli_light.py`) will run only if this file exists; otherwise they are skipped. The **full** test suite does not require it.

---

## Testing

We use `pytest`. To run everything:

```bash
PYTHONPATH=src:. pytest -q
```

Typical subsets:

```bash
# Core comparator test corpus
PYTHONPATH=src:. pytest -q tests/test_comparator.py

# CLI tests (full comparator)
PYTHONPATH=src:. pytest -q tests/test_cli_tool.py

# CLI "light" tests (run only if light comparator exists)
PYTHONPATH=src:. pytest -q tests/test_cli_light.py
```

> The CI (GitHub Actions) runs a targeted subset by default; switch it to `pytest -q` to run all tests.

---

## Examples of rewrites

| Input                             | Rewritten / Canonical   |
| --------------------------------- | ----------------------- |
| `now`                             | `block.timestamp`       |
| `_msgSender()`                    | `msg.sender`            |
| `isOwner()`                       | `msg.sender == owner()` |
| `0x0000…0000` (40 zeros)          | `address(0)`            |
| `1 ether` / `5 gwei` / `100 wei`  | raw wei integer         |
| `SafeMath.add(a,b)` / `a.add(b)`  | `(a) + (b)`             |
| `type(IERC721).interfaceId` ↔ hex | normalized `type(...)`  |

---

## Notes & limitations

* **Numerics / domains:** For SMT checks, variables are assumed non-negative (Solidity-like domains).
* **Division:** We model `a / b` as `a * (b ** -1)` in symbolic form (not integer division).
* **Functions & arrays:** Uninterpreted in reasoning unless specialized; treated as symbols or function terms.
* **Scope:** Focused on boolean predicates used in `require`/`assert`—not full contract semantics.
* **Logging:** All internal debug goes through `sindi.utils.printer`. Set `SINDI_QUIET=1` to suppress globally.

---

## Contributing

Issues and PRs are welcome. If you add rewrite rules or parser coverage, please include targeted tests. For large features:

1. Open an issue with the proposed change and rationale.
2. Keep PRs focused and tested.
3. Ensure the CLI remains tidy (no debug logs leaking to stdout).

---

## Citation (paper & code)

If you use Sindi in academic work, please cite the **Sindi** paper (upcoming) and this repository.

* Tool: `https://github.com/mojtaba-eshghie/SInDi`
* PyPI: `https://pypi.org/project/sindi/`
