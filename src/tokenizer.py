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
            (r'\b\d+\s*(seconds|minutes|hours|days|weeks)\b', 'TIME_UNIT'),  # Handle time units
            (r'[a-zA-Z_]\w*', 'IDENTIFIER'),
            (r'\d+e\d+', 'SCIENTIFIC'),  # Handle scientific notation
            (r'\s+', None),  # Let's ignore whitespace(s)
        ]
        self.time_units = {
            'seconds': 1,
            'minutes': 60,
            'hours': 3600,
            'days': 86400,
            'weeks': 604800,
        }

    def normalize(self, predicate: str) -> str:
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
                        if tag == 'TIME_UNIT':
                            number, unit = re.match(r'(\d+)\s*(\w+)', value).groups()
                            value = str(int(number) * self.time_units[unit])
                            tag = 'INTEGER'
                        elif tag == 'SCIENTIFIC':
                            value = str(int(float(value)))
                            tag = 'INTEGER'
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

        return tokens
