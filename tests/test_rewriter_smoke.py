import pytest
from src.sindi.rewriter import Rewriter

R = Rewriter().apply

def test_now_to_block_timestamp():
    assert R("now >= 0 && a > b") == "block.timestamp >= 0 && a > b"

def test_msgsender_function_to_property():
    assert R("_msgSender() == admin") == "msg.sender == admin"

def test_isOwner_and_isAdmin_rewrites():
    assert R("isOwner() && x > 0") == "msg.sender == owner() && x > 0"
    assert R("isAdmin() || halted") == "msg.sender == admin || halted"

def test_owner_forms():
    # Bare names become owner()
    assert R("_owner == msg.sender") == "owner() == msg.sender"
    assert R("owner == msg.sender") == "owner() == msg.sender"
    # Do not touch member access like foo.owner
    assert R("foo.owner == msg.sender") == "foo.owner == msg.sender"
    # Do not touch already-a-call
    assert R("owner() == msg.sender") == "owner() == msg.sender"

def test_zero_address_hex_to_address0():
    assert R("to != 0x0000000000000000000000000000000000000000") == "to != address(0)"

def test_interface_ids_hex_to_type_interfaceId_and_normalize_type_form():
    assert R("x == 0x80ac58cd") == "x == type(IERC721).interfaceId"
    assert R("y == 0x36372b07") == "y == type(IERC20).interfaceId"
    assert R("z == 0xd9b67a26") == "z == type(IERC1155).interfaceId"
    # normalize spaced form
    assert R("x == type ( IERC721 ) . interfaceId") == "x == type(IERC721).interfaceId"

def test_ether_units_to_raw_wei_integers():
    assert R("msg.value >= 1 ether") == "msg.value >= 1000000000000000000"
    assert R("fee == 5 gwei") == "fee == 5000000000"
    assert R("dust < 100 wei") == "dust < 100"

def test_wei_scientific_and_pow10():
    assert R("x == 1e18 wei") == "x == 1000000000000000000"
    assert R("y == 10**18 wei") == "y == 1000000000000000000"

def test_safemath_static_and_extension_styles():
    # Static
    assert R("SafeMath.add(a,b) > c") == "(a) + (b) > c"
    assert R("SafeMath.sub(a,b) >= 0") == "(a) - (b) >= 0"
    assert R("SafeMath.mul(x,y) == z") == "(x) * (y) == z"
    assert R("SafeMath.div(p,q) <= r") == "(p) / (q) <= r"
    assert R("SafeMath.mod(u,v) != 0") == "(u) % (v) != 0"
    # Extension (with indexing and member chains)
    assert R("balances[user].add(amount) <= cap") == "(balances[user]) + (amount) <= cap"
    assert R("supply.sub(burnt) == live") == "(supply) - (burnt) == live"
    assert R("price.mul(qty) >= min") == "(price) * (qty) >= min"
    assert R("sum.div(n) == avg") == "(sum) / (n) == avg"
    assert R("a.mod(m) == 0") == "(a) % (m) == 0"

def test_idempotent_application():
    s = "isOwner() && _msgSender() != 0x0000000000000000000000000000000000000000 && msg.value >= 1 ether"
    once = R(s)
    twice = R(once)
    assert once == twice
