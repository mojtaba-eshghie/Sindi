// SPDX-License-Identifier: MIT
pragma solidity >=0.8.10;

import "./D4AProtocol.sol";
import "@openzeppelin/contracts-upgradeable/utils/cryptography/EIP712Upgradeable.sol";

contract D4AProtocolWithPermission is D4AProtocol, EIP712Upgradeable {
    bytes32 internal constant MINTNFT_TYPEHASH =
        keccak256("MintNFT(bytes32 canvasID,bytes32 tokenURIHash,uint256 flatPrice)");

    mapping(bytes32 => NftMintTracker) public nftMintTrackers;

    function createCanvas(bytes32 daoId, string calldata canvasUri, bytes32[] calldata proof)
        external
        payable
        nonReentrant
        returns (bytes32)
    {
        if (settings.permission_control().isCanvasCreatorBlacklisted(daoId, msg.sender)) revert Blacklisted();
        if (!settings.permission_control().inCanvasCreatorWhitelist(daoId, msg.sender, proof)) {
            revert NotInWhitelist();
        }
        return _createCanvas(daoId, canvasUri);
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

    modifier ableToMint(bytes32 daoId, bytes32[] calldata proof, uint256 amount) {
        _checkMintEligibility(daoId, msg.sender, proof, amount);
        _;
    }

    function _checkMintEligibility(bytes32 daoId, address account, bytes32[] calldata proof, uint256 amount)
        internal
        view
    {
        if (!_ableToMint(daoId, account, proof, amount)) revert ExceedMaxMintAmount();
    }

    function mintNFT(
        bytes32 daoId,
        bytes32 _canvas_id,
        string calldata _token_uri,
        bytes32[] calldata proof,
        uint256 _flat_price,
        bytes calldata _signature
    ) external payable nonReentrant returns (uint256) {
        {
            _checkMintEligibility(daoId, msg.sender, proof, 1);
        }
        _verifySignature(_canvas_id, _token_uri, _flat_price, _signature);
        nftMintTrackers[daoId].mintInfos[msg.sender].minted += 1;
        return _mintNft(_canvas_id, _token_uri, _flat_price);
    }

    function batchMint(
        bytes32 daoId,
        bytes32 canvasId,
        bytes32[] calldata proof,
        MintNftInfo[] calldata mintNftInfos,
        bytes[] calldata signatures
    ) external payable nonReentrant returns (uint256[] memory) {
        uint32 length = uint32(mintNftInfos.length);
        {
            _checkMintEligibility(daoId, msg.sender, proof, length);
            for (uint32 i = 0; i < length;) {
                _verifySignature(canvasId, mintNftInfos[i].tokenUri, mintNftInfos[i].flatPrice, signatures[i]);
                unchecked {
                    ++i;
                }
            }
        }
        nftMintTrackers[daoId].mintInfos[msg.sender].minted += length;
        return _mintNft(daoId, canvasId, mintNftInfos);
    }

    event MintCapSet(bytes32 indexed DAO_id, uint32 mintCap, DesignatedCap[] designatedMintCaps);

    error NotDaoOwner();

    function setMintCapAndPermission(
        bytes32 daoId,
        uint32 _mintCap,
        DesignatedCap[] calldata designatedMintCaps,
        IPermissionControl.Whitelist memory whitelist,
        IPermissionControl.Blacklist memory blacklist,
        IPermissionControl.Blacklist memory unblacklist
    ) public override {
        if (msg.sender != settings.project_proxy() && msg.sender != settings.owner_proxy().ownerOf(daoId)) {
            revert NotDaoOwner();
        }
        NftMintTracker storage mintTracker = nftMintTrackers[daoId];
        mintTracker.mintCap = _mintCap;
        uint256 length = designatedMintCaps.length;
        for (uint256 i = 0; i < length;) {
            mintTracker.mintInfos[designatedMintCaps[i].account].designatedCap = designatedMintCaps[i].cap;
            unchecked {
                ++i;
            }
        }

        emit MintCapSet(daoId, _mintCap, designatedMintCaps);

        settings.permission_control().modifyPermission(daoId, whitelist, blacklist, unblacklist);
    }

    error Blacklisted();
    error NotInWhitelist();

    function _ableToMint(bytes32 daoId, address account, bytes32[] calldata proof, uint256 amount)
        internal
        view
        returns (bool)
    {
        // check priority
        // 1. blacklist
        // 2. designated mint cap
        // 3. whitelist (merkle tree || ERC721)
        // 4. DAO mint cap
        IPermissionControl permissionControl = settings.permission_control();
        if (permissionControl.isMinterBlacklisted(daoId, account)) {
            revert Blacklisted();
        }
        uint32 mintCap;
        uint128 minted;
        uint128 designatedCap;
        {
            NftMintTracker storage mintTracker = nftMintTrackers[daoId];
            mintCap = mintTracker.mintCap;
            MintInfo memory mintInfo = mintTracker.mintInfos[account];
            minted = mintInfo.minted;
            designatedCap = mintInfo.designatedCap;
        }

        bool isWhitelistOff;
        {
            IPermissionControl.Whitelist memory whitelist = permissionControl.getWhitelist(daoId);
            isWhitelistOff = whitelist.minterMerkleRoot == bytes32(0) && whitelist.minterNFTHolderPasses.length == 0;
        }

        uint256 expectedMinted = minted + amount;
        // no whitelist
        if (isWhitelistOff) {
            return mintCap == 0 ? true : expectedMinted <= mintCap;
        }

        // whitelist on && not in whitelist
        if (!permissionControl.inMinterWhitelist(daoId, account, proof)) {
            revert NotInWhitelist();
        }

        // designated mint cap
        return designatedCap != 0 ? expectedMinted <= designatedCap : mintCap != 0 ? expectedMinted <= mintCap : true;
    }

    error InvalidSignature();

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
        if (
            !IAccessControlUpgradeable(address(settings)).hasRole(keccak256("SIGNER_ROLE"), signer)
                && signer != settings.owner_proxy().ownerOf(_canvas_id)
        ) revert InvalidSignature();
    }
}
