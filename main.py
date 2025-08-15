#!/usr/bin/env python3
"""
SInDi CLI: run rewrite, tokenize, parse, simplify, and compare.

Examples:
  # Rewrite only
  python main.py rewrite "isOwner() && msg.value >= 1 ether"

  # Tokenize (after rewrite)
  python main.py tokenize "now >= 0 && _msgSender() != address(0)"

  # Parse (pretty tree)
  python main.py parse "balanceOf(to)+amount<=holdLimitAmount" --tree

  # Simplify (SymPy-based path) and show SymPy form
  python main.py simplify "a - 1 < b" --show-sympy

  # Compare using solver-free rules
  python main.py compare "a > b * 2" "a > b * 1" --rules-only

  # Compare using full comparator (SymPy/Z3)
  python main.py compare "msg.sender == msg.origin && a >= b" "msg.sender == msg.origin"

  # Read predicates from files
  python main.py compare p1.txt p2.txt --p1-file --p2-file --rules-only
"""
import argparse
import json
import sys
from typing import Any, Dict

# Core building blocks
from src.sindi.rewriter import Rewriter
from src.sindi.tokenizer import Tokenizer
from src.sindi.parser import Parser, ASTNode
from src.sindi.simplifier import Simplifier
from src.sindi.comparator import Comparator  # full (SymPy/Z3) comparator
from src.sindi.comparator_light import ComparatorRulesOnly # light (rules-only) comparator


# ---------- small helpers ----------
def read_predicate(value: str, is_file: bool) -> str:
    if not is_file:
        return value
    with open(value, "r", encoding="utf-8") as f:
        return f.read().strip()

def ast_to_dict(n: ASTNode) -> Dict[str, Any]:
    return {"value": n.value, "children": [ast_to_dict(c) for c in n.children]}

def print_tree(n: ASTNode, indent: int = 0) -> None:
    pad = "  " * indent
    print(f"{pad}{n.value}")
    for c in n.children:
        print_tree(c, indent + 1)


# ---------- subcommand actions ----------
def cmd_rewrite(args: argparse.Namespace) -> int:
    rw = Rewriter()
    s = read_predicate(args.predicate, args.from_file)
    print(rw.apply(s))
    return 0

def cmd_tokenize(args: argparse.Namespace) -> int:
    rw = Rewriter()
    tk = Tokenizer()
    s = read_predicate(args.predicate, args.from_file)
    if not args.skip_rewrite:
        s = rw.apply(s)
    tokens = tk.tokenize(s)
    if args.json:
        print(json.dumps([{"value": v, "tag": t} for (v, t) in tokens], ensure_ascii=False))
    else:
        print(tokens)
    return 0

def cmd_parse(args: argparse.Namespace) -> int:
    rw = Rewriter()
    tk = Tokenizer()
    s = read_predicate(args.predicate, args.from_file)
    if not args.skip_rewrite:
        s = rw.apply(s)
    tokens = tk.tokenize(s)
    ast = Parser(tokens).parse()
    if args.tree:
        print_tree(ast)
    elif args.json:
        print(json.dumps(ast_to_dict(ast), ensure_ascii=False))
    else:
        print(ast)  # repr
    return 0

def cmd_simplify(args: argparse.Namespace) -> int:
    rw = Rewriter()
    tk = Tokenizer()
    sp = Simplifier()
    s = read_predicate(args.predicate, args.from_file)
    if not args.skip_rewrite:
        s = rw.apply(s)
    tokens = tk.tokenize(s)
    ast = Parser(tokens).parse()
    simplified = sp.simplify(ast)

    out: Dict[str, Any] = {}
    out["simplified_ast"] = ast_to_dict(simplified)

    if args.show_sympy:
        # Access internal converter for debugging output
        try:
            sym = sp._to_sympy(ast)  # type: ignore[attr-defined]
            out["sympy_expr_original"] = str(sym)
        except Exception as e:
            out["sympy_expr_original_error"] = str(e)

        try:
            sym_s = sp._to_sympy(simplified)  # type: ignore[attr-defined]
            out["sympy_expr_simplified"] = str(sym_s)
        except Exception as e:
            out["sympy_expr_simplified_error"] = str(e)

    if args.json:
        print(json.dumps(out, ensure_ascii=False))
    else:
        if args.show_sympy:
            if "sympy_expr_original" in out:
                print("SymPy (original):", out["sympy_expr_original"])
            if "sympy_expr_simplified" in out:
                print("SymPy (simplified):", out["sympy_expr_simplified"])
        print("Simplified AST:")
        print_tree(simplified)
    return 0

def cmd_compare(args: argparse.Namespace) -> int:
    rw = Rewriter()
    tk = Tokenizer()

    p1 = read_predicate(args.predicate1, args.p1_file)
    p2 = read_predicate(args.predicate2, args.p2_file)

    # Choose comparator
    if args.rules_only:
        if ComparatorRulesOnly is None:
            print("Error: rules-only comparator not available. Make sure src/sindi/comparator_rules.py exists.",
                  file=sys.stderr)
            return 2
        cmp = ComparatorRulesOnly(verbose=args.verbose)
    else:
        cmp = Comparator()

    verdict = cmp.compare(p1, p2)

    if not args.verbose and not args.json:
        print(verdict)
        return 0

    # For verbose/json, also emit normalized/rewritten forms and ASTs
    out: Dict[str, Any] = {"verdict": verdict}

    # Rewritten forms for visibility
    rp1 = rw.apply(p1)
    rp2 = rw.apply(p2)
    out["rewritten"] = {"p1": rp1, "p2": rp2}

    # Tokenize + parse for AST dumps (normalized form depends on comparator; here we show parser output)
    ast1 = Parser(tk.tokenize(rp1)).parse()
    ast2 = Parser(tk.tokenize(rp2)).parse()
    out["ast"] = {"p1": ast_to_dict(ast1), "p2": ast_to_dict(ast2)}

    if args.json:
        print(json.dumps(out, ensure_ascii=False))
    else:
        print("Verdict:", verdict)
        print("\n[Rewritten]\n p1:", rp1, "\n p2:", rp2)
        print("\n[AST p1]")
        print_tree(ast1)
        print("\n[AST p2]")
        print_tree(ast2)
    return 0


# ---------- CLI wiring ----------
def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="sindi",
        description="SInDi CLI: rewrite, tokenize, parse, simplify, and compare Solidity predicates."
    )
    sub = p.add_subparsers(dest="cmd", required=True)

    # rewrite
    pr = sub.add_parser("rewrite", help="Apply rewrite rules and print the result.")
    pr.add_argument("predicate", help="Predicate string or a path with --from-file.")
    pr.add_argument("--from-file", action="store_true", help="Treat predicate as a file path.")
    pr.set_defaults(func=cmd_rewrite)

    # tokenize
    pt = sub.add_parser("tokenize", help="Tokenize (optionally after rewrite).")
    pt.add_argument("predicate", help="Predicate string or a path with --from-file.")
    pt.add_argument("--from-file", action="store_true", help="Treat predicate as a file path.")
    pt.add_argument("--skip-rewrite", action="store_true", help="Tokenize without applying rewriter.")
    pt.add_argument("--json", action="store_true", help="Emit JSON.")
    pt.set_defaults(func=cmd_tokenize)

    # parse
    pp = sub.add_parser("parse", help="Parse into AST (optionally after rewrite).")
    pp.add_argument("predicate", help="Predicate string or a path with --from-file.")
    pp.add_argument("--from-file", action="store_true", help="Treat predicate as a file path.")
    pp.add_argument("--skip-rewrite", action="store_true", help="Parse without applying rewriter.")
    pp.add_argument("--tree", action="store_true", help="Pretty-print the AST tree.")
    pp.add_argument("--json", action="store_true", help="Emit JSON.")
    pp.set_defaults(func=cmd_parse)

    # simplify
    ps = sub.add_parser("simplify", help="Simplify AST (SymPy-based).")
    ps.add_argument("predicate", help="Predicate string or a path with --from-file.")
    ps.add_argument("--from-file", action="store_true", help="Treat predicate as a file path.")
    ps.add_argument("--skip-rewrite", action="store_true", help="Simplify without applying rewriter.")
    ps.add_argument("--show-sympy", action="store_true", help="Also show SymPy expressions.")
    ps.add_argument("--json", action="store_true", help="Emit JSON.")
    ps.set_defaults(func=cmd_simplify)

    # compare
    pc = sub.add_parser("compare", help="Compare two predicates and print verdict.")
    pc.add_argument("predicate1", help="First predicate or a path with --p1-file.")
    pc.add_argument("predicate2", help="Second predicate or a path with --p2-file.")
    pc.add_argument("--p1-file", action="store_true", help="Treat predicate1 as a file path.")
    pc.add_argument("--p2-file", action="store_true", help="Treat predicate2 as a file path.")
    pc.add_argument("--rules-only", action="store_true",
                    help="Use solver-free ComparatorRulesOnly (if available).")
    pc.add_argument("--verbose", action="store_true",
                    help="Show rewritten predicates and ASTs.")
    pc.add_argument("--json", action="store_true", help="Emit JSON (includes rewritten and ASTs).")
    pc.set_defaults(func=cmd_compare)

    return p


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    try:
        return args.func(args)
    except KeyboardInterrupt:
        print("Interrupted.", file=sys.stderr)
        return 130
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
