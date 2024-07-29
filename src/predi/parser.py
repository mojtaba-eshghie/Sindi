from typing import List, Tuple
from predi.config import debug_print


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
            raise ValueError(f"Expected token {expected_tag} but got {token[1]} at position {self.position}")
        self.position += 1
        return token

    def expression(self) -> ASTNode:
        node = self.logical_term()
        #debug_print(f"Parsed term: {node}")

        while self.position < len(self.tokens) and self.tokens[self.position][1] in ('AND', 'OR'):
            operator = self.tokens[self.position]
            #debug_print(f"Parsing operator in expression: {operator}")
            self.position += 1
            right = self.logical_term()
            node = ASTNode(operator[0], [node, right])
            #debug_print(f"Parsed expression with operator: {node}")

        return node

    def logical_term(self) -> ASTNode:
        node = self.equality()
        #debug_print(f"Parsed equality: {node}")

        while self.position < len(self.tokens) and self.tokens[self.position][1] in ('EQUAL', 'NOT_EQUAL'):
            operator = self.tokens[self.position]
            #debug_print(f"Parsing operator in logical term: {operator}")
            self.position += 1
            right = self.equality()
            node = ASTNode(operator[0], [node, right])
            #debug_print(f"Parsed logical term with operator: {node}")

        return node

    def equality(self) -> ASTNode:
        node = self.relational()
        #debug_print(f"Parsed relational: {node}")

        while self.position < len(self.tokens) and self.tokens[self.position][1] in ('GREATER', 'LESS', 'GREATER_EQUAL', 'LESS_EQUAL'):
            operator = self.tokens[self.position]
            #debug_print(f"Parsing operator in equality: {operator}")
            self.position += 1
            right = self.relational()
            node = ASTNode(operator[0], [node, right])
            #debug_print(f"Parsed equality with operator: {node}")

        return node

    def relational(self) -> ASTNode:
        node = self.term()
        #debug_print(f"Parsed term in relational: {node}")

        while self.position < len(self.tokens) and self.tokens[self.position][1] in ('PLUS', 'MINUS'):
            operator = self.tokens[self.position]
            #debug_print(f"Parsing operator in relational: {operator}")
            self.position += 1
            right = self.term()
            node = ASTNode(operator[0], [node, right])
            #debug_print(f"Parsed relational with operator: {node}")

        return node

    def term(self) -> ASTNode:
        node = self.factor()
        #debug_print(f"Parsed factor in term: {node}")

        while self.position < len(self.tokens) and self.tokens[self.position][1] in ('MULTIPLY', 'DIVIDE', 'MODULUS'):
            operator = self.tokens[self.position]
            #debug_print(f"Parsing operator in term: {operator}")
            self.position += 1
            right = self.factor()
            node = ASTNode(operator[0], [node, right])
            #debug_print(f"Parsed term with operator: {node}")

        return node

    def factor(self) -> ASTNode:
        if self.position >= len(self.tokens):
            raise ValueError("Unexpected end of input")
        token = self.tokens[self.position]
        if token[1] in ('TRUE', 'FALSE'):
            self.position += 1
            return ASTNode(token[0])
        if token[1] == 'ADDRESS_LITERAL':
            self.position += 1
            return ASTNode(token[0])
        if token[1] == 'BYTES_LITERAL':
            self.position += 1
            return ASTNode(token[0])
        if token[1] == 'LPAREN':
            self.position += 1
            node = self.expression()
            self.consume('RPAREN')
            return node
        elif token[1] in ('IDENTIFIER', 'MSG_SENDER', 'MSG_ORIGIN', 'INTEGER', 'FLOAT', 'SCIENTIFIC'):
            self.position += 1
            node = ASTNode(token[0])
            return self.postfix(node)
        elif token[1] == 'NOT':
            self.position += 1
            node = self.factor()
            node = ASTNode('!', [node])
            return node
        elif token[1] in ('PLUS', 'MINUS'):
            self.position += 1
            node = self.factor()
            node = ASTNode(token[0], [node])
            return node
        raise ValueError(f"Unexpected token {token[1]} at position {self.position}")

    def postfix(self, node: ASTNode) -> ASTNode:
        while self.position < len(self.tokens) and self.tokens[self.position][1] in ('DOT', 'LBRACKET', 'LPAREN'):
            token = self.tokens[self.position]
            #debug_print(f"Parsing postfix at position {self.position}: {token}")

            if token[1] == 'DOT':
                self.position += 1
                member_token = self.consume('IDENTIFIER')
                node = ASTNode(f"{node.value}.{member_token[0]}")
            elif token[1] == 'LBRACKET':
                self.position += 1
                index_node = self.expression()
                self.consume('RBRACKET')
                node = ASTNode(f"{node.value}[]", [index_node])
            elif token[1] == 'LPAREN':
                self.position += 1
                args = []
                while self.position < len(self.tokens) and self.tokens[self.position][1] != 'RPAREN':
                    args.append(self.expression())
                    if self.position < len(self.tokens) and self.tokens[self.position][1] == 'COMMA':
                        #debug_print(f"Consuming COMMA at position {self.position}")
                        self.position += 1
                self.consume('RPAREN')
                node = ASTNode(f"{node.value}()", args)
            #debug_print(f"Parsed postfix: {node}")
        return node

    def function_call(self, token: Tuple[str, str]) -> ASTNode:
        function_name = token[0]
        self.position += 1  # Consume FUNCTION_CALL token
        self.consume('LPAREN')
        args = []
        while self.position < len(self.tokens) and self.tokens[self.position][1] != 'RPAREN':
            args.append(self.expression())
            if self.position < len(self.tokens) and self.tokens[self.position][1] == 'COMMA':
                self.position += 1
        self.consume('RPAREN')
        node = ASTNode(function_name, args)
        #debug_print(f"Parsed function call: {node}")
        return node