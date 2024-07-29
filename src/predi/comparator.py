import sympy as sp
from sympy.logic.boolalg import And, Or, Not
from sympy.logic.inference import satisfiable
from predi.tokenizer import Tokenizer
from predi.parser import Parser
from predi.simplifier import Simplifier
from predi.config import debug_print


class Comparator:
    def __init__(self):
        self.tokenizer = Tokenizer()
        self.simplifier = Simplifier()

    def compare(self, predicate1: str, predicate2: str) -> str:
        # Tokenize, parse, and simplify the first predicate
        tokens1 = self.tokenizer.tokenize(predicate1)
        #debug_print(f"Tokens1: {tokens1}")
        parser1 = Parser(tokens1)
        ast1 = parser1.parse()
        #debug_print(f"Parsed AST1: {ast1}")

        # Tokenize, parse, and simplify the second predicate
        tokens2 = self.tokenizer.tokenize(predicate2)
        #debug_print(f"Tokens2: {tokens2}")
        parser2 = Parser(tokens2)
        ast2 = parser2.parse()
        #debug_print(f"Parsed AST2: {ast2}")

        # Convert ASTs to SymPy expressions
        expr1 = self._to_sympy_expr(ast1)
        expr2 = self._to_sympy_expr(ast2)

        #debug_print(f'> expr1: {expr1}')
        #debug_print(f'> expr2: {expr2}')

        # Simplify expressions
        simplified_expr1 = sp.simplify(expr1)
        #debug_print(f"Simplified SymPy Expression 1: {simplified_expr1}")

        simplified_expr2 = sp.simplify(expr2)
        #debug_print(f"Simplified SymPy Expression 2: {simplified_expr2}")

        # Manually check implications
        implies1_to_2 = self._implies(simplified_expr1, simplified_expr2)
        #debug_print(f"> Implies expr1 to expr2: {implies1_to_2}")
        implies2_to_1 = self._implies(simplified_expr2, simplified_expr1)
        #debug_print(f"> Implies expr2 to expr1: {implies2_to_1}")

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
            try:
                # Try converting to int or float if the value is a numeric string
                value = float(ast.value) if '.' in ast.value else int(ast.value)
                return sp.Number(value)
            except ValueError:
                # If conversion fails, treat it as a symbol
                return sp.Symbol(ast.value.replace('.', '_'))
        args = [self._to_sympy_expr(child) for child in ast.children]
        if ast.value in ('&&', '||', '!', '==', '!=', '>', '<', '>=', '<='):
            return getattr(sp, self._sympy_operator(ast.value))(*args)
        elif ast.value == '/':
            return sp.Mul(sp.Pow(args[1], -1), args[0])
        elif ast.value == '+':
            return sp.Add(*args)
        elif ast.value == '-':
            return sp.Add(args[0], sp.Mul(-1, args[1]))
        elif ast.value == '*':
            return sp.Mul(*args)
        elif '()' in ast.value:
            func_name = ast.value.replace('()', '')
            return sp.Function(func_name)(*args)
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
        #debug_print(f"Checking implication: {expr1} -> {expr2}")
        if expr1 == expr2:
            #debug_print("Expressions are identical.")
            return True

        # Handle equivalences through algebraic manipulation
        try:
            if sp.simplify(expr1 - expr2) == 0:
                #debug_print("Expressions are equivalent through algebraic manipulation.")
                return True
        except Exception as e: 
            #debug_print(f"Error: {e}")
            pass


        # Handle negation equivalence (e.g., !used[salt] == used[salt] == false)
        if isinstance(expr1, Not) and isinstance(expr2, sp.Equality):
            #debug_print('>>>>>>>>>>>> here1')
            #debug_print(f'expr2: {expr2}')
            #debug_print(f'expr2.rhs: {expr2.rhs}')
            #debug_print(f'expr2.lhs: {expr2.lhs}')
            if expr2.rhs == sp.false or expr2.rhs == False or expr2.rhs == sp.Symbol('false'):
                #debug_print('>>>>>>>>>>>> here1.1')
                return self._implies(expr1.args[0], expr2.lhs)
            if expr2.lhs == sp.false or expr2.lhs == False or expr2.lhs == sp.Symbol('false'):
                #debug_print('>>>>>>>>>>>> here1.2')
                return self._implies(expr1.args[0], expr2.rhs)

        if isinstance(expr2, Not) and isinstance(expr1, sp.Equality):
            #debug_print('>>>>>>>>>>>> here2')
            #debug_print(f'expr1: {expr1}')
            #debug_print(f'expr1.rhs: {expr1.rhs}')
            #debug_print(f'expr1.lhs: {expr1.lhs}')
            if expr1.rhs == sp.false or expr1.rhs == False or expr1.rhs == sp.Symbol('false'):
                #debug_print('>>>>>>>>>>>> here2.1')
                return self._implies(expr2.args[0], expr1.lhs)
            if expr1.lhs == sp.false or expr1.lhs == False or expr1.lhs == sp.Symbol('false'):
                #debug_print('>>>>>>>>>>>> here2.2')
                return self._implies(expr2.args[0], expr1.rhs)

        # Handle equivalence involving `true`
        if isinstance(expr1, sp.Symbol) and isinstance(expr2, sp.Equality):
            if expr2.rhs == sp.true or expr2.rhs == True or expr2.rhs == sp.Symbol('true'):
                return self._implies(expr1, expr2.lhs)
            if expr2.lhs == sp.true or expr2.lhs == True or expr2.lhs == sp.Symbol('true'):
                return self._implies(expr1, expr2.rhs)
        
        if isinstance(expr2, sp.Symbol) and isinstance(expr1, sp.Equality):
            if expr1.rhs == sp.true or expr1.rhs == True or expr1.rhs == sp.Symbol('true'):
                return self._implies(expr2, expr1.lhs)
            if expr1.lhs == sp.true or expr1.lhs == True or expr1.lhs == sp.Symbol('true'):
                return self._implies(expr2, expr1.rhs)
        

        # Handle logical equivalence for AND, OR, NOT operations
        if isinstance(expr1, Not) and isinstance(expr2, Or):
            if len(expr2.args) == 2:
                left, right = expr2.args
                if isinstance(left, sp.Equality) and left.rhs == sp.false:
                    return self._implies(expr1.args[0], left.lhs) and self._implies(right, sp.true)
                if isinstance(right, sp.Equality) and right.rhs == sp.false:
                    return self._implies(expr1.args[0], right.lhs) and self._implies(left, sp.true)

        if isinstance(expr2, Not) and isinstance(expr1, Or):
            if len(expr1.args) == 2:
                left, right = expr1.args
                if isinstance(left, sp.Equality) and left.rhs == sp.false:
                    return self._implies(expr2.args[0], left.lhs) and self._implies(right, sp.true)
                if isinstance(right, sp.Equality) and right.rhs == sp.false:
                    return self._implies(expr2.args[0], right.lhs) and self._implies(left, sp.true)

        if isinstance(expr1, And) and isinstance(expr2, And):
            if len(expr1.args) == len(expr2.args):
                return all(self._implies(arg1, arg2) for arg1, arg2 in zip(expr1.args, expr2.args))

        if isinstance(expr1, Or) and isinstance(expr2, Or):
            if len(expr1.args) == len(expr2.args):
                return all(self._implies(arg1, arg2) for arg1, arg2 in zip(expr1.args, expr2.args))



        # Handle AND expression for expr2
        if isinstance(expr2, And):
            # expr1 should imply all parts of expr2 if expr2 is an AND expression
            results = [self._implies(expr1, arg) for arg in expr2.args]
            #debug_print(f"Implication results for And expr2 which was `{expr1} => {expr2}`: {results}")
            return all(results)

        # Handle AND expression for expr1
        if isinstance(expr1, And):
            # All parts of expr1 should imply expr2 if expr1 is an AND expression
            results = [self._implies(arg, expr2) for arg in expr1.args]
            #debug_print(f"Implication results for And expr1 which was `{expr1} => {expr2}`: {results}")
            return any(results)

        # Handle OR expression for expr2
        if isinstance(expr2, Or):
            # expr1 should imply at least one part of expr2 if expr2 is an OR expression
            results = [self._implies(expr1, arg) for arg in expr2.args]
            #debug_print(f"Implication results for Or expr2 which was `{expr1} => {expr2}`: {results}")
            return any(results)

        # Handle OR expression for expr1
        if isinstance(expr1, Or):
            # All parts of expr1 should imply expr2 if expr1 is an OR expression
            results = [self._implies(arg, expr2) for arg in expr1.args]
            #debug_print(f"Implication results for Or expr1 which was `{expr1} => {expr2}`: {results}")
            return all(results)

        # Handle function calls
        if isinstance(expr1, sp.Function) and isinstance(expr2, sp.Function):
            # Ensure the function names and the number of arguments match
            if expr1.func == expr2.func and len(expr1.args) == len(expr2.args):
                return all(self._implies(arg1, arg2) for arg1, arg2 in zip(expr1.args, expr2.args))
            return False

        if isinstance(expr1, sp.Symbol) and isinstance(expr2, sp.Symbol):
            return expr1 == expr2

        # Specific relational operator checks for numerical comparisons
        relational_operators = (sp.Gt, sp.Ge, sp.Lt, sp.Le, sp.Eq, sp.Ne)
        if isinstance(expr1, relational_operators) and isinstance(expr2, relational_operators):
            #debug_print(f'we are here!... expr1: {expr1}, expr2: {expr2}')
            # Check for Eq vs non-Eq comparisons; we don't handle this well, let's return False
            if (isinstance(expr1, sp.Eq) and not isinstance(expr2, sp.Eq)) or (not isinstance(expr1, sp.Eq) and isinstance(expr2, sp.Eq)):
                return False  # Handle Eq vs non-Eq cases explicitly

            if all(isinstance(arg, (sp.Float, sp.Integer, sp.Symbol)) for arg in [expr1.lhs, expr1.rhs, expr2.lhs, expr2.rhs]):
                #debug_print(f'Inside!... expr1: {expr1}, expr2: {expr2}')
                # Check if the negation of the implication is not satisfiable
                try:
                    negation = sp.And(expr1, Not(expr2))
                    #debug_print(f"Negation of the implication {expr1} -> {expr2}: {satisfiable(negation)}; type of {type(satisfiable(negation))}")
                    result = not satisfiable(negation, use_lra_theory=True)
                    #debug_print(f"Implication {expr1} -> {expr2} using satisfiable: {result}")
                    return result
                except Exception as e:
                    #debug_print(f"Error: {e}")
                    return False
        return False
