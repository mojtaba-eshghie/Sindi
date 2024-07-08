import csv
import unittest
from src.config import debug_print
from src.comparator import Comparator

class TestComparatorWithDataset(unittest.TestCase):
    def setUp(self):
        self.comparator = Comparator()
        self.success_count = 0
        self.failure_count = 0

    def load_predicates(self, filename):
        with open(filename, 'r') as csvfile:
            reader = csv.DictReader(csvfile)
            predicates = [(row['predicate'], row['diversified_predicate']) for row in reader]
        return predicates

    def test_comparator_with_dataset(self):
        predicates = self.load_predicates('datasets/diversified_predicates.csv')
        for index, (predicate1, predicate2) in enumerate(predicates):
            with self.subTest(index=index, predicate1=predicate1, predicate2=predicate2):
                
                try:
                    debug_print(f"{predicate1}\n- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - \n{predicate2}", type_='info')
                    result = self.comparator.compare(predicate1, predicate2)
                    debug_print(f">>> Comparing predicates at index {index} resulted in: {result}", type_='neutral')
                    debug_print('=' * 140)
                    debug_print('=' * 140)
                    self.success_count += 1
                except Exception as e:
                    debug_print(f"Exception occurred at index {index} while comparing '{predicate1}' with '{predicate2}': {e}", type_='exception')
                    debug_print('=' * 140)
                    debug_print('=' * 140)
                    self.failure_count += 1

    def tearDown(self):
        print(f"Total successes: {self.success_count}")
        print(f"Total failures: {self.failure_count}")

if __name__ == '__main__':
    unittest.main()
