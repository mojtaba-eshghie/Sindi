// SPDX-License-Identifier: MIT
pragma solidity >=0.8.10;

import "./D4AProtocol.sol";
import "@openzeppelin/contracts-upgradeable/utils/cryptography/EIP712Upgradeable.sol";

contract D4AProtocolWithPermission is D4AProtocol, EIP712Upgradeable {
    bytes32 internal constant MINTNFT_TYPEHASH =
        keccak256("MintNFT(bytes32 canvasID,bytes32 tokenURIHash,uint256 flatPrice)");

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

    function initialize(address _settings) external reinitializer(2) {
        settings = ID4ASetting(_settings);
        __EIP712_init("D4AProtocolWithPermission", "1");
    }

    function mintNFT(
        bytes32 _DAO_id,
        bytes32 _canvas_id,
        string calldata _token_uri,
        bytes32[] calldata _proof,
        uint256 _flat_price,
        bytes calldata _signature
    ) external payable nonReentrant returns (uint256) {
        require(!settings.permission_control().isMinterBlacklisted(_DAO_id, msg.sender), "Account is blacklisted");
        require(settings.permission_control().inMinterWhitelist(_DAO_id, msg.sender, _proof), "Not in whitelist");
        _verifySignature(_canvas_id, _token_uri, _flat_price, _signature);
        return _mintNFT(_canvas_id, _token_uri, _flat_price);
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
