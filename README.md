# SSPredicates: Solidity Structural and Semantic Predicate Comparison Tool

This project provides tools to compare predicates (boolean expressions) in Solidity programming language.

## Tokenizer

The tokenizer module provides functionality to tokenize Solidity predicates into meaningful components.

### Usage

```python
from src.tokenizer import Tokenizer

tokenizer = Tokenizer()
tokens = tokenizer.tokenize("msg.sender == msg.origin")
print(tokens)
```
