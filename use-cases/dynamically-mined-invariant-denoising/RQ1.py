import json
import pandas as pd
import matplotlib.pyplot as plt
import numpy as np


def label_selector(file_path:str):
    if file_path == 'erc20':
        return "ERC20"
    else:
        return "SoK"


def RQ1(file_path):

    # Load data from JSON file
    with open(file_path, 'r') as f:
        data = json.load(f)

    file_path = file_path.removeprefix("./")
    file_path = file_path.removesuffix(".json")
    # Flatten nested JSON structure
    flat_data = []
    for item in data:
        if isinstance(item, list):  # Handle list of lists
            flat_data.extend(item)
        else:
            flat_data.append(item)

    # Convert to DataFrame
    df = pd.DataFrame(flat_data)

    # Calculate total and average times
    total_parsing_time = df['total_parsing_time'].sum()
    total_reduction_time = df['total_reduction_time'].sum()
    average_parsing_time = df['total_parsing_time'].mean()
    average_reduction_time = df['total_reduction_time'].mean()
    average_reduction_ratio = round(df['reduction_ratio'].mean(),2)
    predicates_removed = df["predicates_before_reduction"].sum() - df["predicates_after_reduction"].sum()
    average_predicates_removed = predicates_removed / len(df)

    # Print calculated values
    print(f"Total Parsing Time: {total_parsing_time}")
    print(f"Total Reduction Time: {total_reduction_time}")
    print(f"Average Parsing Time: {average_parsing_time}")
    print(f"Average Reduction Time: {average_reduction_time}")
    print(f"Average Reduction Ratio: {average_reduction_ratio}")
    print(f"Average predicates removed: {average_predicates_removed}")
    print(f"Total predicates removed: {predicates_removed}")

    # Generate histogram for reduction ratio with custom ticks and no grid
    num_bins = 4
    counts, bins, patches = plt.hist(df['reduction_ratio'], bins=num_bins, edgecolor='black', alpha=0.8, align='mid')

    # Set the x-ticks to be at the center of each bin
    bin_centers = 0.5 * (bins[1:] + bins[:-1])
    plt.xticks(bin_centers, [f"{center:.2f}" for center in bin_centers])



    # Set the x-ticks to be at the center of each bin, with 0.65 instead of 0.66
    bin_centers = 0.5 * (bins[1:] + bins[:-1])
    custom_ticks = [f"{center:.2f}" for center in bin_centers]
    if file_path == 'sok':
        custom_ticks[0] = '0.65'  # Change the first tick to 0.65

    plt.xticks(bin_centers, custom_ticks)

    # Set labels and title
    plt.xlabel('Reduction Ratio',  fontsize=14)
    plt.ylabel('Frequency' ,fontsize=14)
    # plt.title(f'Histogram of Reduction Ratios {label_selector(file_path)} for Smart Contract', fontsize=16)

    # Turn off the grid
    plt.grid(False)

    # Save and show the plot
    plt.savefig(f'reduction_ratio_histogram_{file_path}.pdf', format='pdf', dpi=300)
    plt.clf()


if __name__ == "__main__":
    RQ1("./erc20.json")
    # print("_______________________________________________________________")
    RQ1("./sok.json")