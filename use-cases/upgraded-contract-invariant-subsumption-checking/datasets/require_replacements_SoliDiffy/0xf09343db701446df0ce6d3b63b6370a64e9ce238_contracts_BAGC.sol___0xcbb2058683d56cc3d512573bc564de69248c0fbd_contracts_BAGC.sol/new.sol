// SPDX-License-Identifier: MIT
pragma solidity ^0.8.9;

import "@openzeppelin/contracts-upgradeable/token/ERC721/extensions/ERC721EnumerableUpgradeable.sol";
import "@openzeppelin/contracts-upgradeable/token/ERC721/extensions/ERC721URIStorageUpgradeable.sol";
import "@openzeppelin/contracts-upgradeable/proxy/utils/Initializable.sol";
import "@openzeppelin/contracts/utils/cryptography/ECDSA.sol";

import "./core/BAGCCore.sol";

import "./interface/IBAGC.sol";
import "./interface/IMerchNFT.sol";
import "./interface/IInvitation.sol";

error BAGC_It_Is_User_TokenId();
error BAGC_Not_Invitation_Owner();
error BAGC_Not_Owner();
error BAGC_Already_Registered();
error BAGC_Pool_Not_Exist();

contract BAGC is ERC721URIStorageUpgradeable, ERC721EnumerableUpgradeable, BAGCCore {
    using ECDSA for bytes32;

    /// @notice Emitted when the token is minted.
    /// @dev If a token is minted, this event should be emitted.
    /// @param to The address that the token is minted to.
    /// @param tokenId The identifier for a token.
    /// @param InvitationTokenId The identifier for a invitation token.
    event Minted(address to, uint256 tokenId, uint256 InvitationTokenId);

    /// @notice Emitted when the token is staked.
    event Staked(address caller, uint256 tokenId, uint256 poolId, uint256 currentNum);

    /// @notice Emitted when the token is locked.
    event Locked(address caller, uint256 tokenId);

    /// @notice Emitted when the token is unlocked.
    event Unlocked(address caller, uint256 tokenId);

    function initialize(
        string memory name,
        string memory symbol,
        string memory baseURI_,
        address invitationNFTAddress_,
        address relayerAddress_,
        uint256 numUserAvailableTokens,
        uint256 userTokenBoundaries
    ) public initializer {
        __ERC721_init(name, symbol);
        __ERC721URIStorage_init();
        __ERC721Enumerable_init();
        __Ownable_init();
        baseURI = baseURI_;
        invitationNFTAddress = invitationNFTAddress_;
        relayerAddress = relayerAddress_;
        _numUserAvailableTokens = numUserAvailableTokens;
        _userTokenBoundaries = userTokenBoundaries;
    }

    /**
     * ==================
     * mint
     * ==================
     */

    /// @notice the function used to mint not user tokens with merch
    /// @dev the function that only owner can mint
    /// @param to The address that the token is minted to.
    /// @param tokenId The token id to mint.
    function ownerMint(address to, uint256 tokenId) public onlyOwner {
        if (IBAGC(address(this)).isUserToken(tokenId)) {
            revert BAGC_It_Is_User_TokenId();
        }

        _safeMint(to, tokenId);

        IMerchNFT(merchNFTAddress).mint(to, tokenId);
    }

    /// @notice the function used to mint not user tokens without merch
    /// @dev the function that only owner can mint
    /// @param to The address that the token is minted to.
    /// @param tokenId The token id to mint.
    function ownerMintWithoutMerch(address to, uint256 tokenId) public onlyOwner {
        if (IBAGC(address(this)).isUserToken(tokenId)) {
            revert BAGC_It_Is_User_TokenId();
        }

        _safeMint(to, tokenId);
    }

    function ownerBatchMintWithoutMerch(
        address to,
        uint256[] memory tokenIdArray
    ) public onlyOwner {
        for (uint256 i = 0; i < tokenIdArray.length; i++) {
            if (IBAGC(address(this)).isUserToken(tokenIdArray[i])) {
                revert BAGC_It_Is_User_TokenId();
            }
            _safeMint(to, tokenIdArray[i]);
        }
    }

    /// @notice the function used to mint user token
    /// @param invitationTokenId The tokenId of the invitation NFT.
    /// @param relayerSignature The signature of the relayer.
    /// @param salt The random number
    function userMint(
        uint256 invitationTokenId,
        bytes memory relayerSignature,
        uint256 salt
    ) public {
        (bool success, string memory message) = verifyMintSignature(
            invitationTokenId,
            relayerSignature,
            salt
        );

        require(success, message);

        InvitationNft nft = InvitationNft(invitationNFTAddress);
        if (nft.ownerOf(invitationTokenId) != msg.sender) {
            revert BAGC_Not_Invitation_Owner();
        }

        uint256 tokenId = getRandomAvailableTokenId(msg.sender, salt);

        _safeMint(msg.sender, tokenId);

        _numUserAvailableTokens -= 1;

        nft.burn(invitationTokenId);

        IMerchNFT(merchNFTAddress).mint(msg.sender, tokenId);

        emit Minted(msg.sender, tokenId, invitationTokenId);
    }

    function tokenURI(
        uint256 tokenId
    ) public view override(ERC721URIStorageUpgradeable, ERC721Upgradeable) returns (string memory) {
        return super.tokenURI(tokenId);
    }

    function burn(uint256 tokenId) public {
        require(
            _isApprovedOrOwner(_msgSender(), tokenId),
            "ERC721Burnable: caller is not owner nor approved"
        );
        _burn(tokenId);
    }

    /**
     * ==================
     * staking
     * ==================
     */

    /// @notice the function used to get the pool id of the token
    /// @param tokenId The identifier for an BAGC nft.
    function getPoolId(uint256 tokenId) public view returns (uint256) {
        return _poolId[tokenId];
    }

    /// @notice the function used to get the pool info of the pool id
    function getPoolInfo(uint256 poolId) public view returns (uint256, PoolInfo memory) {
        return (_endTime[poolId], _poolInfo[poolId]);
    }

    /// @param tokenId The identifier for an BAGC nft.
    function stakingPool(uint256 tokenId, uint256 poolId, bytes memory relayerSignature) public {
        PoolInfo memory poolInfo = _poolInfo[poolId];

        if (poolInfo.currentNum + 1 > poolInfo.maxNum) {
            revert("BAGC : Pool is full");
        }

        if (poolInfo.status == 0) {
            revert BAGC_Pool_Not_Exist();
        }
        if (_endTime[_poolId[tokenId]] >= block.timestamp) {
            revert BAGC_Already_Registered();
        }

        if (ownerOf(tokenId) != msg.sender) {
            revert BAGC_Not_Owner();
        }

        (bool success, string memory message) = verifyStakingPoolSignature(
            tokenId,
            poolId,
            relayerSignature
        );
        require(success, message);

        _poolId[tokenId] = poolId;
        _poolInfo[poolId].currentNum += 1;
        emit Staked(msg.sender, tokenId, poolId, poolInfo.currentNum + 1);
    }

    function changePool(uint256 tokenId, uint256 poolId) public onlyOwner {
        if (_poolInfo[_poolId[tokenId]].currentNum > 0) {
            _poolInfo[_poolId[tokenId]].currentNum -= 1;
        }
        if (poolId != 0) {
            _poolInfo[poolId].currentNum += 1;
        }
        _poolId[tokenId] = poolId;
    }

    /// @notice When you execute this function on etherscan, it cannot unlock itself.
    function Lock(uint256 tokenId) public {
        if (ownerOf(tokenId) != msg.sender) {
            revert BAGC_Not_Owner();
        }
        _locked[tokenId] = 1;
        emit Locked(msg.sender, tokenId);
    }

    /// @notice the function used to get the lock status of the token
    function isLock(uint256 tokenId) external view returns (uint256) {
        return _locked[tokenId];
    }

    function Unlock(uint256 tokenId) public onlyOwner {
        _locked[tokenId] = 0;
        emit Unlocked(msg.sender, tokenId);
    }

    /// @dev If it's locked, the transfer is blocked.
    function _beforeTokenTransfer(
        address from,
        address to,
        uint256 tokenId,
        uint256 batchSize
    ) internal override(ERC721Upgradeable, ERC721EnumerableUpgradeable) {
        require(_endTime[_poolId[tokenId]] < block.timestamp, "BAGC: staked");
        require(_locked[tokenId] == 0, "BAGC: locked");
        super._beforeTokenTransfer(from, to, tokenId, batchSize);
    }

    function _baseURI() internal view override returns (string memory) {
        return baseURI;
    }

    function _burn(
        uint256 tokenId
    ) internal override(ERC721URIStorageUpgradeable, ERC721Upgradeable) {
        super._burn(tokenId);
    }

    function supportsInterface(
        bytes4 interfaceId
    ) public view override(ERC721Upgradeable, ERC721EnumerableUpgradeable) returns (bool) {
        return super.supportsInterface(interfaceId);
    }

    uint256[50] private __gap;
}
