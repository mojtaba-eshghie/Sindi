import csv
import unittest
from src.config import debug_print
from src.comparator import Comparator

class TestComparatorWithDataset(unittest.TestCase):
    def setUp(self):
        self.comparator = Comparator()

    def load_predicates(self, filename):
        with open(filename, 'r') as csvfile:
            reader = csv.DictReader(csvfile)
            predicates = [(row['predicate'], row['diversified_predicate']) for row in reader]
        return predicates

    def test_comparator_with_dataset(self):
        predicates = self.load_predicates('diversified_predicates.csv')
        for predicate1, predicate2 in predicates:
            with self.subTest(predicate1=predicate1, predicate2=predicate2):
                result = self.comparator.compare(predicate1, predicate2)
                debug_print('test_comparator', f"Comparing '{predicate1}' with '{predicate2}' resulted in: {result}")
                # Here, you might want to add specific assertions based on expected results

if __name__ == '__main__':
    unittest.main()
