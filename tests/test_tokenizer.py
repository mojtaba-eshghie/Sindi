import unittest
import csv
import os
from src.tokenizer import Tokenizer

DATASET = 'predicate_sample_10000.csv'


class TestTokenizer(unittest.TestCase):
    def setUp(self):
        self.tokenizer = Tokenizer()

    
    def test_simple_predicate(self):
        predicate = "msg.sender == msg.origin"
        expected_tokens = [
            ('msg.sender', 'MSG_SENDER'),
            ('==', 'EQUAL'),
            ('msg.origin', 'MSG_ORIGIN')
        ]
        self.assertEqual(self.tokenizer.tokenize(predicate), expected_tokens)

    def test_complex_predicate(self):
        predicate = "require(msg.sender != msg.origin && balance >= 100)"
        expected_tokens = [
            ('require', 'REQUIRE'),
            ('(', 'LPAREN'),
            ('msg.sender', 'MSG_SENDER'),
            ('!=', 'NOT_EQUAL'),
            ('msg.origin', 'MSG_ORIGIN'),
            ('&&', 'AND'),
            ('balance', 'IDENTIFIER'),
            ('>=', 'GREATER_EQUAL'),
            ('100', 'NUMBER'),
            (')', 'RPAREN')
        ]
        self.assertEqual(self.tokenizer.tokenize(predicate), expected_tokens)

    def test_arithmetic_predicate(self):
        predicate = "c/a==b"
        expected_tokens = [
            ('c', 'IDENTIFIER'),
            ('/', 'DIVIDE'),
            ('a', 'IDENTIFIER'),
            ('==', 'EQUAL'),
            ('b', 'IDENTIFIER')
        ]
        self.assertEqual(self.tokenizer.tokenize(predicate), expected_tokens)


    def test_normalize_complex_predicate(self):
        predicate = "require( msg.sender!=msg.origin && a>=b )"
        normalized_predicate = "require ( msg.sender != msg.origin && a >= b )"
        self.assertEqual(self.tokenizer.normalize(predicate), normalized_predicate)


    def test_array_access_predicate(self):
        predicate = "value<=_balances[from]"
        expected_tokens = [
            ('value', 'IDENTIFIER'),
            ('<=', 'LESS_EQUAL'),
            ('_balances[from]', 'ARRAY_ACCESS')
        ]
        self.assertEqual(self.tokenizer.tokenize(predicate), expected_tokens)

    def test_function_call_predicate(self):
        predicate = "value<=allowance(from,to)"
        expected_tokens = [
            ('value', 'IDENTIFIER'),
            ('<=', 'LESS_EQUAL'),
            ('allowance(from,to)', 'FUNCTION_CALL')
        ]
        self.assertEqual(self.tokenizer.tokenize(predicate), expected_tokens)

    '''
    def test_tokenize_dataset_predicates(self):
        dataset_path = os.path.join(os.path.dirname(__file__), 'datasets', DATASET)
        with open(dataset_path, newline='', encoding='utf-8') as csvfile:
            reader = csv.reader(csvfile)
            for index, row in enumerate(reader):
                # Assuming the predicate is always in the first column
                predicate = row[1]
                print(f"({index}) Tokenizing predicate: {predicate}")
                # Attempt to tokenize the predicate
                try:
                    self.tokenizer.tokenize(predicate)
                except Exception as e:
                    # print row index and predicate
                    self.fail(f"Tokenization failed for predicate '{predicate}' with exception {e}")
    '''
    
if __name__ == '__main__':
    unittest.main()
