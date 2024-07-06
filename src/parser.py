from typing import List, Tuple, Union

# Define a Node class for the AST
class ASTNode:
    def __init__(self, value: str, children: List['ASTNode'] = None):
        self.value = value
        self.children = children if children is not None else []

    def __repr__(self):
        return f"ASTNode(value='{self.value}', children={self.children})"

class Parser:
    def __init__(self, tokens: List[Tuple[str, str]]):
        self.tokens = tokens
        self.position = 0

    def parse(self) -> ASTNode:
        self.position = 0  # Reset the position for each new parse
        return self.expression()

    def consume(self, expected_tag: str) -> Tuple[str, str]:
        if self.position >= len(self.tokens):
            raise ValueError(f"Unexpected end of input, expected {expected_tag}")
        token = self.tokens[self.position]
        if token[1] != expected_tag:
            raise ValueError(f"Expected token {expected_tag} but got {token[1]}")
        self.position += 1
        return token

    def expression(self) -> ASTNode:
        # Handle the require statement
        if self.position < len(self.tokens) and self.tokens[self.position][1] == 'REQUIRE':
            self.position += 1
            self.consume('LPAREN')
            node = self.expression()
            self.consume('RPAREN')
            return ASTNode('require', [node])

        # Start with a term
        node = self.term()

        # Handle && and || operators
        while self.position < len(self.tokens) and self.tokens[self.position][1] in ('AND', 'OR'):
            operator = self.tokens[self.position]
            self.position += 1
            right = self.term()
            node = ASTNode(operator[0], [node, right])

        return node

    def term(self) -> ASTNode:
        # Handle comparison operators
        node = self.factor()
        while self.position < len(self.tokens) and self.tokens[self.position][1] in ('EQUAL', 'NOT_EQUAL', 'GREATER_EQUAL', 'LESS_EQUAL', 'GREATER', 'LESS'):
            operator = self.tokens[self.position]
            self.position += 1
            right = self.factor()
            node = ASTNode(operator[0], [node, right])
        return node

    def factor(self) -> ASTNode:
        if self.position >= len(self.tokens):
            raise ValueError("Unexpected end of input")
        token = self.tokens[self.position]
        if token[1] == 'LPAREN':
            self.position += 1
            node = self.expression()
            self.consume('RPAREN')
            return node
        elif token[1] in ('IDENTIFIER', 'MSG_SENDER', 'MSG_ORIGIN', 'NUMBER', 'ADDRESS', 'BYTES4', 'BYTES32', 'KECCAK256', 'STRING_LITERAL'):
            self.position += 1
            return ASTNode(token[0])
        elif token[1] == 'NOT':
            self.position += 1
            node = self.factor()
            return ASTNode('!', [node])
        elif token[1] == 'METHOD_CALL' or token[1] == 'FUNCTION_CALL' or token[1] == 'ARRAY_ACCESS':
            self.position += 1
            return ASTNode(token[0])
        raise ValueError(f"Unexpected token {token[1]} at position {self.position}")

