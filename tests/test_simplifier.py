# solidity_predicate_comparison/tests/test_simplifier.py

import unittest
from src.tokenizer import Tokenizer
from src.parser import Parser, ASTNode
from src.simplifier import Simplifier

class TestSimplifier(unittest.TestCase):
    def setUp(self):
        self.tokenizer = Tokenizer()
        self.simplifier = Simplifier()

    def assertASTEqual(self, ast1, ast2):
        self.assertEqual(ast1.value, ast2.value)
        self.assertEqual(len(ast1.children), len(ast2.children))
        
        # Sort children based on their string representation for comparison
        sorted_children1 = sorted(ast1.children, key=lambda x: repr(x))
        sorted_children2 = sorted(ast2.children, key=lambda x: repr(x))
        
        for child1, child2 in zip(sorted_children1, sorted_children2):
            self.assertASTEqual(child1, child2)

    def test_simplify_simple_predicate(self):
        predicate = "msg.sender == msg.origin"
        tokens = self.tokenizer.tokenize(predicate)
        #print(f"Tokens: {tokens}")
        parser = Parser(tokens)
        ast = parser.parse()
        #print(f"Parsed AST: {ast}")
        simplified_ast = self.simplifier.simplify(ast)
        expected_ast = ASTNode('==', [ASTNode('msg_sender'), ASTNode('msg_origin')])
        # Ensure that the equality arguments are compared without considering their order
        self.assertASTEqual(simplified_ast, expected_ast)

    def test_simplify_complex_predicate(self):
        predicate = "msg.sender != msg.origin && a >= b"
        tokens = self.tokenizer.tokenize(predicate)
        #print(f"Tokens: {tokens}")
        parser = Parser(tokens)
        ast = parser.parse()
        #print(f"Parsed AST: {ast}")
        simplified_ast = self.simplifier.simplify(ast)
        expected_ast = ASTNode('&&', [
            ASTNode('!=', [ASTNode('msg_sender'), ASTNode('msg_origin')]),
            ASTNode('>=', [ASTNode('a'), ASTNode('b')])
        ])
        self.assertASTEqual(simplified_ast, expected_ast)

if __name__ == '__main__':
    pass
    #unittest.main()
