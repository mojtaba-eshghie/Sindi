# PreDi: Symbolic Solidity Predicate Difference Tool

PreDi is a tool to compare two predicates written in Solidity, the smart contract programming language. PreDi determines if two predicates are equivalent or if one is stronger than the other.

## Features

- Tokenizes and parses each Solidity predicate into an Abstract Syntax Tree (AST)
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
