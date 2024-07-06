import re
from typing import List, Tuple

class Tokenizer:
    def __init__(self):
        # Define the token patterns
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
            (r'address\([^\)]*\)', 'ADDRESS'),
            (r'bytes4\([^\)]*\)', 'BYTES4'),
            (r'bytes32\([^\)]*\)', 'BYTES32'),
            (r'keccak256\([^\)]*\)', 'KECCAK256'),
            (r'\"[^\"]*\"', 'STRING_LITERAL'),
            (r'[a-zA-Z_]\w*\[.*?\]', 'ARRAY_ACCESS'),
            (r'[a-zA-Z_]\w*\.\w+\([^\)]*\)', 'METHOD_CALL'),
            (r'[a-zA-Z_]\w*\([^\)]*\)', 'FUNCTION_CALL'),
            (r'[a-zA-Z_]\w*', 'IDENTIFIER'),
            (r'\d+', 'NUMBER'),
            (r'\s+', None),  # Ignore whitespace
        ]

    
    def normalize(self, predicate: str) -> str:
        # Remove extra spaces
        predicate = re.sub(r'\s+', '', predicate)
        # Ensure consistent spacing around operators and parentheses
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
                        tokens.append((match.group(0), tag))
                    position = match.end()
                    break
            if not match:
                # Handle unexpected character case for better debugging
                raise ValueError(f"Unexpected character: {predicate[position]} at position {position}")
        return tokens