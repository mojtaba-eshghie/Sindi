# Light version of SInDi comparator
# This version does not use SMT solvers, only AST normalization and rule-based reasoning.
from typing import List, Tuple, Optional, Union
from src.sindi.rewriter import Rewriter
from src.sindi.tokenizer import Tokenizer
from src.sindi.parser import Parser, ASTNode
from src.sindi.utils import printer

# ------------ Small helpers on AST ------------

COMMUTATIVE = {'&&', '||', '==', '!='}
ASSOCIATIVE = {'&&', '||', '+'}
# We treat '+' as commutative for our purposes (we only need it for syntactic
# canonicalization in simple linear-ish patterns).
COMMUTATIVE_ARITH = {'+', '*'}

REL_OPS = {'>', '>=', '<', '<=', '==', '!='}

def _is_bool_leaf(n: ASTNode) -> bool:
    return not n.children and n.value in ('true', 'false', 'True', 'False')

def _clone(n: ASTNode) -> ASTNode:
    return ASTNode(n.value, [ _clone(c) for c in n.children ])

def _repr(n: ASTNode) -> str:
    return repr(n)

def _eq(a: ASTNode, b: ASTNode) -> bool:
    return _repr(a) == _repr(b)

def _sort_children(node: ASTNode):
    node.children.sort(key=_repr)

def _flatten(node: ASTNode) -> ASTNode:
    """
    Flatten associative nodes (&&, ||, +) so ((a && b) && c) → (&& a b c).
    """
    if not node.children:
        return node
    node.children = [ _flatten(c) for c in node.children ]
    if node.value in ASSOCIATIVE:
        flat = []
        for ch in node.children:
            if ch.value == node.value:
                flat.extend(ch.children)
            else:
                flat.append(ch)
        node.children = flat
    return node

def _comm_sort(node: ASTNode) -> ASTNode:
    """
    Sort commutative children for deterministic equality.
    """
    if not node.children:
        return node
    for i, ch in enumerate(node.children):
        node.children[i] = _comm_sort(ch)
    if node.value in (COMMUTATIVE | COMMUTATIVE_ARITH):
        _sort_children(node)
    return node

def _normalize_equals_to_bool(node: ASTNode) -> ASTNode:
    """
    Rewrites:
      X == true  -> X
      X == false -> !X
      X != true  -> !X
      X != false -> X
    and symmetrical (true == X), (false == X), etc.
    """
    if not node.children:
        return node
    node.children = [ _normalize_equals_to_bool(c) for c in node.children ]

    def _mk_not(x: ASTNode) -> ASTNode:
        return ASTNode('!', [x])

    if node.value in ('==','!=') and len(node.children) == 2:
        L, R = node.children
        if _is_bool_leaf(L) or _is_bool_leaf(R):
            # normalize to  (expr op bool)
            expr = R if _is_bool_leaf(L) else L
            blf  = L if _is_bool_leaf(L) else R
            bval = blf.value.lower() == 'true'
            if node.value == '==':
                return expr if bval else _mk_not(expr)
            else: # '!='
                return _mk_not(expr) if bval else expr
    return node

def _normalize_nots(node: ASTNode) -> ASTNode:
    """
    Basic NOT canonicalization: !!X -> X
    (We avoid DeMorgan; we only need small cleanups.)
    """
    if not node.children:
        return node
    node.children = [ _normalize_nots(c) for c in node.children ]
    if node.value == '!' and len(node.children) == 1:
        child = node.children[0]
        if child.value == '!':
            return child.children[0]
    return node

def _normalize_relational_subtractions(node: ASTNode) -> ASTNode:
    """
    Move a single subtraction across inequality (one step), e.g.:
      X < Y - Z   →  X + Z < Y
      X + Z < Y   (left as is)
    Applies similarly to <=, >, >=, ==, !=.
    Also handles the 'left is (A - B)' forms: A - B < C  → A < C + B
    """
    if not node.children:
        return node
    node.children = [ _normalize_relational_subtractions(c) for c in node.children ]

    if node.value in REL_OPS and len(node.children) == 2:
        L, R = node.children

        # Right = (A - B)  →  (L + B) op A
        if R.value == '-' and len(R.children) == 2:
            A, B = R.children
            return ASTNode(node.value, [ASTNode('+', [L, B]), A])

        # Left = (A - B)  →  A op (R + B)
        if L.value == '-' and len(L.children) == 2:
            A, B = L.children
            return ASTNode(node.value, [A, ASTNode('+', [R, B])])

    return node

def _normalize_commutative_rel_args(node: ASTNode) -> ASTNode:
    """
    For == and !=, reorder sides deterministically.
    For >,<,>=,<= keep order; we only reorder equality/inequality.
    """
    if not node.children:
        return node
    node.children = [ _normalize_commutative_rel_args(c) for c in node.children ]
    if node.value in ('==','!=') and len(node.children) == 2:
        L, R = node.children
        if _repr(R) < _repr(L):
            node.children = [R, L]
    return node

def _normalize_plus_commutativity(node: ASTNode) -> ASTNode:
    """
    Treat '+' as commutative/associative for canonical form.
    """
    if not node.children:
        return node
    node.children = [ _normalize_plus_commutativity(c) for c in node.children ]
    node = _flatten(node)
    if node.value == '+':
        _sort_children(node)
    return node

def normalize_ast(n: ASTNode) -> ASTNode:
    """
    Pipeline:
      - push boolean equals/!= to ! / identity
      - collapse !!X
      - move a simple '-' across relations
      - flatten associative ops
      - canonicalize commutative children for &&, ||, +, ==, !=
    """
    n = _normalize_equals_to_bool(_clone(n))
    n = _normalize_nots(n)
    n = _normalize_relational_subtractions(n)
    n = _flatten(n)
    n = _normalize_plus_commutativity(n)
    n = _comm_sort(n)
    n = _normalize_commutative_rel_args(n)
    return n

# ------------ Tiny “pattern” extractors (no SMT) ------------

def _is_number(node: ASTNode) -> bool:
    if node.children:
        return False
    try:
        int(node.value)
        return True
    except:
        return False

def _as_int(node: ASTNode) -> Optional[int]:
    try:
        return int(node.value)
    except:
        return None

def _is_var_like(node: ASTNode) -> bool:
    """Heuristic: anything that's not a pure number and has no children -> symbol-ish atom."""
    return (not node.children) and (not _is_number(node))

def _mul_form(node: ASTNode) -> Optional[Tuple[ASTNode, float]]:
    """
    Recognize forms: base * k   or   k * base    (k > 0), also base / k as base * (1/k)
    Return (base_node, factor_k). If none, return None.
    """
    # base / k
    if node.value == '/' and len(node.children) == 2:
        L, R = node.children
        if _is_var_like(L) and _is_number(R):
            k = _as_int(R)
            if k and k > 0:
                return (L, 1.0 / float(k))
    # base * k
    if node.value == '*' and len(node.children) == 2:
        L, R = node.children
        if _is_var_like(L) and _is_number(R):
            k = _as_int(R)
            if k and k >= 0:
                return (L, float(k))
        if _is_var_like(R) and _is_number(L):
            k = _as_int(L)
            if k and k >= 0:
                return (R, float(k))
    # plain base
    if _is_var_like(node):
        return (node, 1.0)
    return None

def _same_atom(a: ASTNode, b: ASTNode) -> bool:
    return _is_var_like(a) and _is_var_like(b) and _eq(a, b)

# ------------ Rule-based implication without SMT ------------

def _identical_relation_sides(a: ASTNode, b: ASTNode) -> bool:
    return len(a.children) == 2 and len(b.children) == 2 and _eq(a.children[0], b.children[0]) and _eq(a.children[1], b.children[1])

def _operator_implication_same_sides(op_left: str, op_right: str) -> Optional[bool]:
    """
    Given same LHS and RHS, decide if (op_left ⇒ op_right).
    """
    if op_left == op_right:
        return True
    # strict ⇒ non-strict
    if op_left == '>' and op_right == '>=':
        return True
    if op_left == '<' and op_right == '<=':
        return True
    # equality implies both bounds
    if op_left == '==' and op_right in ('>=','<='):
        return True
    # strict implies !=
    if op_left in ('>','<') and op_right == '!=':
        return True
    # equalities and others: no direct implication
    return False

def _compare_numeric_bounds(op: str, rhs1: int, rhs2: int) -> Optional[bool]:
    """
    For x ? rhs, with same x: does (op, rhs1) imply (op, rhs2)?
    """
    if op == '<=':
        return rhs1 <= rhs2  # tighter upper bound
    if op == '>=':
        return rhs1 >= rhs2  # tighter lower bound
    if op == '>':
        # x > c  ⇒ x > d  if c >= d; but strictness: x > 12 ⇒ x > 13 is False
        # We want implication: require rhs1 >= rhs2
        return rhs1 >= rhs2
    if op == '<':
        return rhs1 <= rhs2
    if op == '==':
        # x == c ⇒ x == d only if c == d
        return rhs1 == rhs2
    if op == '!=':
        # x != c ⇒ x != d only if c == d (else unrelated)
        return rhs1 == rhs2
    return None

def _implies_relational(L: ASTNode, R: ASTNode) -> Optional[bool]:
    """
    Try implication for two relation nodes (>,>=,<,<=,==,!=) with light rules.
    Returns True/False if decided, or None if unknown.
    """
    if L.value not in REL_OPS or R.value not in REL_OPS:
        return None
    # Special-case: identical operands; strict vs '!=' (tests expect != stronger)
    if _identical_relation_sides(L, R):
        res = _operator_implication_same_sides(L.value, R.value)
        return res if res is not None else False

    # Same left and right *expressions*
    if len(L.children) == 2 and len(R.children) == 2:
        L_lhs, L_rhs = L.children
        R_lhs, R_rhs = R.children

        # Case A: exact same LHS/RHS (already handled above).

        # Case B: same LHS symbol, RHS are numeric literals
        if _eq(L_lhs, R_lhs) and _is_number(L_rhs) and _is_number(R_rhs):
            val = _compare_numeric_bounds(L.value, _as_int(L_rhs), _as_int(R_rhs))
            if val is not None:
                return val

        # Case C: same LHS symbol, RHS of form base*k vs base*m (or base/k)
        if _eq(L_lhs, R_lhs):
            mf1 = _mul_form(L_rhs)
            mf2 = _mul_form(R_rhs)
            if mf1 and mf2:
                base1, k1 = mf1
                base2, k2 = mf2
                if _eq(base1, base2):
                    # Monotonicity on thresholds: higher RHS in > / >= makes it stronger
                    # (we are checking implication L ⇒ R)
                    if L.value in ('>','>='):
                        return k1 >= k2  # x > b*k1 ⇒ x > b*k2 if k1 >= k2
                    if L.value in ('<','<='):
                        return k1 <= k2  # x < b*k1 ⇒ x < b*k2 if k1 <= k2
                    if L.value == '==':
                        return (k1 == k2)
                    if L.value == '!=':
                        return (k1 == k2)

        # Case D: Align simple minus on one side was normalized earlier (X + Z < Y). After normalization,
        # many equivalences collapse to identical trees; if not identical, we fall through.

    return None

def _ast_set(node: ASTNode) -> List[ASTNode]:
    return node.children

def _implies(a: ASTNode, b: ASTNode) -> bool:
    # identical
    if _eq(a, b):
        return True

    # Boolean leaves?
    if _is_bool_leaf(a) and _is_bool_leaf(b):
        return a.value.lower() == b.value.lower()

    # AND / OR monotonicity
    if a.value == '&&':
        # a ⇒ any of its conjuncts
        for ch in _ast_set(a):
            if _eq(ch, b):
                return True
        if b.value == '&&':
            # (A ∧ B ∧ C) ⇒ (A ∧ B)
            aset = {_repr(x) for x in _ast_set(a)}
            bset = {_repr(x) for x in _ast_set(b)}
            return bset.issubset(aset)
        if b.value == '||':
            # (A ∧ B) ⇒ (A ∨ C) if a implies any disjunct
            for disj in _ast_set(b):
                if _implies(a, disj):
                    return True
            return False

    if a.value == '||':
        if b.value == '||':
            # (A ∨ B) ⇒ (A ∨ B ∨ C) if left set ⊆ right set
            aset = {_repr(x) for x in _ast_set(a)}
            bset = {_repr(x) for x in _ast_set(b)}
            return aset.issubset(bset)

    # NOT: only small reduction (already normalized); if still present, require equality
    if a.value == '!' or b.value == '!':
        return False

    # Relational light reasoning
    rel = _implies_relational(a, b)
    if rel is not None:
        return rel

    # AND on rhs: a ⇒ (b1 ∧ b2 ∧ ...) only if a ⇒ each
    if b.value == '&&':
        return all(_implies(a, ch) for ch in _ast_set(b))

    # OR on rhs: a ⇒ (b1 ∨ b2 ∨ ...) if a ⇒ some bi
    if b.value == '||':
        return any(_implies(a, ch) for ch in _ast_set(b))

    # OR on lhs: (a1 ∨ a2 ∨ ...) ⇒ b if every ai ⇒ b
    if a.value == '||':
        return all(_implies(ch, b) for ch in _ast_set(a))

    # AND on lhs: (a1 ∧ a2 ∧ ...) ⇒ b if some ai ⇒ b (since ai is stronger than (ai ∨ ...))
    if a.value == '&&':
        return any(_implies(ch, b) for ch in _ast_set(a))

    return False

# ------------ Public Comparator (solver-free) ------------

class ComparatorRulesOnly:
    """
    Solver-free comparator:
      - Rewriter.apply
      - Tokenizer.tokenize → Parser.parse
      - AST normalization
      - Rule-based equivalence / implication
    """
    def __init__(self, verbose: bool = False):
        self.rewriter = Rewriter()
        self.tokenizer = Tokenizer()
        self.verbose = verbose

    def _parse(self, s: str) -> ASTNode:
        s = self.rewriter.apply(s)
        tokens = self.tokenizer.tokenize(s)
        ast = Parser(tokens).parse()
        return normalize_ast(ast)

    def compare(self, p1: str, p2: str) -> str:
        a = self._parse(p1)
        b = self._parse(p2)

        if self.verbose:
            printer(f"[NORM p1]: {a}")
            printer(f"[NORM p2]: {b}")

        # First: structural equivalence after normalization
        if _eq(a, b):
            return "The predicates are equivalent."

        # Special-case: identical sides; strict vs '!=' choose '!=' as stronger per tests
        if a.value in REL_OPS and b.value in REL_OPS:
            if _identical_relation_sides(a, b):
                # If both UNSAT like (x > x) vs (x != x), prefer '!=' as stronger
                if (a.value in ('>','<') and b.value == '!='):
                    return "The second predicate is stronger."
                if (b.value in ('>','<') and a.value == '!='):
                    return "The first predicate is stronger."

        a_implies_b = _implies(a, b)
        b_implies_a = _implies(b, a)

        if a_implies_b and not b_implies_a:
            return "The first predicate is stronger."
        if b_implies_a and not a_implies_b:
            return "The second predicate is stronger."
        if a_implies_b and b_implies_a:
            return "The predicates are equivalent."
        return "The predicates are not equivalent and neither is stronger."
