# Δ Sindi: Semantic Invariant Differencing for Solidity Smart Contracts

SInDi compares two **Solidity boolean predicates** (e.g., `require` guards) and decides whether they are **equivalent**, or **one is stronger**.

- **Docs & source:** GitHub → https://github.com/mojtaba-eshghie/SInDi  
- **Author:** https://eshghie.com/

## Install

```bash
pip install sindi
````

## Quick usage

### Library

```python
from sindi import Comparator, ComparatorRulesOnly

cmp = Comparator()
print(cmp.compare("a > b", "a >= b"))
# "The first predicate is stronger."

light = ComparatorRulesOnly()
print(light.compare("a > b * 2", "a > b"))
# "The first predicate is stronger."
```

### CLI

```bash
# Compare (full)
sindi compare "msg.sender == msg.origin && a >= b" "msg.sender == msg.origin"

# Light comparator (no SMT)
sindi compare "a > b * 2" "a > b" --light

# Rewrite / tokenize / parse / simplify
sindi rewrite "isOwner() && now >= 0"
sindi tokenize "..." --json
sindi parse "..." --tree
sindi simplify "..." --show-sympy --json
```

## API (tiny)

* `Comparator().compare(p1: str, p2: str) -> str`
  Full semantic differencing (SymPy + selective Z3 where needed).

* `ComparatorRulesOnly().compare(p1: str, p2: str) -> str`
  Lightweight, **solver-free** structural/rewrites reasoning.

---

*Notes:* Functions & arrays are treated as uninterpreted symbols for reasoning. Division is modeled as `a * b**-1`. Variables are assumed non-negative in SMT checks.