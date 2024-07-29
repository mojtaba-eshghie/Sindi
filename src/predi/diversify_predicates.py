import csv
import random
from predi.config import debug_print

def advanced_diversify_predicate(predicate):
    # Define the diversification strategies
    strategies = [
        change_logical_operators,
        negate_condition,
        add_complexity,
        simplify_condition,
        random_modification
    ]
    # Apply a random strategy for diversification
    strategy = random.choice(strategies)
    return strategy(predicate)

def change_logical_operators(predicate):
    if '&&' in predicate:
        return predicate.replace('&&', '||')
    elif '||' in predicate:
        return predicate.replace('||', '&&')
    else:
        return predicate

def negate_condition(predicate):
    if '==' in predicate:
        return predicate.replace('==', '!=')
    elif '!=' in predicate:
        return predicate.replace('!=', '==')
    elif '<=' in predicate:
        return predicate.replace('<=', '>')
    elif '>=' in predicate:
        return predicate.replace('>=', '<')
    elif '<' in predicate:
        return predicate.replace('<', '>=')
    elif '>' in predicate:
        return predicate.replace('>', '<=')
    else:
        return f"!({predicate})"

def add_complexity(predicate):
    complex_conditions = [
        f"({predicate}) || (a < b)",
        f"({predicate}) && (a > b)",
        f"({predicate}) || (msg.value > 0)",
        f"({predicate}) && (msg.value == 0)"
    ]
    return random.choice(complex_conditions)

def simplify_condition(predicate):
    if '&&' in predicate or '||' in predicate:
        return predicate.split('&&')[0].strip().split('||')[0].strip()
    return predicate

def random_modification(predicate):
    modifications = [
        f"({predicate}) && (true)",
        f"({predicate}) || (false)",
        f"({predicate}) && (msg.sender != address(0))",
        f"({predicate}) || (block.number > 0)"
    ]
    return random.choice(modifications)

def diversify_predicates(input_file, output_file):
    with open(input_file, 'r') as csvfile:
        reader = csv.DictReader(csvfile)
        fieldnames = reader.fieldnames + ['diversified_predicate']
        rows = []

        for row in reader:
            original_predicate = row['predicate']
            diversified_predicate = advanced_diversify_predicate(original_predicate)
            row['diversified_predicate'] = diversified_predicate
            rows.append(row)
            #debug_print('diversify_predicates', f"Original: {original_predicate} => Diversified: {diversified_predicate}")

    with open(output_file, 'w', newline='') as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


if __name__ == '__main__':
    input_file = 'datasets/predicate_sample_10000.csv'
    output_file = 'datasets/diversified_predicates.csv'
    diversify_predicates(input_file, output_file)
