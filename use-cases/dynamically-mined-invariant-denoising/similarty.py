from predi.comparator import Comparator 
import re 
list =[ "Sum(stakingTokenBalances[...])",
            "Sum(stakingTokenBalances[...]) ",
            "Sum(stakingTokenBalances[...])",
            "0",]


list2 = [ "ori(Sum(stakingTokenBalances[...])) >= stakingTokenSupply",
            "ori(Sum(stakingTokenBalances[...])) > stakingTokenSupply",
            "ori(Sum(stakingTokenBalances[...])) != stakingTokenSupply"]



def jaccard_index_characters(str1, str2):
    set1 = set(str1)
    set2 = set(str2)
    
    intersection = set1.intersection(set2)
    union = set1.union(set2)
    
    jaccard_index = len(intersection) / len(union)
    return jaccard_index



def regex_parse(a: str):
    """Uses regex to clean daikon expression from [...], Sum(), ori() """
    a = re.sub(r'\[\.\.\.\]', '[placeHolder]', a)
    result = re.search(r'ori\(([\w\[\]\(\)\.]+)\)', a)
    if result:
        a = result.group(1)
    
    result = re.search(r'Sum\(([\w\[\]\(\)\.]+)\)', a)
    if result:
        a = result.group(1)

    return a


def recursive_parse(a: str):
    """Uses regex to clean daikon expression from [...], Sum(), ori() """
    if(a.startswith("ori") or a.startswith("Sum")):
        a = a[4:]
        a = a[0:-1]
        a = recursive_parse(a)

    if(a.endswith("[...]")):
        a = a[0:-5]
        a += "[spreadOperator]"

    return a



# for exp in list:
#     print("___")
#     print(exp)
#     print(recursive_parse(exp))


# print(recursive_parse("ori(Sum(stakingTokenBalances[...]))"))



# for x in list:
#     for x1 in list2:
#         print(x, x1)
#         print(jaccard_index_characters(x,x1))
# cp = Comparator()
# print(cp.compare("foo$x$ == 3", "foo$x$ > 3"))


print(jaccard_index_characters("ori(_status) > 0",
            "ori(_status) == 1"))

print(jaccard_index_characters("ori(Sum(stakingTokenBalances[...])) != stakingTokenSupply",
            "Sum(stakingTokenBalances[...]) <= stakingTokenSupply"))



# print(cp.compare("_status > ori(_status)", "_status == ori(_status)"))


# print(comparator.compare("x == 1", "x == 0 || x == 2 || x == 3 || x == 1 || x == 6 || x == 7 || x == 9 || x == 8 || x == 10"))
#  print(comparator.compare("stakingTokenBalances > stakingTokenBalances", "stakingTokenBalances != stakingTokenBalances"))
#  print(comparator.compare("x > y" ,"x != y"))
#  # print(comparator.compare(predicate1="exampleFunction(x) > exampleFunction(y)", predicate2="exampleFunction(x) >= exampleFunction(y)"))
#  # print(comparator.compare("x - 1 < y", "x - 1 <= y"))
#  # print(comparator.compare("x + 1 < y", "x + 1 <= y"))
#  # print(comparator.compare("x <= y", "x == y"))
#  # print(comparator.compare("x >= y", "x == y"))