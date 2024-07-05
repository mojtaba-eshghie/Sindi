# solidity_predicate_comparison/src/comparator.py

import sympy as sp
from src.tokenizer import Tokenizer
from src.parser import Parser
from src.simplifier import Simplifier
from src.parser import ASTNode

class Comparator:
    def __init__(self):
        self.tokenizer = Tokenizer()
        self.simplifier = Simplifier()

    def compare(self, predicate1: str, predicate2: str) -> str:
        # Tokenize, parse, and simplify the first predicate
        tokens1 = self.tokenizer.tokenize(predicate1)
        print(f"Tokens1: {tokens1}")
        parser1 = Parser(tokens1)
        ast1 = parser1.parse()
        print(f"Parsed AST1: {ast1}")
        simplified_ast1 = self.simplifier.simplify(ast1)
        print(f"Simplified AST1: {simplified_ast1}")

        # Tokenize, parse, and simplify the second predicate
        tokens2 = self.tokenizer.tokenize(predicate2)
        print(f"Tokens2: {tokens2}")
        parser2 = Parser(tokens2)
        ast2 = parser2.parse()
        print(f"Parsed AST2: {ast2}")
        simplified_ast2 = self.simplifier.simplify(ast2)
        print(f"Simplified AST2: {simplified_ast2}")

        # Compare the simplified ASTs
        if self._ast_equal(simplified_ast1, simplified_ast2):
            return "The predicates are equivalent."
        elif self._is_stronger(simplified_ast1, simplified_ast2):
            return "The first predicate is stronger."
        elif self._is_stronger(simplified_ast2, simplified_ast1):
            return "The second predicate is stronger."
        else:
            return "The predicates are not equivalent and neither is stronger."

    def _ast_equal(self, ast1: ASTNode, ast2: ASTNode) -> bool:
        if ast1.value != ast2.value or len(ast1.children) != len(ast2.children):
            return False
        return all(self._ast_equal(c1, c2) for c1, c2 in zip(ast1.children, ast2.children))

    def _is_stronger(self, ast1: ASTNode, ast2: ASTNode) -> bool:
        expr1 = self._to_sympy_expr(ast1)
        expr2 = self._to_sympy_expr(ast2)
        return sp.simplify(sp.Implies(expr1, expr2))

    def _to_sympy_expr(self, ast: ASTNode):
        if not ast.children:
            return sp.Symbol(ast.value.replace('.', '_'))
        args = [self._to_sympy_expr(child) for child in ast.children]
        if ast.value in ('&&', '||', '!', '==', '!=', '>', '<', '>=', '<='):
            return getattr(sp, self._sympy_operator(ast.value))(*args)
        return sp.Symbol(ast.value.replace('.', '_'))

    def _sympy_operator(self, op: str) -> str:
        return {
            '&&': 'And',
            '||': 'Or',
            '!': 'Not',
            '==': 'Eq',
            '!=': 'Ne',
            '>': 'Gt',
            '<': 'Lt',
            '>=': 'Ge',
            '<=': 'Le'
        }[op]



    def _contains(self, haystack: ASTNode, needle: ASTNode) -> bool:
        if haystack.value == needle.value and len(haystack.children) == len(needle.children):
            if all(self._contains(hc, nc) for hc, nc in zip(haystack.children, needle.children)):
                return True
        return any(self._contains(child, needle) for child in haystack.children)

