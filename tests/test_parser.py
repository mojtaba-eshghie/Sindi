import unittest
from src.predi.tokenizer import Tokenizer
from src.predi.parser import Parser, ASTNode


class TestParser(unittest.TestCase):
    def setUp(self):
        self.tokenizer = Tokenizer()

    def test_parse_simple_predicate(self):
        predicate = "msg.sender == msg.origin"
        tokens = self.tokenizer.tokenize(predicate)
        parser = Parser(tokens)
        ast = parser.parse()
        expected_ast = ASTNode('==', [ASTNode('msg.sender'), ASTNode('msg.origin')])
        self.assertEqual(repr(ast), repr(expected_ast))

    def test_parse_complex_predicate(self):
        predicate = "msg.sender != msg.origin && a >= b"
        tokens = self.tokenizer.tokenize(predicate)
        parser = Parser(tokens)
        ast = parser.parse()
        expected_ast = ASTNode('&&', [
            ASTNode('!=', [ASTNode('msg.sender'), ASTNode('msg.origin')]),
            ASTNode('>=', [ASTNode('a'), ASTNode('b')])
        ])
        self.assertEqual(repr(ast), repr(expected_ast))


    def test_parse_not_operator(self):
        predicate = "!msg.sender"
        tokens = self.tokenizer.tokenize(predicate)
        parser = Parser(tokens)
        ast = parser.parse()
        expected_ast = ASTNode('!', [ASTNode('msg.sender')])
        self.assertEqual(repr(ast), repr(expected_ast))

    def test_parse_method_call(self):
        predicate = "obj.methodCall(param1, param2)"
        tokens = self.tokenizer.tokenize(predicate)
        parser = Parser(tokens)
        ast = parser.parse()
        expected_ast = ASTNode('obj.methodCall(param1, param2)')
      

if __name__ == '__main__':
    unittest.main()
