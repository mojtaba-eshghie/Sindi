

import os
import json
import random
import sys
# Set the path to your folder



def extract_random_entries(n, folder_path, output_path):
    files = [f for f in os.listdir(folder_path) if os.path.isfile(os.path.join(folder_path, f))]
    random_entries = []
    for _ in range(n):
        selected_file = random.choice(files)
        file_path = os.path.join(folder_path, selected_file)
        print(selected_file)
        with open(file_path, 'r') as f:
            data = json.load(f)

        random_entry = random.choice(data)
        # Add additional field to the entry
        random_entry["valid_output"] = False
        random_entries.append(random_entry)

    # Write all entries to a JSON file in array format
    with open(output_path, 'w') as outfile:
        json.dump(random_entries, outfile, indent=4)





if __name__ == "__main__":
    folder_path = '/Users/gustavkasche/InvPurge/InvCon+/src/output/sok/removed'
    output_path = './sok_random_sample_removed.json'
    extract_random_entries(50, folder_path, output_path)
    folder_path = '/Users/gustavkasche/InvPurge/InvCon+/src/output/sok/kept'
    output_path = './sok_random_sample_kept.json'
    extract_random_entries(50, folder_path, output_path)

    folder_path = '/Users/gustavkasche/InvPurge/InvCon+/src/output/erc20/removed'
    output_path = './erc20_random_sample_removed.json'
    extract_random_entries(50, folder_path, output_path)
    folder_path = '/Users/gustavkasche/InvPurge/InvCon+/src/output/erc20/kept'
    output_path = './erc20_random_sample_kept.json'
    extract_random_entries(50, folder_path, output_path)