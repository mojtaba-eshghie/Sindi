from src.sindi.comparator_light import ComparatorRulesOnly

C = ComparatorRulesOnly()

def test_and_subsumption():
    assert C.compare("msg.sender == msg.origin && a >= b", "msg.sender == msg.origin") == \
           "The first predicate is stronger."

def test_or_subsumption():
    assert C.compare("msg.sender == msg.origin || a < b", "a < b") == \
           "The second predicate is stronger."

def test_strict_vs_nonstrict_same_sides():
    assert C.compare("x > y", "x >= y") == "The first predicate is stronger."
    assert C.compare("(a + 1) < b", "(a + 1) <= b") == "The first predicate is stronger."

def test_eq_to_bool_forms():
    assert C.compare("used[salt] == false", "!used[salt]") == "The predicates are equivalent."

def test_move_minus_across_ineq():
    assert C.compare("balanceOf(to) <= holdLimitAmount - amount",
                     "balanceOf(to) + amount <= holdLimitAmount") == "The predicates are equivalent."

def test_numeric_bounds():
    assert C.compare("a <= 10", "a <= 20") == "The first predicate is stronger."
    assert C.compare("a > 12", "a > 13") == "The second predicate is stronger."

def test_mul_factors_rhs():
    assert C.compare("a > b * 2", "a > b * 1") == "The first predicate is stronger."
    assert C.compare("a > b / 2", "a > b") == "The second predicate is stronger."

def test_owner_rewrites_work_the_same():
    assert C.compare("isOwner()", "msg.sender == owner()") == "The predicates are equivalent."
    assert C.compare("_owner == msg.sender", "owner() == msg.sender") == "The predicates are equivalent."
