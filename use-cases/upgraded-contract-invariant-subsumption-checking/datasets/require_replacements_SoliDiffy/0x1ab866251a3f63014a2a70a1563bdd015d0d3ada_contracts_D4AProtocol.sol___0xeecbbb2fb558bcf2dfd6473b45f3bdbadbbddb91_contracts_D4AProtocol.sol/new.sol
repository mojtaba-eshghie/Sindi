// SPDX-License-Identifier: MIT
pragma solidity >=0.8.10;

import "@openzeppelin/contracts-upgradeable/proxy/utils/Initializable.sol";
import "@openzeppelin/contracts-upgradeable/security/ReentrancyGuardUpgradeable.sol";
import "@openzeppelin/contracts-upgradeable/access/IAccessControlUpgradeable.sol";
import "./impl/D4AProject.sol";
import "./impl/D4ACanvas.sol";
import "./impl/D4APrice.sol";
import "./impl/D4AReward.sol";
import "./interface/ID4ASetting.sol";
import "./interface/ID4AProtocol.sol";

abstract contract D4AProtocol is Initializable, ReentrancyGuardUpgradeable, ID4AProtocol {
    using D4AProject for mapping(bytes32 => D4AProject.project_info);
    using D4ACanvas for mapping(bytes32 => D4ACanvas.canvas_info);
    using D4APrice for D4APrice.project_price_info;
    using D4AReward for mapping(bytes32 => D4AReward.reward_info);

    mapping(bytes32 => bool) public uri_exists;

    uint256 public project_num;

    mapping(bytes32 => mapping(uint256 => uint256)) public round_2_total_eth;

    uint256 public canvas_num;

    uint256 public project_bitmap;

    // event from library
    event NewProject(
        bytes32 project_id, string uri, address fee_pool, address erc20_token, address erc721_token, uint256 royalty_fee
    );
    event NewCanvas(bytes32 project_id, bytes32 canvas_id, string uri);

    /// @custom:oz-upgrades-unsafe-allow constructor
    constructor() {
        _disableInitializers();
    }

    error NotRole(bytes32 role, address account);

    /**
     * @dev Modifier that checks that an account has a specific role. Reverts
     * with a standardized message including the required role.
     *
     * The format of the revert reason is given by the following regular expression:
     *
     *  /^AccessControl: account (0x[0-9a-f]{40}) is missing role (0x[0-9a-f]{64})$/
     *
     * _Available since v4.1._
     */
    modifier onlyRole(bytes32 role) {
        _checkRole(role);
        _;
    }

    /**
     * @dev Revert with a standard message if `msg.sender` is missing `role`.
     * Overriding this function changes the behavior of the {onlyRole} modifier.
     *
     * Format of the revert message is described in {_checkRole}.
     *
     * _Available since v4.6._
     */
    function _checkRole(bytes32 role) internal view virtual {
        _checkRole(role, msg.sender);
    }

    /**
     * @dev Revert with a standard message if `account` is missing `role`.
     *
     * The format of the revert reason is given by the following regular expression:
     *
     *  /^AccessControl: account (0x[0-9a-f]{40}) is missing role (0x[0-9a-f]{64})$/
     */
    function _checkRole(bytes32 role, address account) internal view virtual {
        if (!_hasRole(role, account)) {
            revert NotRole(role, account);
        }
    }

    function _hasRole(bytes32 role, address account) internal view virtual returns (bool) {
        return IAccessControlUpgradeable(address(settings)).hasRole(role, account);
    }

    function changeProjectNum(uint256 _project_num) public onlyRole(bytes32(0)) {
        project_num = _project_num;
    }

    function changeSetting(address _settings) public onlyRole(bytes32(0)) {
        settings = ID4ASetting(_settings);
    }

    error NotCaller(address caller);

    modifier onlyCaller(address caller) {
        _checkCaller(caller);
        _;
    }

    function _checkCaller(address caller) internal view {
        if (caller != msg.sender) {
            revert NotCaller(caller);
        }
    }

    modifier d4aNotPaused() {
        _checkPauseStatus();
        _;
    }

    error D4APaused();

    function _checkPauseStatus() internal view {
        if (settings.d4a_pause()) {
            revert D4APaused();
        }
    }

    modifier notPaused(bytes32 id) {
        _checkPauseStatus(id);
        _;
    }

    error Paused(bytes32 id);

    function _checkPauseStatus(bytes32 id) internal view {
        if (settings.pause_status(id)) {
            revert Paused(id);
        }
    }

    error UriAlreadyExist(string uri);

    error UriNotExist(string uri);

    modifier uriExist(string calldata uri) {
        _checkUriExist(uri);
        _;
    }

    modifier uriNotExist(string calldata uri) {
        _checkUriNotExist(uri);
        _;
    }

    function _uriExist(string calldata uri) internal view returns (bool) {
        return uri_exists[keccak256(abi.encodePacked(uri))];
    }

    function _checkUriExist(string calldata uri) internal view {
        if (!_uriExist(uri)) {
            revert UriNotExist(uri);
        }
    }

    function _checkUriNotExist(string calldata uri) internal view {
        if (_uriExist(uri)) {
            revert UriAlreadyExist(uri);
        }
    }

    function createProject(
        uint256 _start_prb,
        uint256 _mintable_rounds,
        uint256 _floor_price_rank,
        uint256 _max_nft_rank,
        uint96 _royalty_fee,
        string calldata _project_uri
    )
        public
        payable
        override
        nonReentrant
        onlyCaller(settings.project_proxy())
        d4aNotPaused
        uriNotExist(_project_uri)
        returns (bytes32 project_id)
    {
        uri_exists[keccak256(abi.encodePacked(_project_uri))] = true;
        project_id = all_projects.createProject(
            settings,
            _start_prb,
            _mintable_rounds,
            _floor_price_rank,
            _max_nft_rank,
            _royalty_fee,
            project_num,
            _project_uri
        );
        project_num++;
    }

    error DaoIndexTooLarge();
    error DaoIndexAlreadyExist();

    function createOwnerProject(
        uint256 _start_prb,
        uint256 _mintable_rounds,
        uint256 _floor_price_rank,
        uint256 _max_nft_rank,
        uint96 _royalty_fee,
        string calldata _project_uri,
        uint256 _project_index
    )
        public
        payable
        override
        nonReentrant
        onlyCaller(settings.project_proxy())
        d4aNotPaused
        returns (
            // uriNotExist(_project_uri)
            bytes32 project_id
        )
    {
        {
            _checkUriNotExist(_project_uri);
        }
        {
            if (_project_index >= settings.reserved_slots()) revert DaoIndexTooLarge();
            if (((project_bitmap >> _project_index) & 1) != 0) revert DaoIndexAlreadyExist();
        }

        {
            project_bitmap |= (1 << _project_index);
            uri_exists[keccak256(abi.encodePacked(_project_uri))] = true;
        }
        {
            return all_projects.createProject(
                settings,
                _start_prb,
                _mintable_rounds,
                _floor_price_rank,
                _max_nft_rank,
                _royalty_fee,
                _project_index,
                _project_uri
            );
        }
    }

    function getProjectCanvasCount(bytes32 _project_id) public view returns (uint256) {
        return all_projects.getProjectCanvasCount(_project_id);
    }

    error DaoNotExist();
    error CanvasNotExist();

    modifier daoExist(bytes32 daoId) {
        _checkDaoExist(daoId);
        _;
    }

    function _checkDaoExist(bytes32 daoId) internal view {
        if (!all_projects[daoId].exist) revert DaoNotExist();
    }

    modifier canvasExist(bytes32 canvasId) {
        _checkCanvasExist(canvasId);
        _;
    }

    function _checkCanvasExist(bytes32 canvasId) internal view {
        if (!all_canvases[canvasId].exist) revert CanvasNotExist();
    }

    function _createCanvas(bytes32 _project_id, string calldata _canvas_uri)
        internal
        d4aNotPaused
        daoExist(_project_id)
        notPaused(_project_id)
        uriNotExist(_canvas_uri)
        returns (bytes32 canvas_id)
    {
        uri_exists[keccak256(abi.encodePacked(_canvas_uri))] = true;

        canvas_id = all_canvases.createCanvas(
            settings,
            all_projects[_project_id].fee_pool,
            _project_id,
            all_projects[_project_id].start_prb,
            all_projects.getProjectCanvasCount(_project_id),
            _canvas_uri
        );

        all_projects[_project_id].canvases.push(canvas_id);
    }

    event D4AMintNFT(bytes32 project_id, bytes32 canvas_id, uint256 token_id, string token_uri, uint256 price);

    error NftExceedMaxAmount();

    error PriceTooLow();

    function _mintNft(bytes32 canvasId, string calldata _token_uri, uint256 flatPrice)
        internal
        returns (
            // d4aNotPaused
            // notPaused(canvasId)
            // canvasExist(canvasId)
            // uriNotExist(_token_uri)
            uint256 token_id
        )
    {
        {
            _checkPauseStatus();
            _checkPauseStatus(canvasId);
            _checkCanvasExist(canvasId);
            _checkUriNotExist(_token_uri);
        }
        bytes32 daoId = all_canvases[canvasId].project_id;

        if (flatPrice != 0 && flatPrice < all_projects.getProjectFloorPrice(daoId)) revert PriceTooLow();
        _checkPauseStatus(daoId);

        D4AProject.project_info storage pi = all_projects[daoId];
        D4ACanvas.canvas_info storage ci = all_canvases[canvasId];
        if (pi.nft_supply >= pi.max_nft_amount) revert NftExceedMaxAmount();

        MintVars memory vars;
        vars.currentRound = settings.PRB().currentRound();
        vars.nftPriceMultiplyFactor =
            pi.nftPriceMultiplyFactor == 0 ? settings.defaultNftPriceMultiplyFactor() : pi.nftPriceMultiplyFactor;

        {
            bytes32 token_uri_hash = keccak256(abi.encodePacked(_token_uri));
            uri_exists[token_uri_hash] = true;
        }

        // get next mint price
        GetCanvasNextPriceVars memory getCanvasNextPriceVar;
        getCanvasNextPriceVar.daoId = daoId;
        getCanvasNextPriceVar.canvasId = canvasId;
        getCanvasNextPriceVar.currentRound = vars.currentRound;
        getCanvasNextPriceVar.floorPrices = pi.floor_prices;
        getCanvasNextPriceVar.floorPriceRank = pi.floor_price_rank;
        getCanvasNextPriceVar.startPrb = pi.start_prb;
        getCanvasNextPriceVar.nftPriceMultiplyFactor = vars.nftPriceMultiplyFactor;
        getCanvasNextPriceVar.flatPrice = flatPrice;
        uint256 price = _getCanvasNextPrice(getCanvasNextPriceVar);

        // split fee
        {
            address protocolFeePool = settings.protocol_fee_pool();
            address daoFeePool = pi.fee_pool;
            address canvasOwner = settings.owner_proxy().ownerOf(canvasId);
            uint256 daoShare = (
                flatPrice == 0 ? settings.mint_project_fee_ratio() : settings.mint_project_fee_ratio_flat_price()
            ) * price;
            (vars.daoFee, vars.protocolFee) = _splitFee(protocolFeePool, daoFeePool, canvasOwner, price, daoShare);
        }

        // update
        _updatePrice(vars.currentRound, daoId, canvasId, price, flatPrice, vars.nftPriceMultiplyFactor);

        _updateReward(daoId, canvasId, vars.daoFee, vars.protocolFee, price);

        // mint
        token_id = ID4AERC721(pi.erc721_token).mintItem(msg.sender, _token_uri);
        {
            pi.nft_supply++;
            ci.nft_tokens.push(token_id);
            ci.nft_token_number++;
            tokenid_2_canvas[keccak256(abi.encodePacked(daoId, token_id))] = canvasId;
        }

        emit D4AMintNFT(daoId, canvasId, token_id, _token_uri, price);
    }

    function _updatePrice(
        uint256 currentRound,
        bytes32 daoId,
        bytes32 canvasId,
        uint256 price,
        uint256 flatPrice,
        uint256 nftPriceMultiplyFactor
    ) internal {
        if (flatPrice == 0) {
            all_prices[daoId].updateCanvasPrice(currentRound, canvasId, price, nftPriceMultiplyFactor);
        }
    }

    struct MintNftInfo {
        string tokenUri;
        uint256 flatPrice;
    }

    struct MintVars {
        uint32 length;
        uint256 currentRound;
        uint256 nftPriceMultiplyFactor;
        uint256 priceChangeBasisPoint;
        uint256 price;
        uint256 daoTotalShare;
        uint256 totalPrice;
        uint256 daoFee;
        uint256 protocolFee;
        uint256 initialPrice;
    }

    function _mintNft(bytes32 daoId, bytes32 canvasId, MintNftInfo[] calldata mintNftInfos)
        internal
        returns (
            // d4aNotPaused
            // notPaused(daoId)
            // canvasExist(canvasId)
            // notPaused(canvasId)
            uint256[] memory
        )
    {
        {
            _checkPauseStatus();
            _checkPauseStatus(daoId);
            _checkCanvasExist(canvasId);
            _checkPauseStatus(canvasId);
        }

        MintVars memory vars;
        vars.length = uint32(mintNftInfos.length);
        {
            uint256 projectFloorPrice = all_projects.getProjectFloorPrice(daoId);
            for (uint32 i = 0; i < vars.length;) {
                _checkUriNotExist(mintNftInfos[i].tokenUri);
                if (mintNftInfos[i].flatPrice != 0 && mintNftInfos[i].flatPrice < projectFloorPrice) {
                    revert PriceTooLow();
                }
                unchecked {
                    ++i;
                }
            }
        }

        D4AProject.project_info storage pi = all_projects[daoId];
        D4ACanvas.canvas_info storage ci = all_canvases[canvasId];
        if (pi.nft_supply >= pi.max_nft_amount) revert NftExceedMaxAmount();

        vars.currentRound = settings.PRB().currentRound();
        vars.nftPriceMultiplyFactor =
            pi.nftPriceMultiplyFactor == 0 ? settings.defaultNftPriceMultiplyFactor() : pi.nftPriceMultiplyFactor;
        vars.priceChangeBasisPoint = D4APrice._PRICE_CHANGE_BASIS_POINT;

        GetCanvasNextPriceVars memory getCanvasNextPriceVar;
        getCanvasNextPriceVar.daoId = daoId;
        getCanvasNextPriceVar.currentRound = vars.currentRound;
        getCanvasNextPriceVar.floorPrices = pi.floor_prices;
        getCanvasNextPriceVar.floorPriceRank = pi.floor_price_rank;
        getCanvasNextPriceVar.startPrb = pi.start_prb;
        getCanvasNextPriceVar.nftPriceMultiplyFactor = vars.nftPriceMultiplyFactor;
        vars.price = _getCanvasNextPrice(getCanvasNextPriceVar);
        vars.initialPrice = vars.price;
        vars.daoTotalShare;
        vars.totalPrice;
        uint256[] memory tokenIds = new uint256[](vars.length);
        {
            uint256 mintProjectFeeRatio = settings.mint_project_fee_ratio();
            uint256 mintProjectFeeRatioFlatPrice = settings.mint_project_fee_ratio_flat_price();
            for (uint32 i = 0; i < vars.length;) {
                {
                    bytes32 token_uri_hash = keccak256(abi.encodePacked(mintNftInfos[i].tokenUri));
                    uri_exists[token_uri_hash] = true;
                }

                tokenIds[i] = ID4AERC721(pi.erc721_token).mintItem(msg.sender, mintNftInfos[i].tokenUri);
                {
                    pi.nft_supply++;
                    ci.nft_tokens.push(tokenIds[i]);
                    ci.nft_token_number++;
                    tokenid_2_canvas[keccak256(abi.encodePacked(daoId, tokenIds[i]))] = canvasId;
                }
                uint256 flatPrice = mintNftInfos[i].flatPrice;
                if (flatPrice == 0) {
                    vars.daoTotalShare += mintProjectFeeRatio * vars.price;
                    vars.totalPrice += vars.price;
                    emit D4AMintNFT(daoId, canvasId, tokenIds[i], mintNftInfos[i].tokenUri, vars.price);
                    vars.price *= vars.nftPriceMultiplyFactor / vars.priceChangeBasisPoint;
                } else {
                    vars.daoTotalShare += mintProjectFeeRatioFlatPrice * flatPrice;
                    vars.totalPrice += flatPrice;
                    emit D4AMintNFT(daoId, canvasId, tokenIds[i], mintNftInfos[i].tokenUri, flatPrice);
                }
                unchecked {
                    ++i;
                }
            }
        }

        {
            // split fee
            address protocolFeePool = settings.protocol_fee_pool();
            address daoFeePool = pi.fee_pool;
            address canvasOwner = settings.owner_proxy().ownerOf(canvasId);

            (vars.daoFee, vars.protocolFee) =
                _splitFee(protocolFeePool, daoFeePool, canvasOwner, vars.totalPrice, vars.daoTotalShare);
        }

        // update canvas price
        if (vars.price != vars.initialPrice) {
            vars.price = vars.price * vars.priceChangeBasisPoint / vars.nftPriceMultiplyFactor;
            _updatePrice(vars.currentRound, daoId, canvasId, vars.price, 0, vars.nftPriceMultiplyFactor);
        }

        _updateReward(daoId, canvasId, vars.daoFee, vars.protocolFee, vars.totalPrice);

        return tokenIds;
    }

    struct GetCanvasNextPriceVars {
        bytes32 daoId;
        bytes32 canvasId;
        uint256 currentRound;
        uint256[] floorPrices;
        uint256 floorPriceRank;
        uint256 startPrb;
        uint256 nftPriceMultiplyFactor;
        uint256 flatPrice;
    }

    function _getCanvasNextPrice(GetCanvasNextPriceVars memory vars) internal view returns (uint256 price) {
        if (vars.flatPrice == 0) {
            price = all_prices[vars.daoId].getCanvasNextPrice(
                vars.currentRound,
                vars.floorPrices,
                vars.floorPriceRank,
                vars.startPrb,
                vars.canvasId,
                vars.nftPriceMultiplyFactor
            );
        } else {
            price = vars.flatPrice;
        }
    }

    function _updateReward(bytes32 _project_id, bytes32 canvasId, uint256 daoFee, uint256 protocolFee, uint256 price)
        internal
    {
        D4AProject.project_info memory pi = all_projects[_project_id];

        all_rewards.updateMintWithAmount(
            settings, _project_id, canvasId, price - daoFee - protocolFee, daoFee, pi.mintable_rounds, round_2_total_eth
        );
        all_rewards.updateRewardForCanvas(
            settings, _project_id, canvasId, pi.start_prb, pi.mintable_rounds, pi.erc20_total_supply
        );
    }

    error NotEnoughEther();
    error EthTransferFailed();

    function _splitFee(
        address protocolFeePool,
        address daoFeePool,
        address canvasOwner,
        uint256 price,
        uint256 daoShare
    ) internal returns (uint256 daoFee, uint256 protocolFee) {
        if (msg.value < price) revert NotEnoughEther();

        uint256 exchange = msg.value - price;
        uint256 ratioBasisPoint = settings.ratio_base();

        daoFee = daoShare / ratioBasisPoint;
        protocolFee = price * settings.mint_d4a_fee_ratio() / ratioBasisPoint;

        _transferEth(protocolFeePool, protocolFee);
        _transferEth(daoFeePool, daoFee);
        _transferEth(canvasOwner, price - daoFee - protocolFee);
        _transferEth(msg.sender, exchange);
    }

    function _transferEth(address to, uint256 amount) internal {
        if (amount == 0) return;
        (bool succ,) = to.call{value: amount}("");
        if (!succ) revert EthTransferFailed();
    }

    function getNFTTokenCanvas(bytes32 _project_id, uint256 _token_id) public view returns (bytes32) {
        return tokenid_2_canvas[keccak256(abi.encodePacked(_project_id, _token_id))];
    }

    event D4AClaimProjectERC20Reward(bytes32 project_id, address erc20_token, uint256 amount);
    event D4AExchangeERC20ToETH(
        bytes32 project_id, address owner, address to, uint256 erc20_amount, uint256 eth_amount
    );

    function claimProjectERC20Reward(bytes32 _project_id)
        public
        nonReentrant
        d4aNotPaused
        notPaused(_project_id)
        daoExist(_project_id)
        returns (uint256)
    {
        D4AProject.project_info storage pi = all_projects[_project_id];
        all_rewards.issueTokenToCurrentRound(
            settings, _project_id, pi.erc20_token, pi.start_prb, pi.mintable_rounds, pi.erc20_total_supply
        );
        uint256 amount = all_rewards.claimProjectReward(
            settings, _project_id, pi.erc20_token, pi.start_prb, pi.mintable_rounds, pi.erc20_total_supply
        );
        emit D4AClaimProjectERC20Reward(_project_id, pi.erc20_token, amount);
        return amount;
    }

    function claimProjectERC20RewardWithETH(bytes32 _project_id) public returns (uint256) {
        uint256 erc20_amount = claimProjectERC20Reward(_project_id);
        D4AProject.project_info storage pi = all_projects[_project_id];
        return D4AReward.claimProjectERC20RewardWithETH(
            settings, _project_id, pi.erc20_token, erc20_amount, all_projects[_project_id].fee_pool, round_2_total_eth
        );
    }

    event D4AClaimCanvasReward(bytes32 project_id, bytes32 canvas_id, address erc20_token, uint256 amount);

    function claimCanvasReward(bytes32 canvasId)
        public
        nonReentrant
        d4aNotPaused
        notPaused(canvasId)
        canvasExist(canvasId)
        returns (uint256)
    {
        bytes32 project_id = all_canvases[canvasId].project_id;
        _checkDaoExist(project_id);
        _checkPauseStatus(project_id);

        D4AProject.project_info storage pi = all_projects[project_id];

        all_rewards.issueTokenToCurrentRound(
            settings, project_id, pi.erc20_token, pi.start_prb, pi.mintable_rounds, pi.erc20_total_supply
        );
        uint256 amount = all_rewards.claimCanvasReward(
            settings, project_id, canvasId, pi.erc20_token, pi.start_prb, pi.mintable_rounds, pi.erc20_total_supply
        );
        emit D4AClaimCanvasReward(project_id, canvasId, pi.erc20_token, amount);
        return amount;
    }

    function claimCanvasRewardWithETH(bytes32 canvasId) public returns (uint256) {
        uint256 erc20_amount = claimCanvasReward(canvasId);

        bytes32 project_id = all_canvases[canvasId].project_id;
        D4AProject.project_info storage pi = all_projects[project_id];
        return D4AReward.claimCanvasRewardWithETH(
            settings,
            project_id,
            canvasId,
            pi.erc20_token,
            erc20_amount,
            all_projects[project_id].fee_pool,
            round_2_total_eth
        );
    }

    function exchangeERC20ToETH(bytes32 _project_id, uint256 amount, address _to)
        public
        nonReentrant
        d4aNotPaused
        notPaused(_project_id)
        returns (uint256)
    {
        D4AProject.project_info storage pi = all_projects[_project_id];
        all_rewards.issueTokenToCurrentRound(
            settings, _project_id, pi.erc20_token, pi.start_prb, pi.mintable_rounds, pi.erc20_total_supply
        );
        return D4AReward.ToETH(
            settings, pi.erc20_token, pi.fee_pool, _project_id, msg.sender, _to, amount, round_2_total_eth
        );
    }

    function changeDaoNftPriceMultiplyFactor(bytes32 daoId, uint256 newNftPriceMultiplyFactor)
        public
        onlyRole(bytes32(0))
    {
        require(newNftPriceMultiplyFactor >= 10_000);
        all_projects[daoId].nftPriceMultiplyFactor = newNftPriceMultiplyFactor;
    }
}
