

def group_predicates(parsed:list):
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
