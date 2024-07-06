import sys
from src.comparator import Comparator

def main():
    if len(sys.argv) != 3:
        print("Usage: python main.py <predicate1> <predicate2>")
        return

    predicate1 = sys.argv[1]
    predicate2 = sys.argv[2]

    comparator = Comparator()
    result = comparator.compare(predicate1, predicate2)
    print(result)

if __name__ == "__main__":
    main()
