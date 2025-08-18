// SPDX-License-Identifier: MIT
pragma solidity ^0.8.16;

// import "@openzeppelin/contracts-upgradeable/security/ReentrancyGuardUpgradeable.sol";
// import "@openzeppelin/contracts/token/ERC721/IERC721.sol";
// import "@openzeppelin/contracts/utils/Strings.sol";
import "./Guardian/Erc721LockRegistry.sol";
import "./OPR/upgradeable/DefaultOperatorFiltererUpgradeable.sol";
import "./interfaces/IBreedingInfoV2.sol";

contract KeungzGenesis is
    ERC721x,
    DefaultOperatorFiltererUpgradeable,
    IBreedingInfoV2
{
    uint256 public MAX_SUPPLY;

    string public baseTokenURI;
    string public tokenURISuffix;
    string public tokenURIOverride;

    // ============ vvv V5: UNUSED vvv ===============
    mapping(address => bool) public whitelistedMarketplaces;
    mapping(address => bool) public blacklistedMarketplaces;
    uint8 public marketplaceRestriction;
    // ============ ^^^ V5: UNUSED ^^^ ===============

    // ============ vvv V7: UNUSED vvv ============
    mapping(uint256 => mapping(address => uint256))
        public tokenOwnershipsLengths; // tokenId => address => [token] holded how long by [address] in seconds
    mapping(address => address[]) public addressAssociations;
    mapping(address => mapping(address => bool)) public addressAssociationsMap; // address => association

    event MarketplaceWhitelisted(address indexed market, bool whitelisted);
    event MarketplaceBlacklisted(address indexed market, bool blacklisted);

    mapping(uint256 => mapping(address => uint256)) tolMinusOffset; // tokenId => address => tol offset in seconds
    bool tolOffsetSealed;

    // V5
    bool public canStake;
    mapping(uint256 => uint256) public tokensLastStakedAt; // tokenId => timestamp
    event Stake(uint256 tokenId, address by, uint256 stakedAt);
    event Unstake(
        uint256 tokenId,
        address by,
        uint256 stakedAt,
        uint256 unstakedAt
    );
    // ============ ^^^ V7: UNUSED ^^^ ============

    // V6
    /* V7: Unused */
    mapping(uint256 => bool) public lockedTokenIds; // tokenId => locked
    mapping(address => bool) public lockedTransferToAddresses; // address => locked
    /* V7: Unused */
    mapping(address => bool) public isRescuing;

    // V7
    mapping(uint256 => uint256) public holdingSinceOverride; // tokenId => holdingSince

    function initialize(string memory baseURI) public initializer {
        ERC721x.__ERC721x_init("Keungz Genesis", "KZG");
        baseTokenURI = baseURI;
        MAX_SUPPLY = 432;
    }

    function initializeV2() public onlyOwner reinitializer(2) {
        DefaultOperatorFiltererUpgradeable.__DefaultOperatorFilterer_init();
    }

    // =============== TOKEN TRANSFER RECORD ===============
    function oldGetTokenOwnershipLengthOfOwner(
        uint256 tokenId,
        bool withAssociation
    ) public view returns (uint256) {
        TokenOwnership memory ship = explicitOwnershipOf(tokenId);
        address owner = ship.addr;
        uint256 holdingLength = block.timestamp - ship.startTimestamp;
        holdingLength += tokenOwnershipsLengths[tokenId][owner];
        holdingLength -= tolMinusOffset[tokenId][owner];
        if (withAssociation) {
            address[] storage assoArray = addressAssociations[owner];

            for (uint256 i = 0; i < assoArray.length; i++) {
                address asso = assoArray[i];
                // check for mutuals
                if (addressAssociationsMap[asso][owner]) {
                    holdingLength += tokenOwnershipsLengths[tokenId][asso];
                    holdingLength -= tolMinusOffset[tokenId][asso];
                }
            }
        }
        return holdingLength;
    }
    
    function oldGetTokenOwnershipLengths(uint256[] calldata tokenIds)
        public
        view
        returns (uint256[] memory)
    {
        uint256[] memory ret = new uint256[](tokenIds.length);
        for (uint256 i = 0; i < tokenIds.length; i++) {
            uint256 tokenId = tokenIds[i];
            ret[i] = oldGetTokenOwnershipLengthOfOwner(tokenId, true);
        }
        return ret;
    }


    function getHoldingSince(uint256 tokenId) internal view returns (uint256) {
        if (holdingSinceOverride[tokenId] > 0) {
            return holdingSinceOverride[tokenId];
        }
        return explicitOwnershipOf(tokenId).startTimestamp;
    }

    function getHoldingSinceExternal(uint256 tokenId) external view returns (uint256) {
        if (holdingSinceOverride[tokenId] > 0) {
            return holdingSinceOverride[tokenId];
        }
        return explicitOwnershipOf(tokenId).startTimestamp;
    }

    function getHoldingLength(uint256 tokenId) internal view returns (uint256) {
        return block.timestamp - getHoldingSince(tokenId);
    }

    function getTokenOwnershipLength(uint256 tokenId)
        public
        view
        returns (uint256)
    {
        return getHoldingLength(tokenId);
    }

    function getTokenOwnershipLengths(uint256[] calldata tokenIds)
        public
        view
        returns (uint256[] memory)
    {
        uint256[] memory ret = new uint256[](tokenIds.length);
        for (uint256 i = 0; i < tokenIds.length; i++) {
            uint256 tokenId = tokenIds[i];
            ret[i] = getTokenOwnershipLength(tokenId);
        }
        return ret;
    }

    function overrideHoldingSince(
        uint256[] calldata tokenIds,
        uint256[] calldata timestamps
    ) external onlyOwner {
        for (uint256 i = 0; i < tokenIds.length; i++) {
            holdingSinceOverride[tokenIds[i]] = timestamps[i];
        }
    }

    function transferFrom(
        address _from,
        address _to,
        uint256 _tokenId
    ) public virtual override(ERC721x) onlyAllowedOperator(_from) {
        // require(!lockedTokenIds[_tokenId], "tokenId locked");
        require(!lockedTransferToAddresses[_to], "'to' locked");
        holdingSinceOverride[_tokenId] = 0;
        super.transferFrom(_from, _to, _tokenId);
    }

    function safeTransferFrom(
        address from,
        address to,
        uint256 tokenId,
        bytes memory data
    ) public virtual override(ERC721x) onlyAllowedOperator(from) {
        // require(!lockedTokenIds[tokenId], "tokenId locked");
        require(!lockedTransferToAddresses[to], "'to' locked");
        holdingSinceOverride[tokenId] = 0;
        super.safeTransferFrom(from, to, tokenId, data);
    }

    function keepTOLTransferFrom(
        address from,
        address to,
        uint256 tokenId
    ) public {
        require(
            ownerOf(tokenId) == from,
            "Only token owner can do keep TOL transfer"
        );
        require(msg.sender == from, "Sender must be from token owner");
        require(from != to, "From and To must be different");

        if (holdingSinceOverride[tokenId] == 0) {
            uint256 holdingSince = explicitOwnershipOf(tokenId).startTimestamp;
            holdingSinceOverride[tokenId] = holdingSince;
        }

        super.transferFrom(from, to, tokenId);
    }

    // =============== BASE URI ===============

    function compareStrings(string memory a, string memory b)
        public
        pure
        returns (bool)
    {
        return keccak256(abi.encodePacked(a)) == keccak256(abi.encodePacked(b));
    }

    function _baseURI() internal view virtual override returns (string memory) {
        return baseTokenURI;
    }

    function tokenURI(uint256 _tokenId)
        public
        view
        override(ERC721AUpgradeable, IERC721AUpgradeable)
        returns (string memory)
    {
        if (bytes(tokenURIOverride).length > 0) {
            return tokenURIOverride;
        }
        return string.concat(super.tokenURI(_tokenId), tokenURISuffix);
    }

    function setBaseURI(string calldata baseURI) external onlyOwner {
        baseTokenURI = baseURI;
    }

    function setTokenURISuffix(string calldata _tokenURISuffix)
        external
        onlyOwner
    {
        if (compareStrings(_tokenURISuffix, "!empty!")) {
            tokenURISuffix = "";
        } else {
            tokenURISuffix = _tokenURISuffix;
        }
    }

    function setTokenURIOverride(string calldata _tokenURIOverride)
        external
        onlyOwner
    {
        if (compareStrings(_tokenURIOverride, "!empty!")) {
            tokenURIOverride = "";
        } else {
            tokenURIOverride = _tokenURIOverride;
        }
    }

    // =============== IBreedingInfoV2 ===============

    function ownerOfGenesis(uint256 tokenId) external view returns (address) {
        return ownerOf(tokenId);
    }

    // =============== Transfer Lock ===============
    function setTransferToLocked(address addr, bool locked) external onlyOwner {
        lockedTransferToAddresses[addr] = locked;
    }
}
