import sympy as sp
from typing import Union
from predi.parser import ASTNode
from predi.config import debug_print

class Simplifier:
    def __init__(self):
        self.symbols = {
            'msg.sender': sp.Symbol('msg_sender'),
            'msg.origin': sp.Symbol('msg_origin'),
            '==': sp.Eq,
            '!=': sp.Ne,
            '>=': sp.Ge,
            '<=': sp.Le,
            '>': sp.Gt,
            '<': sp.Lt,
            '&&': sp.And,
            '||': sp.Or,
            '!': sp.Not
        }

    def simplify(self, ast: ASTNode) -> Union[str, ASTNode]:
        #debug_print(f"Simplifying AST: {ast}")
        sympy_expr = self._to_sympy(ast)
        #debug_print(f"Converted to sympy expression: {sympy_expr}")
        simplified_expr = sp.simplify(sympy_expr)
        #debug_print(f"Simplified sympy expression: {simplified_expr}")
        simplified_ast = self._to_ast(simplified_expr)
        #debug_print(f"Converted back to AST: {simplified_ast}")
        return simplified_ast

    def _to_sympy(self, node: ASTNode):
        if node.value in self.symbols and not node.children:
            return self.symbols[node.value]
        elif node.value in self.symbols:
            if node.value in ('&&', '||'):
                return self.symbols[node.value](*[self._to_sympy(child) for child in node.children])
            elif node.value == '!':
                return self.symbols[node.value](self._to_sympy(node.children[0]))
            elif len(node.children) == 2:
                return self.symbols[node.value](self._to_sympy(node.children[0]), self._to_sympy(node.children[1]))
            else:
                raise ValueError(f"Invalid number of children for operator {node.value}")
        elif isinstance(node.value, (int, float)):
            return sp.Number(node.value)
        else:
            # Preserve function calls and other identifiers as-is
            if '(' in node.value and ')' in node.value:
                func_name = node.value  # Ensure the function name is preserved entirely
                args = node.children
                return sp.Function(func_name)(*map(self._to_sympy, args))
            else:
                return sp.Symbol(node.value.replace('.', '_'))

    def _to_ast(self, expr):
        if isinstance(expr, sp.Equality):
            return ASTNode('==', [self._to_ast(expr.lhs), self._to_ast(expr.rhs)])
        elif isinstance(expr, sp.Rel):
            op_map = {'>': '>', '<': '<', '>=': '>=', '<=': '<=', '!=': '!='}
            return ASTNode(op_map[expr.rel_op], [self._to_ast(expr.lhs), self._to_ast(expr.rhs)])
        elif isinstance(expr, sp.And):
            return ASTNode('&&', [self._to_ast(arg) for arg in expr.args])
        elif isinstance(expr, sp.Or):
            return ASTNode('||', [self._to_ast(arg) for arg in expr.args])
        elif isinstance(expr, sp.Not):
            return ASTNode('!', [self._to_ast(expr.args[0])])
        elif isinstance(expr, sp.Function):
            func_name = str(expr.func)
            return ASTNode(func_name, [self._to_ast(arg) for arg in expr.args])
        else:
            return ASTNode(str(expr))
