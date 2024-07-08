import sympy as sp
from sympy.logic.inference import satisfiable
from sympy.logic.boolalg import Implies, Not, And, Or
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
        use_aux_expr1 = self._contains_numerical_comparison(tokens1)
        parser1 = Parser(tokens1)
        ast1 = parser1.parse()
        debug_print(f"Parsed AST1: {ast1}")
        simplified_ast1 = self.simplifier.simplify(ast1)
        debug_print(f"Simplified AST1: {simplified_ast1}")

        # Tokenize, parse, and simplify the second predicate
        tokens2 = self.tokenizer.tokenize(predicate2)
        debug_print(f"Tokens2: {tokens2}")
        use_aux_expr2 = self._contains_numerical_comparison(tokens2)
        parser2 = Parser(tokens2)
        ast2 = parser2.parse()
        debug_print(f"Parsed AST2: {ast2}")
        simplified_ast2 = self.simplifier.simplify(ast2)
        debug_print(f"Simplified AST2: {simplified_ast2}")

        # Convert ASTs to SymPy expressions
        expr1 = self._to_sympy_expr(simplified_ast1, use_aux_expr1)
        expr2 = self._to_sympy_expr(simplified_ast2, use_aux_expr2)

        debug_print(f"SymPy Expression 1: {expr1}")
        debug_print(f"SymPy Expression 2: {expr2}")

        # Simplify expressions
        simplified_expr1 = sp.simplify(expr1)
        simplified_expr2 = sp.simplify(expr2)

        debug_print(f"Simplified SymPy Expression 1: {simplified_expr1}")
        debug_print(f"Simplified SymPy Expression 2: {simplified_expr2}")

        # Define auxiliary conditions for numerical comparisons
        aux_conditions = self._define_auxiliary_conditions()

        # Check implications using satisfiability
        implies1_to_2 = not satisfiable(And(simplified_expr1, Not(simplified_expr2), aux_conditions))
        implies2_to_1 = not satisfiable(And(simplified_expr2, Not(simplified_expr1), aux_conditions))

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

    def _to_sympy_expr(self, ast, use_aux):
        if not ast.children:
            return sp.Symbol(ast.value.replace('.', '_'))
        args = [self._to_sympy_expr(child, use_aux) for child in ast.children]
        if ast.value in ('&&', '||', '!', '==', '!=', '>', '<', '>=', '<='):
            if use_aux and ast.value in ('>', '>=', '<', '<='):
                return self._auxiliary_inequality(ast.value, args)
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

    def _auxiliary_inequality(self, op, args):
        """
        Define auxiliary symbols for inequalities to check consistency.
        """
        lhs, rhs = args
        if op == '>':
            return sp.Symbol(f'{lhs}_gt_{rhs}')
        elif op == '>=':
            return sp.Symbol(f'{lhs}_ge_{rhs}')
        elif op == '<':
            return sp.Symbol(f'{lhs}_lt_{rhs}')
        elif op == '<=':
            return sp.Symbol(f'{lhs}_le_{rhs}')

    def _define_auxiliary_conditions(self):
        """
        Define the logical conditions for auxiliary symbols to be consistent.
        """
        A_gt_B = sp.Symbol('A_gt_B')
        A_ge_B = sp.Symbol('A_ge_B')
        B_lt_A = sp.Symbol('B_lt_A')
        B_le_A = sp.Symbol('B_le_A')
        return And(
            Implies(A_gt_B, A_ge_B),
            Implies(B_lt_A, B_le_A),
            Not(Implies(A_ge_B, A_gt_B)),
            Not(Implies(B_le_A, B_lt_A))
        )
