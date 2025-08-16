import re

def parse_daikon_list(predicates: list):
   """Takes a list of predicates and outputs a list of parsed predicats"""
   parsed_list = []
   for expression in predicates:
      parsed = parse_daikon(expression)
      parsed_list.append(parsed)
   return parsed_list


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


def parse_original(input: dict, list):
   """Takes input dict with orignal predicates and the the parsed and outputs a list of the orignal predicates """
   new_list = []
   for preds in list:
      for entry in preds:
         new_list.append(input[entry])
   return new_list
