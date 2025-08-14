from src.sindi.comparator import Comparator
import pytest

# write a simple test to check if the comparator works as expected
def test_comparator():
    comparator = Comparator()
    
    # Example predicates to compare
    predicate1 = "(a+1) > b / 2"
    predicate2 = "(a+1) > b"
    
    # Compare the predicates
    result = comparator.compare(predicate1, predicate2)
    
    # Check if the result is as expected
    assert result == "The second predicate is stronger."  # Adjust based on your comparator logic
    