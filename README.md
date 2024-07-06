# SSPredicates: Solidity Structural and Semantic Predicate Comparison Tool

This project provides tools to compare predicates (boolean expressions) in Solidity programming language. It can determine if two predicates are equivalent, or if one is stronger than the other.
Sure, let's start by creating a `README.md` file for the repository that explains the purpose of the repository, how to set it up, and how to use it with an example. After that, we'll fill in the `main.py` to provide a command-line interface for comparing predicates.

### README.md

````markdown
# Solidity Predicate Comparison

This repository provides a tool for comparing boolean predicates in Solidity. It can determine if two predicates are equivalent, or if one is stronger than the other.

## Features

- Solidity boolean expressions
- Tokenizes and parses predicates into an Abstract Syntax Tree (AST)
- Simplify AST using symbolic mathematics
- Compare predicates for equivalence and logical strength

## Getting Started

### Prerequisites

- Python 3.8 or higher
- Install required packages using pip

```sh
pip install -r requirements.txt
```
````

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

## Project Structure

- `src/`: Contains the main logic for tokenizing, parsing, simplifying, and comparing predicates.
- `tests/`: Contains unit tests for the project.
- `main.py`: Script for comparing two predicates from the command line.

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.
