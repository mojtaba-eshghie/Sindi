import sympy as sp
from sympy.logic.inference import satisfiable
from sympy.logic.boolalg import Not, And, Or
from src.tokenizer import Tokenizer
from src.parser import Parser
from src.simplifier import Simplifier
from src.config import debug_print

class Comparator:
    def __init__(self):
        self.tokenizer = Tokenizer()
        self.simplifier = Simplifier()

    def compare(self, predicate1: str, predicate2: str) -> str:
        # Tokenize, parse, and simplify the first predicate
        tokens1 = self.tokenizer.tokenize(predicate1)
        debug_print(f"Tokens1: {tokens1}")
        numerical_expr1, symbolic_expr1 = self._separate_numerical_symbolic(tokens1)
        debug_print(f"Numerical Expression 1: {numerical_expr1}")
        debug_print(f"Symbolic Expression 1: {symbolic_expr1}")
        parser1 = Parser(tokens1)
        ast1 = parser1.parse()
        debug_print(f"Parsed AST1: {ast1}")
        simplified_ast1 = self.simplifier.simplify(ast1)
        debug_print(f"Simplified AST1: {simplified_ast1}")

        # Tokenize, parse, and simplify the second predicate
        tokens2 = self.tokenizer.tokenize(predicate2)
        debug_print(f"Tokens2: {tokens2}")
        numerical_expr2, symbolic_expr2 = self._separate_numerical_symbolic(tokens2)
        debug_print(f"Numerical Expression 2: {numerical_expr2}")
        debug_print(f"Symbolic Expression 2: {symbolic_expr2}")
        parser2 = Parser(tokens2)
        ast2 = parser2.parse()
        debug_print(f"Parsed AST2: {ast2}")
        simplified_ast2 = self.simplifier.simplify(ast2)
        debug_print(f"Simplified AST2: {simplified_ast2}")

        # Convert ASTs to SymPy expressions
        expr1 = self._to_sympy_expr(simplified_ast1)
        expr2 = self._to_sympy_expr(simplified_ast2)

        debug_print(f"SymPy Expression 1: {expr1}")
        debug_print(f"SymPy Expression 2: {expr2}")

        # Simplify expressions
        simplified_expr1 = sp.simplify(expr1)
        simplified_expr2 = sp.simplify(expr2)

        debug_print(f"Simplified SymPy Expression 1: {simplified_expr1}")
        debug_print(f"Simplified SymPy Expression 2: {simplified_expr2}")

        # Check implications using satisfiability
        implies1_to_2 = self._check_implication(simplified_expr1, simplified_expr2, numerical_expr1 or numerical_expr2)
        implies2_to_1 = self._check_implication(simplified_expr2, simplified_expr1, numerical_expr1 or numerical_expr2)

        debug_print(f"Implies expr1 to expr2: {implies1_to_2}")
        debug_print(f"Implies expr2 to expr1: {implies2_to_1}")

        if implies1_to_2 and not implies2_to_1:
            return "The first predicate is stronger."
        elif implies2_to_1 and not implies1_to_2:
            return "The second predicate is stronger."
        elif implies1_to_2 and implies2_to_1:
            return "The predicates are equivalent."
        else:
            return "The predicates are not equivalent and neither is stronger."

    def _to_sympy_expr(self, ast):
        if not ast.children:
            return sp.Symbol(ast.value.replace('.', '_'))
        args = [self._to_sympy_expr(child) for child in ast.children]
        if ast.value in ('&&', '||', '!', '==', '!=', '>', '<', '>=', '<='):
            return getattr(sp, self._sympy_operator(ast.value))(*args)
        return sp.Symbol(ast.value.replace('.', '_'))

    def _sympy_operator(self, op):
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

    def _contains_numerical_comparison(self, tokens):
        """
        Check if the tokenized expression contains numerical comparisons.
        """
        numerical_tokens = {'NUMBER', 'GREATER', 'LESS', 'GREATER_EQUAL', 'LESS_EQUAL'}
        return any(token_type in numerical_tokens for _, token_type in tokens)

    def _separate_numerical_symbolic(self, tokens):
        """
        Separate numerical and symbolic parts of the tokenized expression.
        """
        numerical_tokens = {'NUMBER', 'GREATER', 'LESS', 'GREATER_EQUAL', 'LESS_EQUAL'}
        numerical_expr = any(token_type in numerical_tokens for _, token_type in tokens)
        symbolic_expr = any(token_type not in numerical_tokens for _, token_type in tokens)
        return numerical_expr, symbolic_expr

    def _check_implication(self, expr1, expr2, use_lra):
        """
        Check if expr1 implies expr2 using satisfiability with optional LRA.
        """
        try:
            return not satisfiable(And(expr1, Not(expr2)), use_lra_theory=use_lra)
        except Exception as e:
            debug_print(f"Error checking implication: {e}")
            return False
