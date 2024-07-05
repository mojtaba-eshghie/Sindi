# solidity_predicate_comparison/src/simplifier.py

import sympy as sp
from typing import Union
from src.parser import ASTNode

class Simplifier:
    def __init__(self):
        # Map ASTNode values to sympy symbols
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
        #print(f"Simplifying AST: {ast}")
        sympy_expr = self._to_sympy(ast)
        #print(f"Converted to sympy expression: {sympy_expr}")
        simplified_expr = sp.simplify(sympy_expr)
        #print(f"Simplified sympy expression: {simplified_expr}")
        simplified_ast = self._to_ast(simplified_expr)
        #print(f"Converted back to AST: {simplified_ast}")
        return simplified_ast

    def _to_sympy(self, node: ASTNode):
        #print(f"Converting AST node to sympy: {node}")
        if node.value in self.symbols and not node.children:
            # Leaf nodes such as msg.sender, msg.origin, etc.
            leaf_symbol = self.symbols[node.value]
            #print(f"Leaf node {node.value} mapped to sympy symbol: {leaf_symbol}")
            return leaf_symbol
        elif node.value in self.symbols:
            if node.value in ('&&', '||'):
                return self.symbols[node.value](*[self._to_sympy(child) for child in node.children])
            elif node.value == '!':
                return self.symbols[node.value](self._to_sympy(node.children[0]))
            elif len(node.children) == 2:
                return self.symbols[node.value](self._to_sympy(node.children[0]), self._to_sympy(node.children[1]))
            else:
                raise ValueError(f"Invalid number of children for operator {node.value}")
        elif node.value.isdigit():
            return sp.Integer(node.value)
        else:
            # Handle any identifier as a symbol
            identifier_symbol = sp.Symbol(node.value)
            #print(f"Identifier {node.value} mapped to sympy symbol: {identifier_symbol}")
            return identifier_symbol

    def _to_ast(self, expr):
        #print(f"Converting sympy expression to AST: {expr}")
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
        else:
            return ASTNode(str(expr))

