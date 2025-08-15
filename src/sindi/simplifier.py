import sympy as sp
from typing import Union
from src.sindi.parser import ASTNode
#from predi.config import debug_print

class Simplifier:
    def __init__(self):
        # Remove the '-' mapping from here
        self.symbols = {
            'msg.sender': sp.Symbol('msg_sender'),
            'msg.origin': sp.Symbol('msg_origin'),
            # Comparisons
            '==': sp.Eq,
            '!=': sp.Ne,
            '>=': sp.Ge,
            '<=': sp.Le,
            '>': sp.Gt,
            '<': sp.Lt,
            # Logical
            '&&': sp.And,
            '||': sp.Or,
            '!': sp.Not,
            # Arithmetic (Keep Add, Mul, remove Sub)
            '+': sp.Add,
            # '-': sp.Sub, # we will handle subtraction in _to_sympy as a special case of addition
            '*': sp.Mul,
            '/': sp.Mul # Represents division a/b as a * (b**-1)
        }

    def simplify(self, ast: ASTNode) -> Union[str, ASTNode]:
        # ... (rest of simplify method remains the same) ...
        sympy_expr = self._to_sympy(ast)
        simplified_expr = sp.simplify(sympy_expr)
        simplified_ast = self._to_ast(simplified_expr)
        return simplified_ast

    def _to_sympy(self, node: ASTNode):
        # Handle symbols defined in self.symbols (constants like msg.sender)
        if node.value in self.symbols and not node.children:
            # Ensure it's not an operator symbol before returning directly
            # (Operators should be handled below based on children)
            if node.value not in ('+', '*', '/', '&&', '||', '!', '==', '!=', '>=', '<=', '>', '<'):
                 return self.symbols[node.value]

        # Handle operators defined in self.symbols (logical, comparison, +, *)
        # NOTE: Subtraction '-' is handled in a separate block below
        if node.value in self.symbols:
            if node.value in ('&&', '||'): # Logical AND/OR (n-ary)
                return self.symbols[node.value](*[self._to_sympy(child) for child in node.children])
            elif node.value == '!': # Logical NOT (unary)
                if len(node.children) == 1:
                     return self.symbols[node.value](self._to_sympy(node.children[0]))
                else:
                     raise ValueError(f"Invalid number of children for NOT operator: {node}")
            # Handle binary operators (+, *, /, comparisons) - EXCLUDES '-'
            elif node.value in ('==', '!=', '>=', '<=', '>', '<', '+', '*', '/'):
                if len(node.children) == 2:
                    left = self._to_sympy(node.children[0])
                    right = self._to_sympy(node.children[1])
                    # Special handling for division: convert a / b to a * (1/b)
                    if node.value == '/':
                         # Ensure right is not zero if possible (simplification might handle it)
                         return sp.Mul(left, sp.Pow(right, -1))
                    else:
                         # Use Add for '+' and Mul for '*' and comparison functions
                         return self.symbols[node.value](left, right)
                else:
                    raise ValueError(f"Invalid number of children for binary operator '{node.value}': {node}")
            # If node.value was in self.symbols but not handled (e.g., msg.sender with children?),
            # let it pass to other handlers or raise error later.

        # ---> HANDLE SUBTRACTION EXPLICITLY <---
        elif node.value == '-':
            if len(node.children) == 2:
                left = self._to_sympy(node.children[0])
                right = self._to_sympy(node.children[1])
                # Represent subtraction a - b as Add(a, Mul(-1, b))
                return sp.Add(left, sp.Mul(sp.Integer(-1), right))
            elif len(node.children) == 1: # Handle unary minus (negation)
                 operand = self._to_sympy(node.children[0])
                 return sp.Mul(sp.Integer(-1), operand)
            else:
                 raise ValueError(f"Invalid number of children for subtraction/negation operator '-': {node}")
        # ---> END OF SUBTRACTION HANDLING <---


        # Handle numbers (constants without children)
        # Placed after operator checks
        elif not node.children:
            try:
                # Use sp.Integer for whole numbers, sp.Float for decimals/scientific
                if '.' in node.value or 'e' in node.value or 'E' in node.value:
                     # Use Float for anything that looks like a float or scientific notation
                     return sp.Float(node.value)
                else:
                    # Otherwise, assume integer
                    return sp.Integer(int(node.value))
            except ValueError:
                # If it's not a number, treat as a symbol (variable name)
                # Replace '.' typically found in Solidity state vars like 'owner.balance'
                return sp.Symbol(node.value.replace('.', '_'))

        # Handle function calls like balanceOf(to) or name()
        # Checking for '()' might be fragile; consider a dedicated node type from parser if possible.
        elif '(' in node.value and ')' in node.value: # Basic check for function call syntax in value
             func_name = node.value.replace('()', '')
             # Replace dots in function names if needed (e.g., token.balanceOf -> token_balanceOf)
             safe_func_name = func_name.replace('.', '_')

             # Proceed to treat as a function call
             args = [self._to_sympy(child) for child in node.children]
             # Use sp.Function for undefined functions
             # We assume Solidity functions are uninterpreted unless mapped specifically
             return sp.Function(safe_func_name)(*args)

        # Handle indexed access: a[b] or potentially a[b].c (parser dependent)
        # This logic might need refinement based on exact AST structure for complex cases
        elif '[]' in node.value: # Basic check for indexing syntax in value
             # Simplistic handling: Treat array[index] as Function('array')(index)
             base_name = node.value.replace('[]', '')
             safe_base_name = base_name.replace('.', '_') # Handle cases like map.value[key] -> map_value[key]

             # Ensure there is exactly one child representing the index
             if len(node.children) == 1:
                  index_arg = self._to_sympy(node.children[0])
                  return sp.Function(safe_base_name)(index_arg)
             else:
                  raise ValueError(f"Invalid structure for indexed access node: {node}")

        # --- Fallback for unknown node types ---
        # If none of the above matched, it's an unexpected structure.
        raise ValueError(f"Unhandled AST node type or structure in _to_sympy: {node}")

    def _to_ast(self, expr):
        # ... (rest of _to_ast method remains the same, but may need updates for Add, Mul, Sub etc.) ...

        # Add handling for arithmetic operations when converting back
        if isinstance(expr, sp.Add):
            return ASTNode('+', [self._to_ast(arg) for arg in expr.args])
        elif isinstance(expr, sp.Mul):
            # Separate factors and powers for potential division representation
            numer_args = []
            denom_args = []
            for arg in expr.args:
                if isinstance(arg, sp.Pow) and arg.exp.is_negative and arg.exp == -1:
                     denom_args.append(self._to_ast(arg.base))
                elif isinstance(arg, sp.Number) and arg.is_Rational and arg < 0:
                     # Handle negative constants if needed, or absorb sign elsewhere
                     numer_args.append(self._to_ast(arg)) # Keep sign for now
                else:
                     numer_args.append(self._to_ast(arg))

            if not denom_args: # It's a multiplication
                 return ASTNode('*', numer_args)
            else: # It represents a division
                 # Reconstruct numerator
                 if len(numer_args) == 0: numer_ast = ASTNode('1') # Numerator is 1
                 elif len(numer_args) == 1: numer_ast = numer_args[0]
                 else: numer_ast = ASTNode('*', numer_args) # Numerator is a product

                 # Reconstruct denominator
                 if len(denom_args) == 1: denom_ast = denom_args[0]
                 else: denom_ast = ASTNode('*', denom_args) # Denominator is a product

                 return ASTNode('/', [numer_ast, denom_ast])

        elif isinstance(expr, sp.Pow):
             if expr.exp == -1:
                  # This might be handled within Mul, but have a fallback
                  return ASTNode('/', [ASTNode('1'), self._to_ast(expr.base)])
             elif expr.exp > 0 and expr.exp.is_integer:
                  # Potentially handle ** operator if needed
                  return ASTNode('**', [self._to_ast(expr.base), self._to_ast(expr.exp)]) # Or handle differently
             # Default representation if not simple power or division
             return ASTNode(str(expr)) # Fallback


        elif isinstance(expr, sp.Integer) or isinstance(expr, sp.Float) or isinstance(expr, sp.Rational):
            return ASTNode(str(expr))
        elif isinstance(expr, sp.Symbol):
            # Convert back from underscore potentially used? Or keep original name map?
            # Assuming Symbol names are directly usable or stored somewhere.
            return ASTNode(str(expr)) # Simplest conversion

        # --- Existing _to_ast logic ---
        elif isinstance(expr, sp.Equality):
            return ASTNode('==', [self._to_ast(expr.lhs), self._to_ast(expr.rhs)])
        elif isinstance(expr, sp.Rel):
            op_map = {'>': '>', '<': '<', '>=': '>=', '<=': '<=', '!=': '!='}
            # Ensure expr.rel_op is in op_map or handle error
            op = op_map.get(expr.rel_op)
            if op is None: raise ValueError(f"Unknown relational operator in SymPy expression: {expr.rel_op}")
            return ASTNode(op, [self._to_ast(expr.lhs), self._to_ast(expr.rhs)])
        elif isinstance(expr, sp.And):
            return ASTNode('&&', [self._to_ast(arg) for arg in expr.args])
        elif isinstance(expr, sp.Or):
            return ASTNode('||', [self._to_ast(arg) for arg in expr.args])
        elif isinstance(expr, sp.Not):
            # Ensure Not has only one argument
            if len(expr.args) == 1:
                 return ASTNode('!', [self._to_ast(expr.args[0])])
            else:
                 raise ValueError(f"Invalid number of arguments for Not expression: {expr}")
        elif isinstance(expr, sp.Function):
            func_name = str(expr.func)
            # Convert args back
            args_ast = [self._to_ast(arg) for arg in expr.args]
            # Reconstruct original function name format if needed (e.g., add '()')
            # This might need adjustment based on how func names are stored/parsed
            return ASTNode(f"{func_name}()", args_ast) # Assuming functions stored like 'balanceOf()'
        # --- End of existing _to_ast logic ---

        # Fallback for any other type
        else:
             # Convert unknown sympy types to string representation
             # Might lose structure, consider logging a warning
             return ASTNode(str(expr))