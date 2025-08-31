# src/sindi/ast_rewriter.py
from __future__ import annotations
from typing import List, Optional, Tuple
from .parser import ASTNode

COMMUTATIVE_BOOL = {"&&", "||", "==", "!="}
ASSOCIATIVE = {"&&", "||", "+"}
COMMUTATIVE_ARITH = {"+", "*"}

REL_OPS = {">", ">=", "<", "<=", "==", "!="}


def _clone(n: ASTNode) -> ASTNode:
    return ASTNode(n.value, [_clone(c) for c in n.children])


def _repr(n: ASTNode) -> str:
    return repr(n)


def _eq(a: ASTNode, b: ASTNode) -> bool:
    return _repr(a) == _repr(b)


def _sort_children(node: ASTNode) -> None:
    node.children.sort(key=_repr)


def _is_bool_leaf(n: ASTNode) -> bool:
    return (not n.children) and (n.value.lower() in ("true", "false"))


def _is_zero(n: ASTNode) -> bool:
    if n.children:
        return False
    try:
        return int(n.value) == 0
    except Exception:
        try:
            return float(n.value) == 0.0
        except Exception:
            return False


def _is_number(n: ASTNode) -> bool:
    if n.children:
        return False
    try:
        int(n.value)
        return True
    except Exception:
        try:
            float(n.value)
            return True
        except Exception:
            return False


class ASTRewriter:
    """
    Post-parse AST canonicalizer.

    This pass works AFTER string-level rewriting + tokenization + parsing,
    so it has full structure. It focuses on:
      - Boolean-equality folding: (X == true) → X, (X == false) → !X, etc.
      - NOT cleanups: !!X → X
      - Simple algebraic normalization across inequalities:
            X < (Y - Z) -> (X + Z) < Y
            (A - B) < C -> A < (C + B)
      - Flattening associative ops (&&, ||, +)
      - Sorting commutative children (&&, ||, +, ==, !=) for determinism
      - Reordering equality arguments deterministically
      - Plus-commutativity/coalescing
      - A few semantic patterns (owner/admin convenience, bitmask-finalized)
    """

    # ---- convenience substitutions you previously had as strings ----
    # Keep these here as AST-level forms in case the surface pass didn't catch them.
    def _owner_admin_forms(self, n: ASTNode) -> ASTNode:
        # isOwner() -> (msg.sender == owner())
        if n.value == "isOwner()" and not n.children:
            return ASTNode("==", [ASTNode("msg.sender"), ASTNode("owner()")])

        # isAdmin() -> (msg.sender == admin)
        if n.value == "isAdmin()" and not n.children:
            return ASTNode("==", [ASTNode("msg.sender"), ASTNode("admin")])

        # _msgSender() -> msg.sender
        if n.value == "_msgSender()" and not n.children:
            return ASTNode("msg.sender")

        return n

    def _flatten(self, node: ASTNode) -> ASTNode:
        if not node.children:
            return node
        node.children = [self._flatten(c) for c in node.children]
        if node.value in ASSOCIATIVE:
            flat: List[ASTNode] = []
            for ch in node.children:
                if ch.value == node.value:
                    flat.extend(ch.children)
                else:
                    flat.append(ch)
            node.children = flat
        return node

    def _comm_sort(self, node: ASTNode) -> ASTNode:
        if not node.children:
            return node
        node.children = [self._comm_sort(c) for c in node.children]
        if node.value in (COMMUTATIVE_BOOL | COMMUTATIVE_ARITH):
            _sort_children(node)
        return node

    def _normalize_equals_to_bool(self, node: ASTNode) -> ASTNode:
        """
        X == true  -> X
        X == false -> !X
        X != true  -> !X
        X != false -> X
        (and symmetric forms where true/false is on left)
        """
        if not node.children:
            return node
        node.children = [self._normalize_equals_to_bool(c) for c in node.children]

        if node.value in ("==", "!=") and len(node.children) == 2:
            L, R = node.children

            # normalize: (expr op bool)
            if _is_bool_leaf(L) or _is_bool_leaf(R):
                expr = R if _is_bool_leaf(L) else L
                blf = L if _is_bool_leaf(L) else R
                bval = blf.value.lower() == "true"

                if node.value == "==":
                    return expr if bval else ASTNode("!", [expr])
                else:  # "!="
                    return ASTNode("!", [expr]) if bval else expr
        return node

    def _normalize_nots(self, node: ASTNode) -> ASTNode:
        if not node.children:
            return node
        node.children = [self._normalize_nots(c) for c in node.children]
        if node.value == "!" and len(node.children) == 1:
            ch = node.children[0]
            if ch.value == "!":
                return ch.children[0]
        return node

    def _normalize_rel_sub(self, node: ASTNode) -> ASTNode:
        """
        Move a single '-' across inequalities/equalities:
          X < Y - Z   →  X + Z < Y
          A - B < C   →  A < C + B
        Similar for <=, >, >=, ==, !=
        """
        if not node.children:
            return node
        node.children = [self._normalize_rel_sub(c) for c in node.children]

        if node.value in REL_OPS and len(node.children) == 2:
            L, R = node.children

            # Right = (A - B)  →  (L + B) op A
            if R.value == "-" and len(R.children) == 2:
                A, B = R.children
                return ASTNode(node.value, [ASTNode("+", [L, B]), A])

            # Left = (A - B)   →  A op (R + B)
            if L.value == "-" and len(L.children) == 2:
                A, B = L.children
                return ASTNode(node.value, [A, ASTNode("+", [R, B])])

        return node

    def _normalize_plus_comm(self, node: ASTNode) -> ASTNode:
        if not node.children:
            return node
        node.children = [self._normalize_plus_comm(c) for c in node.children]
        node = self._flatten(node)
        if node.value == "+":
            _sort_children(node)
        return node

    def _normalize_commutative_rel_args(self, node: ASTNode) -> ASTNode:
        """
        Reorder args for == and != deterministically: (smaller repr) first.
        """
        if not node.children:
            return node
        node.children = [self._normalize_commutative_rel_args(c) for c in node.children]
        if node.value in ("==", "!=") and len(node.children) == 2:
            L, R = node.children
            if _repr(R) < _repr(L):
                node.children = [R, L]
        return node

    def _finalized_bitmask(self, node: ASTNode) -> ASTNode:
        """
        (X & MarketplaceLib.FLAG_MASK_FINALIZED) == 0   →   !MarketplaceLib.isFinalized(X)
        Handle symmetry too: 0 == (X & FLAG)
        """
        if not node.children:
            return node
        node.children = [self._finalized_bitmask(c) for c in node.children]

        def _mk_is_finalized(x: ASTNode) -> ASTNode:
            return ASTNode("!", [ASTNode("MarketplaceLib.isFinalized()", [x])])

        if node.value == "==" and len(node.children) == 2:
            L, R = node.children

            # Left (& ...), Right 0
            if L.value == "&" and _is_zero(R) and len(L.children) == 2:
                a, b = L.children
                if (not b.children) and b.value == "MarketplaceLib.FLAG_MASK_FINALIZED":
                    return _mk_is_finalized(a)
                if (not a.children) and a.value == "MarketplaceLib.FLAG_MASK_FINALIZED":
                    return _mk_is_finalized(b)

            # Symmetric: Left 0, Right (& ...)
            if _is_zero(L) and R.value == "&" and len(R.children) == 2:
                a, b = R.children
                if (not b.children) and b.value == "MarketplaceLib.FLAG_MASK_FINALIZED":
                    return _mk_is_finalized(a)
                if (not a.children) and a.value == "MarketplaceLib.FLAG_MASK_FINALIZED":
                    return _mk_is_finalized(b)

        return node

    def _apply_local_node_rules(self, node: ASTNode) -> ASTNode:
        """
        Node-local translations that don't need a global traversal context.
        """
        node = self._owner_admin_forms(node)
        return node

    # -------- Pipeline --------
    def normalize(self, root: ASTNode) -> ASTNode:
        # Work on a clone to keep caller's tree untouched
        n = _clone(root)

        # Local substitutions on each node (single-visit)
        def _walk_apply(n: ASTNode) -> ASTNode:
            if not n.children:
                return self._apply_local_node_rules(n)
            n.children = [_walk_apply(c) for c in n.children]
            return self._apply_local_node_rules(n)

        n = _walk_apply(n)

        # Structured normalizations (multi-pass safe order)
        n = self._normalize_equals_to_bool(n)
        n = self._normalize_nots(n)
        n = self._normalize_rel_sub(n)
        n = self._flatten(n)
        n = self._normalize_plus_comm(n)
        n = self._comm_sort(n)
        n = self._normalize_commutative_rel_args(n)
        n = self._finalized_bitmask(n)

        return n