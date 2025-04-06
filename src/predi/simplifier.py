import sympy as sp
from typing import Union
from predi.parser import ASTNode
#from predi.config import debug_print

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

        if not node.children:
            try:
                return sp.Number(float(node.value)) if '.' in node.value else sp.Number(int(node.value))
            except ValueError:
                return sp.Symbol(node.value.replace('.', '_'))

        # Handle indexed attributes: a[b].c
        if '[]' in node.value and '.' in node.value:
            base_name, attr = node.value.split('.')
            base_name = base_name.replace('[]', '')
            base = sp.IndexedBase(f"{base_name}_{attr}")
            index = self._to_sympy(node.children[0])
            return base[index]

        # Handle indexing without attributes: a[b]
        if '[]' in node.value:
            base_name = node.value.replace('[]', '')
            base = sp.IndexedBase(base_name)
            index = self._to_sympy(node.children[0])
            return base[index]

        if '(' in node.value and ')' in node.value:
            func_name = node.value.replace('()', '')
            args = [self._to_sympy(child) for child in node.children]
            return sp.Function(func_name)(*args)

        args = [self._to_sympy(child) for child in node.children]
        return sp.Symbol(node.value.replace('.', '_'))(*args)


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
