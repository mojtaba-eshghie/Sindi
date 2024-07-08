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

        # Convert ASTs to SymPy expressions
        expr1 = self._to_sympy_expr(simplified_ast1)
        expr2 = self._to_sympy_expr(simplified_ast2)

        # Simplify expressions
        debug_print(f"SymPy Expression 1: {expr1}")
        simplified_expr1 = sp.simplify(expr1)
        debug_print(f"Simplified SymPy Expression 1: {simplified_expr1}")


        debug_print(f"SymPy Expression 2: {expr2}")
        simplified_expr2 = sp.simplify(expr2)
        debug_print(f"Simplified SymPy Expression 2: {simplified_expr2}")

        # Manually check implications
        implies1_to_2 = self._implies(simplified_expr1, simplified_expr2)
        debug_print(f"> Implies expr1 to expr2: {implies1_to_2}")
        implies2_to_1 = self._implies(simplified_expr2, simplified_expr1)
        debug_print(f"> Implies expr2 to expr1: {implies2_to_1}")

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

    def _implies(self, expr1, expr2):
        """
        Check if expr1 implies expr2 by manually comparing the expressions.
        """
        debug_print(f"Checking implication: {expr1} -> {expr2}")
        if expr1 == expr2:
            debug_print("Expressions are identical.")
            return True

        # Handle AND expression for expr2
        if isinstance(expr2, And):
            # expr1 should imply all parts of expr2 if expr2 is an AND expression
            results = [self._implies(expr1, arg) for arg in expr2.args]
            debug_print(f"Implication results for And expr2 which was `{expr1} => {expr2}`: {results}")
            return all(results)
        
        # Handle AND expression for expr1
        if isinstance(expr1, And):
            # All parts of expr1 should imply expr2 if expr1 is an AND expression
            results = [self._implies(arg, expr2) for arg in expr1.args]
            debug_print(f"Implication results for And expr1 which was `{expr1} => {expr2}`: {results}")
            return any(results)

        # Handle OR expression for expr2
        if isinstance(expr2, Or):
            # expr1 should imply at least one part of expr2 if expr2 is an OR expression
            results = [self._implies(expr1, arg) for arg in expr2.args]
            debug_print(f"Implication results for Or expr2 which was `{expr1} => {expr2}`: {results}")
            return any(results)
        
        # Handle OR expression for expr1
        if isinstance(expr1, Or):
            # All parts of expr1 should imply expr2 if expr1 is an OR expression
            results = [self._implies(arg, expr2) for arg in expr1.args]
            debug_print(f"Implication results for Or expr1 which was `{expr1} => {expr2}`: {results}")
            return all(results)

        # Specific relational operator checks
        if isinstance(expr1, sp.Gt) and isinstance(expr2, sp.Ge):
            result = expr1.lhs == expr2.lhs and expr1.rhs == expr2.rhs
            debug_print(f"Implication Gt -> Ge: {result}")
            return result
        if isinstance(expr1, sp.Ge) and isinstance(expr2, sp.Gt):
            result = False
            debug_print(f"Implication Ge -> Gt: {result}")
            return result
        if isinstance(expr1, sp.Lt) and isinstance(expr2, sp.Le):
            result = expr1.lhs == expr2.lhs and expr1.rhs == expr2.rhs
            debug_print(f"Implication Lt -> Le: {result}")
            return result
        if isinstance(expr1, sp.Le) and isinstance(expr2, sp.Lt):
            result = False
            debug_print(f"Implication Le -> Lt: {result}")
            return result
        if isinstance(expr1, sp.Ge) and isinstance(expr2, sp.Eq):
            result = expr1.lhs == expr2.lhs and expr1.rhs == expr2.rhs
            debug_print(f"Implication Ge -> Eq: {result}")
            return result
        if isinstance(expr1, sp.Le) and isinstance(expr2, sp.Eq):
            result = expr1.lhs == expr2.lhs and expr1.rhs == expr2.rhs
            debug_print(f"Implication Le -> Eq: {result}")
            return result

        # Check specific cases of comparisons for stronger implication
        if isinstance(expr1, sp.Le) and isinstance(expr2, sp.Eq):
            result = expr1.lhs == expr2.lhs and expr1.rhs == expr2.rhs and not satisfiable(And(expr1, Not(expr2)))
            debug_print(f"Implication Le -> Eq with satisfiability check: {result}")
            return result
        if isinstance(expr2, sp.Eq) and isinstance(expr1, sp.Le):
            result = expr1.lhs == expr2.lhs and expr1.rhs == expr2.rhs
            debug_print(f"Implication Eq -> Le: {result}")
            return result

        # Default case
        return False

    def _contains_numerical_comparison(self, tokens):
        """
        Check if the tokenized expression contains numerical comparisons.
        """
        numerical_tokens = {'NUMBER', 'GREATER', 'LESS', 'GREATER_EQUAL', 'LESS_EQUAL'}
        return any(token_type in numerical_tokens for _, token_type in tokens)
