import json
import os

def update_validity(filename):
    # Load data from the file
    with open(filename, 'r') as file:
        data = json.load(file)
    
    # Iterate through each entry and ask if reduction is valid
    for entry in data:
        print("Before reduction predicates:")
        for pred in entry["before_preds"]:
            print(f"  - {pred}")
        
        print("After reduction predicates:")
        for pred in entry["after_preds"]:
            print(f"  - {pred}")
        
        # Ask the user if the reduction is valid
        response = input("Is the reduction valid? (yes/no): ").strip().lower()
        if response == "yes":
            entry["valid_output"] = True
        elif response == "no":
            entry["valid_output"] = False
        else:
            print("Invalid input, keeping the current value.")

        print("\n" + "="*40 + "\n")

    # Create the new filename with "_after_eval" appended
    new_filename = f"{os.path.splitext(filename)[0]}_after_eval.json"

    # Save the updated data to the new file
    with open(new_filename, 'w') as file:
        json.dump(data, file, indent=4)
    
    print(f"File saved as {new_filename}.")

# Example usage:
update_validity('erc20_random_sample_removed.json')
