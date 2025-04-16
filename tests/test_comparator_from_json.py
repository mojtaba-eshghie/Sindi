import unittest
import json
from src.sindi.comparator import Comparator 

class TestComparatorFromJson(unittest.TestCase):

    def setUp(self):
        self.comparator = Comparator()
        # Load the JSON data
        with open('tests/test_set.json', 'r') as f: 
            self.test_cases = json.load(f)

    def test_comparator_from_json_file(self):
        for index, test_case in enumerate(self.test_cases):
            predicate1 = test_case.get('predicate1')
            predicate2 = test_case.get('predicate2')
            expected_verdict = test_case.get('verdict') 
            if predicate1 is None or predicate2 is None or expected_verdict is None:
                print(f"Skipping invalid test case at index {index}: {test_case}")
                continue

            with self.subTest(index=index, p1=predicate1, p2=predicate2):
                actual_result = self.comparator.compare(predicate1, predicate2)
                # to exactly match the output string of comparator.compare()
                self.assertEqual(actual_result, expected_verdict,
                                 f"Failed: {predicate1} vs {predicate2}")

if __name__ == '__main__':
    unittest.main()