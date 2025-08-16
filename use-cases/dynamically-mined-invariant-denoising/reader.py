import json
import sys

# import our comparator module from the parent directory
sys.path.append('../..')
import src.sindi.comparator as cp
import src.sindi.comparator_light as cp_light


import re
import time
import os


comparator = cp_light.ComparatorRulesOnly()
output_folder = ""

def parse_daikon_list(predicates: list):
   """Takes a list of predicates and outputs a list of parsed predicats"""
   parsed_list = []
   for expression in predicates:
      parsed = parse_daikon(expression)
      parsed_list.append(parsed)
   return parsed_list

def parsed_to_dict(parsed:list):
   """Takes a parsed list of predicates and creates a two dicts one where the predicates are grouped according to
    their involved variabels and one where parsed predicates are mapped to their orignal format """
   category_dict = {}
   preds_dict = {}
   for pred in parsed:
      big_key ,k, v = pred
      if big_key in category_dict:
         category_dict[big_key] = category_dict[big_key] + [v]
      else:
         category_dict[big_key] = [v]
      preds_dict[v] = k

   return category_dict, preds_dict      


def find_strongest_in_dict(preds_dict: dict, contract_addr, all_preds_dict):
   """Takes a dict of predicates and find the strongest for each one and outputs a new list of reduced preds """
   reduced_preds = []


    # Open the output file in write mode
   for pred in preds_dict.values():
      reduced_pred = find_strongest_predicate(pred,contract_addr,all_preds_dict)

      reduced_preds.append(reduced_pred)

  
   return reduced_preds   


def parse_original(input: dict, list):
   """Takes input dict with orignal predicates and the the parsed and outputs a list of the orignal predicates """
   new_list = []
   for preds in list:
      for entry in preds:
         new_list.append(input[entry])
   return new_list


def reduce_json(path: str, contract_addr: str):
   """Reduces the invariants found in the path and outputs a new json"""
   f = open(path)
   data = json.load(f)
   total_list = []
   total_list_red = []
   output_path= output_folder.replace("./output/", "").rstrip("/") + ".json"
   
   output_data: dict =  {"contract": path }
   total_parsing_time = 0
   total_reducing_time = 0
   for entry in data:
      pre_conditions = entry["preconditions"]
      post_conditions = entry["postconditions"]
      total_list += pre_conditions + post_conditions
      parsing_time_start = time.time()
      parsed_preconditions = parse_daikon_list(pre_conditions)
      parsed_postconditions = parse_daikon_list(post_conditions)
      parsing_time_end = time.time()
      total_parsing_time +=  (parsing_time_end - parsing_time_start)
      category_preconditions_dict, parsed_preconditions_dict = parsed_to_dict(parsed_preconditions )
      category_postconditions_dict, parsed_postconditions_dict = parsed_to_dict(parsed_postconditions)
      reducing_time_start = time.time()
      strongest_preconditions = find_strongest_in_dict(category_preconditions_dict, contract_addr,  parsed_preconditions_dict,)
      strongest_postconditions = find_strongest_in_dict(category_postconditions_dict, contract_addr, parsed_postconditions_dict)
      reducing_time_end = time.time()
      total_reducing_time += (reducing_time_end - reducing_time_start)
      reduced_preconditions = parse_original(parsed_preconditions_dict, strongest_preconditions)
      reduced_postconditions = parse_original(parsed_postconditions_dict, strongest_postconditions)
      entry["postconditions"] = reduced_postconditions
      entry["preconditions"] =reduced_preconditions
      total_list_red += reduced_postconditions + reduced_preconditions

   json_out = open(f"{output_folder}/{contract_addr}.json", "w")
   json.dump(data, json_out, indent=4)
   json_out.close()
   output_data = {
   "predicates_before_reduction": len(total_list),
   "predicates_after_reduction": len(total_list_red),
   "reduction_ratio": len(total_list_red) / len(total_list),
   "total_parsing_time": total_parsing_time,
   "total_reduction_time": total_reducing_time,
   "contract": path
   }

   # Check if the output file exists and load existing data

   if os.path.exists(output_path):
      print(f"+++ Output path: {output_path}")
      with open(output_path, "r") as f:
         try:
               all_output_data = json.load(f)
         except json.JSONDecodeError:
               # In case of an empty or malformed file, start with an empty list
               all_output_data = []
   else:
      all_output_data = []

   # Append the new data
   all_output_data.append(output_data)

   # Write the updated list back to the file with indentation
   with open(output_path, "w") as f:
      print(f"+++ Writing output to: {output_path}")
      json.dump(all_output_data, f, indent=4)

   



def find_strongest_predicate(preds: list, contract_addr: str, all_preds_dict: dict):
    """Takes a list of predicates preds and finds the strongest ones in the list"""
    before_preds = preds.copy()
    
    for first_pred in preds:
        stronger_predicate_exists = False
        for second_pred in preds:
            if '"' in first_pred or '"' in second_pred:
               continue
            try:
               result = comparator.compare(first_pred, second_pred)
               if result == 'The predicates are equivalent.':
                  continue
               if result == 'The first predicate is stronger.':
                  preds.remove(second_pred)
               if result == 'The second predicate is stronger.':
                  preds.remove(first_pred)
            except Exception as e:
               print('- - -' * 20)
               print(f"Error comparing predicates: {first_pred} and {second_pred}. Error: {e}")
               print('- - -' * 20)
               continue
            

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


def regex_parse(a: str,):
    """Uses regex to clean daikon expression from [...], Sum(), ori() """
    a = re.sub(r'\[\.\.\.\]', 'arrayPlaceHolder', a)
    result = re.search(r'ori\(([\w\[\]\(\)\.]+)\)', a)
    if result:
        a = result.group(1)
    
    result = re.search(r'Sum\(([\w\[\]\(\)\.]+)\)', a)
    if result:
        a = result.group(1)

    return a


def recursive_parse(a: str ,b="" ):
   """Uses regex to clean daikon expression from [...], Sum(), ori() """


   if(a.startswith("ori")):
      a = a[4:]
      a = a[0:-1]
      b += ".ori"
      a = recursive_parse(a)

   if(a.startswith("Sum")):
      a = a[4:]
      a = a[0:-1]
      b += ".sum"
      a = recursive_parse(a)

   if(a.endswith("[...]")):
      a = a[0:-5]
      b += ".spo"
      a = recursive_parse(a)
   

   return a + b


def split_expression(a:str):
   """Takes a predicates and splits into the a tuple of 
   (lefthandside of expression, relation, righthandside of expression)"""
   if ">=" in a:
      a =  re.split("(\>=)",a)
   if "<=" in a:
      a =  re.split("(\<=)",a)   
   elif "==" in a:
      a = re.split("(\==)",a)
   elif "!=" in a:
      a = re.split("(\!=)",a)   
   elif ">" in a:
      a = re.split("(\>)",a)   
   elif "<" in a:
      a = re.split("(\<)",a)

   left = a[0]
   right = a[-1]
   relation = a[1]
   return left, relation, right





def split_expression(a:str):
   """Takes a predicates and splits into the a tuple of 
   (lefthandside of expression, relation, righthandside of expression)"""
   if "elem in" in a:
      a = re.split("(elem in)", a)
   if "one of" in a:
      a = re.split("(one of)", a)  
   if ">=" in a:
      a =  re.split("(\>=)",a)
   if "<=" in a:
      a =  re.split("(\<=)",a)   
   elif "==" in a:
      a = re.split("(\==)",a)
   elif "!=" in a:
      a = re.split("(\!=)",a)   
   elif ">" in a:
      a = re.split("(\>)",a)   
   elif "<" in a:
      a = re.split("(\<)",a)

   left = a[0]
   right = a[-1]
   relation = a[1]
   return left, relation, right

def parse_daikon(a:str):
   """Takes a daikon style predicate and create a tuple of the (invovled variabels,
   orignal predicate, parsed predicate)
      
      """
   original = a
   left, delimeter, right = split_expression(a)
   left = recursive_parse(left.strip())
   right = recursive_parse(right.strip())
   if(right.isnumeric()):
      parsed_right = "Literal"
    
   else:
      parsed_right = right

   return (left+ " " + parsed_right, original,  f"{left} {delimeter} {right}")

 
def print_list(list):
   for x in list:
      print(x)


def extract_address(file_path):
    # Regular expression to match Ethereum address format
    match = re.search(r'0x[a-fA-F0-9]{40}', file_path)
    return match.group(0) if match else None      

if __name__ == "__main__":

   # pred_list = [
 
   #          "_value > 0",
   #          "_to != 0",
   #          "ori(Sum(balances[...])) > 0",
   #          "ori(Sum(balances[...])) == 5000000000000000000000000",
   #          "ori(Sum(balances[...])) one of [5000000000000000000000000]",
   #          "msg.value == 0",
   #          "msg.value one of [0]",
   #          "ori(totalSupply_) > 0",
   #          "ori(totalSupply_) == 5000000000000000000000000",
   #          "ori(totalSupply_) one of [5000000000000000000000000]",
   #          "ori(unfrozen) == true",
   #          "ori(owner) != 0"
   #        ]
   # parsed_list = parse_daikon_list(pred_list)
 

   # cat, pred = parsed_to_dict(parsed_list)

   # red = find_strongest_in_dict(cat)


   # for x in pred_list:
   #    print(x)
   # red = parse_original(pred, red)
   # print("_________________________________________________")
   # for x in red:
   #    print(x)

   # print(recursive_parse("Sum(stakingTokenBalances[...])"))
   # print(recursive_parse("ori(Sum(stakingTokenBalances[...]))"))
   # print(comparator.compare("stakingTokenBalances_spo_sum_ == stakingTokenBalances_spo_sum_ori_", "stakingTokenBalances_spo_sum_ <= stakingTokenBalances_spo_sum_ori_"))
   
   # print(comparator.compare("x < y", "x <= y"))
   ##print(comparator.compare("x > y", "x >= y"))
   path = sys.argv[1]
   output_folder = sys.argv[2]
   print(path)
   contract_addr = extract_address(path)

   reduce_json(path, contract_addr)


   # print(comparator.compare("_balances[msg.sender_ori]._ori <= _balances_spo_sum_",
   # "_balances[msg.sender]._ori < _balances_spo_sum_"))

   #  print(comparator.compare("stakingTokenBalances > stakingTokenBalances", "stakingTokenBalances != stakingTokenBalances"))
   #  print(comparator.compare("x > y" ,"x != y"))
   #  # print(comparator.compare(predicate1="exampleFunction(x) > exampleFunction(y)", predicate2="exampleFunction(x) >= exampleFunction(y)"))
#   print(comparator.compare("x - 1 < y", "x - 1 <= y"))
   #  # print(comparator.compare("x + 1 < y", "x + 1 <= y"))
   #  # print(comparator.compare("x <= y", "x == y"))
   #  # print(comparator.compare("x >= y", "x == y"))