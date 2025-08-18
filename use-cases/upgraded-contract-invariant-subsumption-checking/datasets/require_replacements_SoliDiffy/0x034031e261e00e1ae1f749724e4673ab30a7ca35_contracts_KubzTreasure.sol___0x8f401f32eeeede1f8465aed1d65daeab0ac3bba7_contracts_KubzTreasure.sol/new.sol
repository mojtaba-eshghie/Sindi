// SPDX-License-Identifier: MIT
pragma solidity ^0.8.16;
import "@openzeppelin/contracts/utils/Strings.sol";
import "@openzeppelin/contracts/utils/math/Math.sol";
import "@openzeppelin/contracts/utils/cryptography/ECDSA.sol";
import "@openzeppelin/contracts/utils/structs/EnumerableSet.sol";
import "@openzeppelin/contracts/token/ERC721/IERC721.sol";
import "@openzeppelin/contracts-upgradeable/security/ReentrancyGuardUpgradeable.sol";
import "./Guardian/Erc721LockRegistry.sol";
import "./OPR/upgradeable/DefaultOperatorFiltererUpgradeable.sol";
import "./interfaces/IBreedingInfo.sol";

// import "hardhat/console.sol";

contract KubzTreasure is
    ERC721x,
    DefaultOperatorFiltererUpgradeable,
    ReentrancyGuardUpgradeable
{
    using EnumerableSet for EnumerableSet.AddressSet;
    using EnumerableSet for EnumerableSet.UintSet;

    string public baseTokenURI;
    address public signer;
    mapping(uint256 => uint256) public boxRarity;
    EnumerableSet.AddressSet claimedUsers;

    mapping(uint256 => uint256) public kubzToTreasure;
    address public signerAlt;
    IERC721 public kubzContract;

    uint256 public MAX_SUPPLY;

    function initialize(string memory baseURI) public initializer {
        ERC721x.__ERC721x_init("Kubz Relic", "Kubz Relic");
        ReentrancyGuardUpgradeable.__ReentrancyGuard_init();
        DefaultOperatorFiltererUpgradeable.__DefaultOperatorFilterer_init();
        baseTokenURI = baseURI;
    }

    function setMaxSupplyPhase(uint256 phase) public onlyOwner {
        if (phase == 1) {
            MAX_SUPPLY = 39999;
        } else if (phase == 2) {
            MAX_SUPPLY = 40069;
        }
    }

    function _startTokenId() internal view virtual override returns (uint256) {
        return 1;
    }

    function setAddresses(
        address signerAddress,
        address signerAltAddress,
        address kubzAddress
    ) external onlyOwner {
        signer = signerAddress;
        signerAlt = signerAltAddress;
        kubzContract = IERC721(kubzAddress);
    }

    // =============== AIR DROP ===============

    function ownerClaim(uint256 count) external onlyOwner {
        safeMint(msg.sender, count);
    }

    function safeMint(address receiver, uint256 quantity) internal {
        require(_totalMinted() + quantity <= MAX_SUPPLY, "exceed MAX_SUPPLY");
        _mint(receiver, quantity);
    }

    // =============== BASE URI ===============
    function _baseURI() internal view virtual override returns (string memory) {
        return baseTokenURI;
    }

    function tokenURI(uint256 _tokenId)
        public
        view
        override(ERC721AUpgradeable, IERC721AUpgradeable)
        returns (string memory)
    {
        return string.concat(super.tokenURI(_tokenId));
    }

    function setBaseURI(string calldata baseURI) external onlyOwner {
        baseTokenURI = baseURI;
    }

    // =============== MARKETPLACE CONTROL ===============
    function transferFrom(
        address _from,
        address _to,
        uint256 _tokenId
    ) public virtual override(ERC721x) onlyAllowedOperator(_from) {
        super.transferFrom(_from, _to, _tokenId);
    }

    function safeTransferFrom(
        address from,
        address to,
        uint256 tokenId,
        bytes memory data
    ) public virtual override(ERC721x) onlyAllowedOperator(from) {
        super.safeTransferFrom(from, to, tokenId, data);
    }

    // =============== MISC ===============
    function getClaimedUsersLength() external view returns (uint256) {
        return claimedUsers.length();
    }

    function getClaimedUsers(uint256 fromIdx, uint256 toIdx)
        external
        view
        returns (address[] memory)
    {
        toIdx = Math.min(toIdx, claimedUsers.length());
        address[] memory part = new address[](toIdx - fromIdx);
        for (uint256 i = 0; i < toIdx - fromIdx; i++) {
            part[i] = claimedUsers.at(i + fromIdx);
        }
        return part;
    }

    function getClaimedUsersAll() external view returns (address[] memory) {
        return claimedUsers.values();
    }

    function getKubzToTreasures(uint256[] calldata kubzTokenIds)
        external
        view
        returns (uint256[] memory)
    {
        uint256[] memory part = new uint256[](kubzTokenIds.length);
        for (uint256 i = 0; i < kubzTokenIds.length; i++) {
            uint256 kubzTokenId = kubzTokenIds[i];
            part[i] = kubzToTreasure[kubzTokenId];
        }
        return part;
    }

    function getBoxRarities(uint256 fromTokenId, uint256 toTokenId)
        external
        view
        returns (uint256[] memory)
    {
        uint256[] memory part = new uint256[]((toTokenId - fromTokenId) + 1);
        for (uint256 tokenId = fromTokenId; tokenId <= toTokenId; tokenId++) {
            uint256 i = tokenId - fromTokenId;
            part[i] = boxRarity[tokenId];
        }
        return part;
    }

    function getBoxRaritiesOf(uint256[] calldata tokenIds)
        external
        view
        returns (uint256[] memory)
    {
        uint256[] memory part = new uint256[](tokenIds.length);
        for (uint256 i = 0; i < tokenIds.length; i++) {
            uint256 tokenId = tokenIds[i];
            part[i] = boxRarity[tokenId];
        }
        return part;
    }

    function burn(uint256[] calldata tokenIds) external {
        for (uint256 i = 0; i < tokenIds.length; i++) {
            _burn(tokenIds[i]);
        }
    }
}
