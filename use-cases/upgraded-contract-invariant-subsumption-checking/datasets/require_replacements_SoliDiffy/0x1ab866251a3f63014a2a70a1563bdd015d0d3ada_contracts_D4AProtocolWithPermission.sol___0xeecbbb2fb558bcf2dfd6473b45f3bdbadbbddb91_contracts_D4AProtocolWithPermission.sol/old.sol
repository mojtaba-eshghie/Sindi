// SPDX-License-Identifier: MIT
pragma solidity >=0.8.10;

import "./D4AProtocol.sol";
import "@openzeppelin/contracts-upgradeable/utils/cryptography/EIP712Upgradeable.sol";

contract D4AProtocolWithPermission is D4AProtocol, EIP712Upgradeable {
    bytes32 internal constant MINTNFT_TYPEHASH =
        keccak256("MintNFT(bytes32 canvasID,bytes32 tokenURIHash,uint256 flatPrice)");

    mapping(bytes32 => NftMintTracker) public nftMintTrackers;

    function createCanvas(bytes32 _DAO_id, string calldata _canvas_uri, bytes32[] calldata _proof)
        external
        payable
        nonReentrant
        returns (bytes32)
    {
        require(
            !settings.permission_control().isCanvasCreatorBlacklisted(_DAO_id, msg.sender), "Account is blacklisted"
        );
        require(settings.permission_control().inCanvasCreatorWhitelist(_DAO_id, msg.sender, _proof), "Not in whitelist");
        return _createCanvas(_DAO_id, _canvas_uri);
    }

    /// @custom:oz-upgrades-unsafe-allow constructor
    constructor() {
        _disableInitializers();
    }

    function initialize(address _settings) public initializer {
        __ReentrancyGuard_init();
        settings = ID4ASetting(_settings);
        project_num = settings.reserved_slots();
        __EIP712_init("D4AProtocolWithPermission", "1");
    }

    error ExceedMaxMintAmount();

    function mintNFT(
        bytes32 _DAO_id,
        bytes32 _canvas_id,
        string calldata _token_uri,
        bytes32[] calldata _proof,
        uint256 _flat_price,
        bytes calldata _signature
    ) external payable nonReentrant returns (uint256) {
        if (!_ableToMint(_DAO_id, msg.sender, _proof)) revert ExceedMaxMintAmount();
        nftMintTrackers[_DAO_id].mintInfos[msg.sender].minted += 1;
        _verifySignature(_canvas_id, _token_uri, _flat_price, _signature);
        return _mintNFT(_canvas_id, _token_uri, _flat_price);
    }

    event MintCapSet(bytes32 indexed DAO_id, uint32 mintCap, DesignatedCap[] designatedMintCaps);

    error NotDaoOwner();

    function setMintCapAndPermission(
        bytes32 _DAO_id,
        uint32 _mintCap,
        DesignatedCap[] calldata designatedMintCaps,
        IPermissionControl.Whitelist memory whitelist,
        IPermissionControl.Blacklist memory blacklist,
        IPermissionControl.Blacklist memory unblacklist
    ) public override {
        if (msg.sender != settings.project_proxy() && msg.sender != settings.owner_proxy().ownerOf(_DAO_id)) {
            revert NotDaoOwner();
        }
        NftMintTracker storage mintTracker = nftMintTrackers[_DAO_id];
        mintTracker.mintCap = _mintCap;
        uint256 length = designatedMintCaps.length;
        for (uint256 i = 0; i < length;) {
            mintTracker.mintInfos[designatedMintCaps[i].account].designatedCap = designatedMintCaps[i].cap;
            unchecked {
                ++i;
            }
        }

        emit MintCapSet(_DAO_id, _mintCap, designatedMintCaps);

        settings.permission_control().modifyPermission(_DAO_id, whitelist, blacklist, unblacklist);
    }

    error Blacklisted();
    error NotInWhitelist();

    function _ableToMint(bytes32 _DAO_id, address _account, bytes32[] calldata _proof) internal view returns (bool) {
        // check priority
        // 1. blacklist
        // 2. designated mint cap
        // 3. whitelist (merkle tree || ERC721)
        // 4. DAO mint cap
        IPermissionControl permissionControl = settings.permission_control();
        if (permissionControl.isMinterBlacklisted(_DAO_id, _account)) {
            revert Blacklisted();
        }
        uint32 mintCap;
        uint128 minted;
        uint128 designatedCap;
        {
            NftMintTracker storage mintTracker = nftMintTrackers[_DAO_id];
            mintCap = mintTracker.mintCap;
            MintInfo memory mintInfo = mintTracker.mintInfos[_account];
            minted = mintInfo.minted;
            designatedCap = mintInfo.designatedCap;
        }

        bool isWhitelistOff;
        {
            IPermissionControl.Whitelist memory whitelist = permissionControl.getWhitelist(_DAO_id);
            isWhitelistOff = whitelist.minterMerkleRoot == bytes32(0) && whitelist.minterNFTHolderPasses.length == 0;
        }

        // no whitelist
        if (isWhitelistOff) {
            return mintCap == 0 ? true : minted < mintCap;
        }

        // whitelist on && not in whitelist
        if (!permissionControl.inMinterWhitelist(_DAO_id, _account, _proof)) {
            revert NotInWhitelist();
        }

        // designated mint cap
        return designatedCap != 0 ? minted < designatedCap : mintCap != 0 ? minted < mintCap : true;
    }

    function _verifySignature(
        bytes32 _canvas_id,
        string calldata _token_uri,
        uint256 _flat_price,
        bytes calldata _signature
    ) internal view {
        bytes32 digest = _hashTypedDataV4(
            keccak256(abi.encode(MINTNFT_TYPEHASH, _canvas_id, keccak256(bytes(_token_uri)), _flat_price))
        );
        address signer = ECDSAUpgradeable.recover(digest, _signature);
        require(
            signer != address(0)
                && (
                    IAccessControlUpgradeable(address(settings)).hasRole(keccak256("SIGNER_ROLE"), signer)
                        || signer == settings.owner_proxy().ownerOf(_canvas_id)
                ),
            "invalid signature"
        );
    }
}
