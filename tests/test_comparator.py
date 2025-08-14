import json
from pathlib import Path
import pytest
from src.sindi.comparator import Comparator

# --- Test Case Loading ---

def load_test_cases():
    """
    Loads and parses test cases from the JSON file.
    The JSON file is expected to be a list containing one dictionary.
    The dictionary's keys are the expected outcomes (e.g., "The first predicate is stronger.").
    The values are lists of predicate pairs to be compared.
    """
    # Build a reliable path to the JSON file, no matter where pytest is run from
    current_dir = Path(__file__).parent
    test_set_path = current_dir / "comparator_test_set.json"

    test_cases = []
    with open(test_set_path) as f:
        # The JSON is a list with one dictionary inside
        data = json.load(f)[0]
        # Iterate over each category (e.g., "The first predicate is stronger.")
        for expected_outcome, predicate_pairs in data.items():
            # Iterate over each pair of predicates in the category
            for pair in predicate_pairs:
                if len(pair) == 2:
                    p1, p2 = pair
                    # Create a pytest parameter set with an informative ID
                    test_cases.append(pytest.param(p1, p2, expected_outcome, id=f"{p1} vs {p2}"))
    return test_cases

# --- Test Function ---

@pytest.mark.parametrize("predicate1, predicate2, expected", load_test_cases())
def test_comparator_with_json_data(predicate1, predicate2, expected):
    """
    Tests the Comparator using data loaded from comparator_test_set.json.
    """
    # Initialize the comparator
    comparator = Comparator()

    # I'm assuming your Comparator has a `compare` method that takes two
    # predicates and returns a string result like the keys in your JSON file.
    # If it returns something else, you may need to adjust the assertion.
    actual_result = comparator.compare(predicate1, predicate2)

    # Assert that the actual result from the comparator matches the expected outcome
    assert actual_result == expected