# SPi: Solidity Semantic Predicate Comparison Tool

SPi [spaɪ], the Solidity Predicate Inspector, is a tool for comparing two boolean predicates written in Solidity, a smart contract programming language. SPi determines if two predicates are equivalent or if one is stronger than the other.

## Features

- Tokenizes and parses Solidity predicates into an Abstract Syntax Tree (AST)
- Simplify AST using symbolic mathematics
- Compare predicates for equivalence and logical strength

## Getting Started

### Prerequisites

- Python 3.8 or higher
- Install required packages using pip

```sh
pip install -r requirements.txt
```

### Running the Tests

To ensure everything is set up correctly, run the unit tests:

```sh
python -m unittest discover -s tests
```

### Usage

You can compare two predicates using the `main.py` script. Here's an example:

```sh
python main.py "msg.sender == msg.origin" "a < b"
```

This will output whether the predicates are equivalent, or which one is stronger.

## Example

```sh
$ python main.py "msg.sender == msg.origin" "msg.origin == msg.sender"
The predicates are equivalent.

$ python main.py "msg.sender == msg.origin && a >= b" "msg.sender == msg.origin"
The first predicate is stronger.

$ python main.py "msg.sender == msg.origin || a < b" "a < b"
The second predicate is stronger.
```
