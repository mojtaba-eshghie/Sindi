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
            (r'\&', 'BITWISE_AND'),
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

            # --- Handle 10**k wei as one numeric token (fallback if string rewriter didn't run) ---
            (r'(?i)\b10\s*\*\*\s*(\d+)\s*wei\b', 'WEI_POW10'),

            # ---- Numbers (order matters: scientific before float/int) ----
            (r'\b\d(?:_?\d)*(?:\.\d(?:_?\d)*)?[eE][+-]?\d+(?:_?\d)*\b', 'SCIENTIFIC'),
            (r'\b\d(?:_?\d)*\.\d(?:_?\d)*\b', 'FLOAT'),
            (r'\b\d(?:_?\d)*\b', 'INTEGER'),

            (r'\btrue\b', 'TRUE'),
            (r'\bfalse\b', 'FALSE'),
            (r'0x[0-9a-fA-F]{40}', 'ADDRESS_LITERAL'),
            (r'0x[0-9a-fA-F]+', 'BYTES_LITERAL'),
            (r'\b\d(?:_?\d)*\s*(seconds|minutes|hours|days|weeks)\b', 'TIME_UNIT'),
            (r'[a-zA-Z_]\w*', 'IDENTIFIER'),
            (r'\s+', None),
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
                            num, unit = re.match(r'(\d(?:_?\d)*)\s*(\w+)', value).groups()
                            num = int(num.replace('_', ''))
                            value = str(num * self.time_units[unit])
                            tag = 'INTEGER'

                        elif tag == 'WEI_POW10':
                            # Turn "10**18 wei" into a big integer literal token
                            m = re.match(r'(?i)\b10\s*\*\*\s*(\d+)\s*wei\b', value)
                            k = int(m.group(1)) if m else 0
                            value = str(10 ** k)
                            tag = 'INTEGER'

                        elif tag in ('SCIENTIFIC', 'FLOAT', 'INTEGER'):
                            # Strip underscores from numeric tokens
                            value = value.replace('_', '')
                            if tag == 'SCIENTIFIC':
                                # Normalize to INTEGER by evaluating (safe enough for our use)
                                # Example: 9e18 -> 9000000000000000000
                                try:
                                    from decimal import Decimal
                                    value = str(int(Decimal(value)))
                                    tag = 'INTEGER'
                                except Exception:
                                    # Fall back to float path if Decimal fails
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
