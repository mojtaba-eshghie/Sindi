import sympy as sp
from src.tokenizer import Tokenizer
from src.parser import Parser
from src.simplifier import Simplifier
from src.parser import ASTNode
from src.config import debug_print


class Comparator:
    def __init__(self):
        self.tokenizer = Tokenizer()
        self.simplifier = Simplifier()

    def compare(self, predicate1: str, predicate2: str) -> str:
        # Tokenize, parse, and simplify the first predicate
        tokens1 = self.tokenizer.tokenize(predicate1)
        debug_print(f"Tokens1: {tokens1}")
        parser1 = Parser(tokens1)
        ast1 = parser1.parse()
        debug_print(f"Parsed AST1: {ast1}")
        simplified_ast1 = self.simplifier.simplify(ast1)
        debug_print(f"Simplified AST1: {simplified_ast1}")

        # Tokenize, parse, and simplify the second predicate
        tokens2 = self.tokenizer.tokenize(predicate2)
        debug_print(f"Tokens2: {tokens2}")
        parser2 = Parser(tokens2)
        ast2 = parser2.parse()
        debug_print(f"Parsed AST2: {ast2}")
        simplified_ast2 = self.simplifier.simplify(ast2)
        debug_print(f"Simplified AST2: {simplified_ast2}")

        # Compare the simplified ASTs using logical equivalence
        expr1 = self._to_sympy_expr(simplified_ast1)
        expr2 = self._to_sympy_expr(simplified_ast2)

        debug_print(f"SymPy Expression 1: {expr1}")
        debug_print(f"SymPy Expression 2: {expr2}")

        # Check for equivalence
        if sp.simplify(expr1 == expr2):
            debug_print("Predicates are equivalent")
            return "The predicates are equivalent."

        # Check if one implies the other
        implies1_to_2 = sp.simplify(sp.Implies(expr1, expr2)) == True
        implies2_to_1 = sp.simplify(sp.Implies(expr2, expr1)) == True

        debug_print(f"Implies expr1 to expr2: {implies1_to_2}")
        debug_print(f"Implies expr2 to expr1: {implies2_to_1}")

        if implies1_to_2 and not implies2_to_1:
            return "The first predicate is stronger."
        elif implies2_to_1 and not implies1_to_2:
            return "The second predicate is stronger."
        else:
            return "The predicates are not equivalent and neither is stronger."

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
