import re
from decimal import Decimal

class Rewriter:
    """
    Canonicalizes Solidity predicate strings before tokenization/parsing,
    implementing the rewrite rules in Table \\ref{tab:canonicalized}.
    """

    _HEX_ZERO_ADDR = re.compile(r"\b0x0{40}\b", flags=re.IGNORECASE)

    # Ether/gwei/wei (simple forms like "2 ether", "5 gwei", "100 wei")
    _ETHER_SIMPLE = re.compile(r"\b(\d+)\s*(ether|gwei|wei)\b", flags=re.IGNORECASE)
    # Scientific "1e18 wei"
    _WEI_SCI = re.compile(r"\b(\d+e\d+)\s*wei\b", flags=re.IGNORECASE)
    # Power form "10**18 wei"
    _WEI_POW10 = re.compile(r"\b10\s*\*\*\s*(\d+)\s*wei\b", flags=re.IGNORECASE)

    # now -> block.timestamp
    _NOW = re.compile(r"\bnow\b")

    # OZ Context
    _MSG_SENDER_FN = re.compile(r"\b_msgSender\s*\(\s*\)")

    # isOwner/isAdmin
    _IS_OWNER = re.compile(r"\bisOwner\s*\(\s*\)")
    _IS_ADMIN = re.compile(r"\bisAdmin\s*\(\s*\)")

    # Bare _owner / owner -> owner()
    _BARE__OWNER = re.compile(r"(?<!\.)\b_owner\b")
    _BARE_OWNER = re.compile(r"(?<!\.)\bower\b(?!\s*\()")

    # Interface ID literals
    _IFACE_MAP = {
        re.compile(r"\b0x36372b07\b", re.IGNORECASE): "type(IERC20).interfaceId",
        re.compile(r"\b0x80ac58cd\b", re.IGNORECASE): "type(IERC721).interfaceId",
        re.compile(r"\b0xd9b67a26\b", re.IGNORECASE): "type(IERC1155).interfaceId",
    }
    # Normalize any spaced form of type(IERCX).interfaceId to a single canonical text
    _TYPE_IFACE_NORMALIZER = re.compile(
        r"\btype\s*\(\s*(IERC20|IERC721|IERC1155)\s*\)\s*\.\s*interfaceId\b"
    )

    # SafeMath (static calls)
    _SM_ADD = re.compile(r"\bSafeMath\s*\.\s*add\s*\(\s*([^,()]+?)\s*,\s*([^)]+?)\s*\)")
    _SM_SUB = re.compile(r"\bSafeMath\s*\.\s*sub\s*\(\s*([^,()]+?)\s*,\s*([^)]+?)\s*\)")
    _SM_MUL = re.compile(r"\bSafeMath\s*\.\s*mul\s*\(\s*([^,()]+?)\s*,\s*([^)]+?)\s*\)")
    _SM_DIV = re.compile(r"\bSafeMath\s*\.\s*div\s*\(\s*([^,()]+?)\s*,\s*([^)]+?)\s*\)")
    _SM_MOD = re.compile(r"\bSafeMath\s*\.\s*mod\s*\(\s*([^,()]+?)\s*,\s*([^)]+?)\s*\)")

    # SafeMath (extension methods) — works with a.balances[idx].add(x) etc.
    _EXT_ADD = re.compile(r"(\b[A-Za-z_]\w*(?:\[[^\]]+\])?(?:\.[A-Za-z_]\w*(?:\[[^\]]+\])?)*)\s*\.s*add\s*\(\s*([^)]+?)\s*\)")
    _EXT_SUB = re.compile(r"(\b[A-Za-z_]\w*(?:\[[^\]]+\])?(?:\.[A-Za-z_]\w*(?:\[[^\]]+\])?)*)\s*\.s*sub\s*\(\s*([^)]+?)\s*\)")
    _EXT_MUL = re.compile(r"(\b[A-Za-z_]\w*(?:\[[^\]]+\])?(?:\.[A-Za-z_]\w*(?:\[[^\]]+\])?)*)\s*\.s*mul\s*\(\s*([^)]+?)\s*\)")
    _EXT_DIV = re.compile(r"(\b[A-Za-z_]\w*(?:\[[^\]]+\])?(?:\.[A-Za-z_]\w*(?:\[[^\]]+\])?)*)\s*\.s*div\s*\(\s*([^)]+?)\s*\)")
    _EXT_MOD = re.compile(r"(\b[A-Za-z_]\w*(?:\[[^\]]+\])?(?:\.[A-Za-z_]\w*(?:\[[^\]]+\])?)*)\s*\.s*mod\s*\(\s*([^)]+?)\s*\)")

    _ETH_MULT = {"ether": 10**18, "gwei": 10**9, "wei": 1}

    def apply(self, s: str) -> str:
        # 1) Trivial textual normalizations
        s = self._NOW.sub("block.timestamp", s)
        s = self._MSG_SENDER_FN.sub("msg.sender", s)
        s = self._IS_OWNER.sub("msg.sender == owner()", s)
        s = self._IS_ADMIN.sub("msg.sender == admin", s)

        # 2) Zero address
        s = self._HEX_ZERO_ADDR.sub("address(0)", s)

        # 3) Interface IDs (hex -> type(...).interfaceId)
        for pat, repl in self._IFACE_MAP.items():
            s = pat.sub(repl, s)
        # Normalize any spaced `type(IERCX).interfaceId`
        s = self._TYPE_IFACE_NORMALIZER.sub(lambda m: f"type({m.group(1)}).interfaceId", s)

        # 4) Owner forms
        s = self._BARE__OWNER.sub("owner()", s)
        s = self._BARE_OWNER.sub("owner()", s)

        # 5) Ether unit canonicalization to raw wei integer
        s = self._canon_ether_units(s)

        # 6) SafeMath → operators (iterate a few times to catch nested cases)
        for _ in range(4):
            before = s
            # Static style
            s = self._SM_ADD.sub(r"(\1) + (\2)", s)
            s = self._SM_SUB.sub(r"(\1) - (\2)", s)
            s = self._SM_MUL.sub(r"(\1) * (\2)", s)
            s = self._SM_DIV.sub(r"(\1) / (\2)", s)
            s = self._SM_MOD.sub(r"(\1) % (\2)", s)
            # Extension style
            s = re.sub(r"(\b[A-Za-z_]\w*(?:\[[^\]]+\])?(?:\.[A-Za-z_]\w*(?:\[[^\]]+\])?)*)\s*\.\s*add\s*\(\s*([^)]+?)\s*\)", r"(\1) + (\2)", s)
            s = re.sub(r"(\b[A-Za-z_]\w*(?:\[[^\]]+\])?(?:\.[A-Za-z_]\w*(?:\[[^\]]+\])?)*)\s*\.\s*sub\s*\(\s*([^)]+?)\s*\)", r"(\1) - (\2)", s)
            s = re.sub(r"(\b[A-Za-z_]\w*(?:\[[^\]]+\])?(?:\.[A-Za-z_]\w*(?:\[[^\]]+\])?)*)\s*\.\s*mul\s*\(\s*([^)]+?)\s*\)", r"(\1) * (\2)", s)
            s = re.sub(r"(\b[A-Za-z_]\w*(?:\[[^\]]+\])?(?:\.[A-Za-z_]\w*(?:\.[A-Za-z_]\w*)?)*)\s*\.\s*div\s*\(\s*([^)]+?)\s*\)", r"(\1) / (\2)", s)
            s = re.sub(r"(\b[A-Za-z_]\w*(?:\[[^\]]+\])?(?:\.[A-Za-z_]\w*(?:\[[^\]]+\])?)*)\s*\.\s*mod\s*\(\s*([^)]+?)\s*\)", r"(\1) % (\2)", s)
            if s == before:
                break

        return s

    # ----- helpers -----

    def _canon_ether_units(self, s: str) -> str:
        # 10**K wei  → integer
        def _pow10_to_int(m):
            k = int(m.group(1))
            return str(10 ** k)

        s = self._WEI_POW10.sub(_pow10_to_int, s)

        # 1e18 wei → integer
        def _sci_to_int(m):
            n = m.group(1)
            return str(int(Decimal(n)))

        s = self._WEI_SCI.sub(_sci_to_int, s)

        # N ether/gwei/wei → integer wei
        def _simple_to_wei(m):
            n = int(m.group(1))
            unit = m.group(2).lower()
            return str(n * self._ETH_MULT[unit])

        s = self._ETHER_SIMPLE.sub(_simple_to_wei, s)
        return s