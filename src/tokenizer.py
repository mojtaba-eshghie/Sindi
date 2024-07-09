import re
from typing import List, Tuple

class Tokenizer:
    def __init__(self):
        self.token_patterns = [
            (r'\bmsg\.sender\b', 'MSG_SENDER'),
            (r'\bmsg\.origin\b', 'MSG_ORIGIN'),
            (r'\brequire\b', 'REQUIRE'),
            (r'==', 'EQUAL'),
            (r'!=', 'NOT_EQUAL'),
            (r'>=', 'GREATER_EQUAL'),
            (r'<=', 'LESS_EQUAL'),
            (r'>', 'GREATER'),
            (r'<', 'LESS'),
            (r'&&', 'AND'),
            (r'\|\|', 'OR'),
            (r'\!', 'NOT'),
            (r'&', 'BITWISE_AND'),
            (r'\?', 'QUESTION'),
            (r':', 'COLON'),
            (r'\(', 'LPAREN'),
            (r'\)', 'RPAREN'),
            (r'\+', 'PLUS'),
            (r'\-', 'MINUS'),
            (r'\*', 'MULTIPLY'),
            (r'\/', 'DIVIDE'),
            (r'\%', 'MODULUS'),
            (r'\.', 'DOT'),
            (r',', 'COMMA'),
            (r'=', 'ASSIGN'),
            (r'\[', 'LBRACKET'),
            (r'\]', 'RBRACKET'),
            (r'\"[^\"]*\"', 'STRING_LITERAL'),
            (r'\b\d+\.\d+\b', 'FLOAT'),
            (r'\b\d+\b', 'INTEGER'),
            (r'\btrue\b', 'TRUE'),
            (r'\bfalse\b', 'FALSE'),
            (r'0x[0-9a-fA-F]{40}', 'ADDRESS_LITERAL'),
            (r'0x[0-9a-fA-F]+', 'BYTES_LITERAL'),
            (r'[a-zA-Z_]\w*', 'IDENTIFIER'),
            (r'\s+', None),  # Let's ignore whitespace(s)
        ]

    def normalize(self, predicate: str) -> str:
        """
        Normalizes the given predicate string by removing unnecessary spaces and adding spaces around operators and parentheses.

        Args:
            predicate (str): The predicate string to be normalized.

        Returns:
            str: The normalized predicate string.
        """
        predicate = re.sub(r'\s+', '', predicate)
        predicate = re.sub(r'([!=<>]=?)', r' \1 ', predicate)
        predicate = re.sub(r'(\&\&|\|\|)', r' \1 ', predicate)
        predicate = re.sub(r'\(', r' ( ', predicate)
        predicate = re.sub(r'\)', r' ) ', predicate)
        predicate = re.sub(r'\s+', ' ', predicate)
        return predicate.strip()

    def tokenize(self, predicate: str) -> List[Tuple[str, str]]:
        tokens = []
        position = 0
        length = len(predicate)

        while position < length:
            match = None
            for pattern, tag in self.token_patterns:
                regex = re.compile(pattern)
                match = regex.match(predicate, position)
                if match:
                    if tag:
                        value = match.group(0)
                        if tag == 'NUMBER':
                            if '.' in value:
                                value = float(value)
                            else:
                                value = int(value)
                        tokens.append((value, tag))
                    position = match.end()
                    break
            if not match:
                if predicate[position] == '(':
                    tokens.append(('(', 'LPAREN'))
                    position += 1
                elif predicate[position] == ')':
                    tokens.append((')', 'RPAREN'))
                    position += 1
                elif predicate[position] == ',':
                    tokens.append((',', 'COMMA'))
                    position += 1
                else:
                    raise ValueError(f"Unexpected character: {predicate[position]} at position {position}")

        # Handle cases where numbers are directly followed by identifiers
        final_tokens = []
        i = 0
        while i < len(tokens):
            if i < len(tokens) - 1 and tokens[i][1] == 'NUMBER' and tokens[i+1][1] == 'IDENTIFIER':
                final_tokens.append((tokens[i][0], 'NUMBER'))
                final_tokens.append((tokens[i+1][0], 'IDENTIFIER'))
                i += 2
            else:
                final_tokens.append(tokens[i])
                i += 1

        return final_tokens

