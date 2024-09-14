import unittest
from src.predi.comparator import Comparator


# Test cases for the Comparator class
test_cases = {
    'The first predicate is stronger.': [
        ("a > b", "a >= b"), 
        ("msg.sender == msg.origin && a >= b", "msg.sender == msg.origin"),
        ("msg.sender == msg.origin", "msg.sender == msg.origin || a < b"),
        ("a == 1", "a >= 1")
    ],
    'The second predicate is stronger.': [
        ("msg.sender == msg.origin || a < b", "a < b"),
        ("a > 12", "a > 13"),
        ("a + 1 <= b", "a + 1 < b"),
    ],
    'The predicates are equivalent.': [
        ("msg.sender == msg.origin", "msg.origin == msg.sender"),
        ("limiter[identity][sender]<(now-adminRate)", "limiter[identity][sender]+adminRate<now"),
        ("used[salt]==false", "!used[salt]"),
    ],
    'The predicates are not equivalent and neither is stronger.': [
        ("(a > b) && (a <= c)", "(a >= b) && (a < c)"),
        ("msg.sender != msg.origin", "a >= b"),
        ("ethBalances[_msgSender()]<=9e18", "tokens<=remainingTokens"),
        ("NS<(1days)", "NS<NE"),
        ("super.balanceOf(to)+amount<=holdLimitAmount", "balanceOf(to)+amount<=holdLimitAmount"),
        (" currentSupply+1<=MAX_SUPPLY", "currentSupply+boyzToUse.length<=MAX_SUPPLY"),
    ]
}

class TestComparator(unittest.TestCase):
    def setUp(self):
        self.comparator = Comparator()
    
    
    def test_comparator(self):
        for expected, test_data in test_cases.items():
            for data in test_data:
                result = self.comparator.compare(data[0], data[1])
                self.assertEqual(result, expected, f"Test case failed: {data[0]} vs {data[1]}")


if __name__ == '__main__':
    unittest.main()
