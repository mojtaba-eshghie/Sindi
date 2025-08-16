from parser import parse_original
from predi import comparator
import os
import json

def find_strongest_predicate(preds: list, contract_addr: str, all_preds_dict: dict):
    """Takes a list of predicates preds and finds the strongest ones in the list"""
    before_preds = preds.copy()
    
    for first_pred in preds:
        stronger_predicate_exists = False
        for second_pred in preds:
            if '"' in first_pred or '"' in second_pred:
               continue
            result = comparator.compare(first_pred, second_pred)
            if result == 'The predicates are equivalent.':
               continue
            if result == 'The first predicate is stronger.':
               preds.remove(second_pred)
            if result == 'The second predicate is stronger.':
               preds.remove(first_pred)

    # Define file paths for removed and kept predicates
    removed_file_path = f"{output_folder}/removed/{contract_addr}-removed.json"
    kept_file_path = f"{output_folder}/kept/{contract_addr}-kept.json"
    
    # Prepare output data
    output_data = {
        "before_preds": parse_original(all_preds_dict, [before_preds]), 
        "after_preds": parse_original(all_preds_dict, [preds])
    }

    # Select the appropriate file path based on whether predicates were removed
    file_path = removed_file_path if len(preds) != len(before_preds) else kept_file_path

    # Load existing data, append new data, and write back to the file
    if os.path.exists(file_path):
        with open(file_path, "r") as file:
            existing_data = json.load(file)
    else:
        existing_data = []

    existing_data.append(output_data)
    
    with open(file_path, "w") as file:
        json.dump(existing_data, file, indent=4)

    # Error handling for unexpected increase in predicates
    if len(preds) > len(before_preds):
        print("ERROR")
        exit()
    
    return preds
