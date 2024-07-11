from typing import List, Tuple
from src.config import debug_print

class ASTNode:
    def __init__(self, value: str, children: List['ASTNode'] = None):
        self.value = value
        self.children = children if children is not None else []

    def __repr__(self):
        return f"ASTNode(value='{self.value}', children={self.children})"

class Parser:
    def __init__(self, tokens):
        self.tokens = tokens
        self.position = 0

    def parse(self) -> ASTNode:
        self.position = 0  # Reset the position for each new parse
        return self.expression()

    def expression(self) -> ASTNode:
        node = self.logical_term()
        debug_print(f"Parsed term: {node}")

        while self.position < len(self.tokens) and self.tokens[self.position][1] in ('AND', 'OR'):
            operator = self.tokens[self.position]
            debug_print(f"Parsing operator in expression: {operator}")
            self.position += 1
            right = self.logical_term()
            node = ASTNode(operator[0], [node, right])
            debug_print(f"Parsed expression with operator: {node}")

        return node

    def logical_term(self) -> ASTNode:
        node = self.equality()
        debug_print(f"Parsed equality: {node}")

        while self.position < len(self.tokens) and self.tokens[self.position][1] in ('EQUAL', 'NOT_EQUAL'):
            operator = self.tokens[self.position]
            debug_print(f"Parsing operator in logical_term: {operator}")
            self.position += 1
            right = self.equality()
            node = ASTNode(operator[0], [node, right])
            debug_print(f"Parsed logical_term with operator: {node}")

        return node

    def equality(self) -> ASTNode:
        node = self.relational()
        debug_print(f"Parsed relational: {node}")

        while self.position < len(self.tokens) and self.tokens[self.position][1] in ('LESS', 'LESS_EQUAL', 'GREATER', 'GREATER_EQUAL'):
            operator = self.tokens[self.position]
            debug_print(f"Parsing operator in equality: {operator}")
            self.position += 1
            right = self.relational()
            node = ASTNode(operator[0], [node, right])
            debug_print(f"Parsed equality with operator: {node}")

        return node

    def relational(self) -> ASTNode:
        node = self.term()
        debug_print(f"Parsed term in relational: {node}")

        while self.position < len(self.tokens) and self.tokens[self.position][1] in ('PLUS', 'MINUS'):
            operator = self.tokens[self.position]
            debug_print(f"Parsing operator in relational: {operator}")
            self.position += 1
            right = self.term()
            node = ASTNode(operator[0], [node, right])
            debug_print(f"Parsed relational with operator: {node}")

        return node

    def term(self) -> ASTNode:
        node = self.factor()
        debug_print(f"Parsed factor in term: {node}")

        while self.position < len(self.tokens) and self.tokens[self.position][1] in ('MULTIPLY', 'DIVIDE', 'MODULUS'):
            operator = self.tokens[self.position]
            debug_print(f"Parsing operator in term: {operator}")
            self.position += 1
            right = self.factor()
            node = ASTNode(operator[0], [node, right])
            debug_print(f"Parsed term with operator: {node}")

        return node

    def factor(self) -> ASTNode:
        token = self.tokens[self.position]
        debug_print(f"Parsing factor: {token}")

        if token[1] == 'LPAREN':
            self.position += 1
            node = self.expression()
            self.consume('RPAREN')
            return node
        elif token[1] in ('IDENTIFIER', 'MSG_SENDER', 'MSG_ORIGIN', 'INTEGER', 'FLOAT'):
            # Check if next token is a unit identifier (days, minutes, seconds)
            if token[1] == 'INTEGER' and self.position + 1 < len(self.tokens) and self.tokens[self.position + 1][1] == 'IDENTIFIER':
                unit_token = self.tokens[self.position + 1]
                self.position += 2
                combined_value = f"{token[0]} {unit_token[0]}"
                return ASTNode(combined_value, [])
            else:
                self.position += 1
                return ASTNode(token[0], [])
        elif token[1] in ('PLUS', 'MINUS', 'NOT'):
            self.position += 1
            right = self.factor()
            return ASTNode(token[0], [right])

        raise ValueError(f"Unexpected token: {token[1]} at position {self.position}")

    def consume(self, expected_tag):
        token = self.tokens[self.position]
        debug_print(f"Consuming token: {token}, expecting: {expected_tag}")
        if token[1] != expected_tag:
            raise ValueError(f"Expected token {expected_tag} but got {token[1]} at position {self.position}")
        self.position += 1
        return token
