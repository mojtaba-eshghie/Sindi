// SPDX-License-Identifier: GPL-2.0-or-later
// (C) Florence Finance, 2022 - https://florence.finance/

pragma solidity 0.8.17;

import "@openzeppelin/contracts-upgradeable/token/ERC20/extensions/ERC4626Upgradeable.sol";
import "@openzeppelin/contracts-upgradeable/access/OwnableUpgradeable.sol";
import "@openzeppelin/contracts-upgradeable/security/PausableUpgradeable.sol";
import "@openzeppelin/contracts-upgradeable/token/ERC20/extensions/draft-ERC20PermitUpgradeable.sol";

import "@chainlink/contracts/src/v0.8/interfaces/AggregatorV3Interface.sol";

import "./FlorinToken.sol";
import "./FlorinTreasury.sol";
import "./Util.sol";
import "./Errors.sol";
import "./WhitelistManager.sol";

/// @title LoanVault
/// @dev
contract LoanVault is ERC4626Upgradeable, ERC20PermitUpgradeable, OwnableUpgradeable, PausableUpgradeable {
    using MathUpgradeable for uint256;

    // LOAN EVENTS
    event RepayLoan(uint256 loanAmount);
    event WriteDownLoan(uint256 estimatedDefaultAmount);
    event WriteUpLoan(uint256 recoveredAmount);
    event FinalizeDefault(uint256 definiteDefaultAmount);

    // REWARDS EVENTS
    event DepositRewards(address from, uint256 rewards);
    event SetApr(uint256 apr);
    event SetFundingFee(uint256 fundingFee);

    // FUNDING EVENTS
    event ExecuteFundingAttempt(address indexed funder, IERC20Upgradeable fundingToken, uint256 fundingTokenAmount, uint256 florinTokens, uint256 shares);
    event AddFundingRequest(uint256 fundingRequestId, uint256 florinTokens);
    event CancelFundingRequest(uint256 fundingRequestId);

    event SetFundingTokenChainLinkFeed(
        IERC20Upgradeable fundingToken,
        AggregatorV3Interface fundingTokenChainLinkFeed,
        bool invertFundingTokenChainLinkFeedAnswer_,
        uint256 chainLinkFeedHeartBeat_
    );
    event SetFundingToken(IERC20Upgradeable token, bool accepted);
    event SetPrimaryFunder(address primaryFunder, bool accepted);
    event SetDelegate(address delegate);
    event CreateFundingAttempt(address indexed funder, IERC20Upgradeable fundingToken, uint256 fundingTokenAmount, uint256 florinTokens, uint256 shares);
    event ApproveFundingAttempt(uint256 fundingAttemptId);
    event RejectFundingAttempt(uint256 fundingAttemptId, string reason);
    event FundingAttemptFailed(uint256 fundId, string reason);
    event SetFundApprover(address funderApprover);
    event SetWhitelistManager(address whitelistManager_);

    /////////////////////////////////////////////////////////////////////////
    /////////////////////////////CORE////////////////////////////////////////
    /////////////////////////////////////////////////////////////////////////

    /// @dev FlorinTreasury contract. Used by functions which require EUR transfers
    FlorinTreasury public florinTreasury;

    /// @dev Sum of capital actively deployed in loans (does not include defaults) [18 decimals]
    uint256 public loansOutstanding;

    /// @dev Amount of vault debt. This is used to handle edge cases which should not occur outside of extreme situations. Will be 0 usually. [18 decimals]
    uint256 public debt;

    /// @dev Sum of recent loan write downs that are not definite defaults yet. This is used to cap the writeUpLoan function to the upside in order to prevent abuse. [18 decimals]
    uint256 public loanWriteDown;

    /////////////////////////////////////////////////////////////////////////
    /////////////////////////////REWARDS/////////////////////////////////////
    /////////////////////////////////////////////////////////////////////////

    /// @dev Timestamp of when outstandingRewardsSnapshot was updated the last time [unix-timestamp]
    uint256 public outstandingRewardsSnapshotTimestamp;

    /// @dev Rewards that need to be deposited into the vault in order match the APR at the moment of outstandingRewardsSnapshotTimestamp [18 decimals]
    uint256 public outstandingRewardsSnapshot;

    /// @dev APR of the vault [16 decimals (e.g. 5%=0.05*10^18]
    uint256 public apr;

    /////////////////////////////////////////////////////////////////////////
    /////////////////////////////FUNDING/////////////////////////////////////
    /////////////////////////////////////////////////////////////////////////

    /// @dev Constant for FundingRequest id to signal that there is no currently active FundingRequest
    uint256 private constant NO_FUNDING_REQUEST = type(uint256).max;

    /// @dev A FundingRequest enables the delegate to raise money from primaryFunders
    struct FundingRequest {
        /// @dev Identifier for the FundingRequest
        uint256 id;
        /// @dev Delegate which created the FundingRequest
        address delegate;
        /// @dev Required funding [18 decimals (FLR)]
        uint256 amountRequested;
        /// @dev Amount filled / provided funding [18 decimals (FLR)]
        uint256 amountFilled;
        /// @dev State (see FundingRequestState enum)
        FundingRequestState state;
    }

    /// @dev States for the lifecycle of a FundingRequest
    enum FundingRequestState {
        OPEN,
        FILLED,
        PARTIALLY_FILLED,
        CANCELLED
    }

    /// @dev A Delegate creates a new pending funding attempt to be approved or rejected by the fund approver
    /// enables the delegate to raise money from primaryFunders
    struct FundingAttempt {
        uint256 id;
        address funder;
        IERC20Upgradeable fundingToken;
        uint256 fundingTokenAmount;
        uint256 flrFundingAmount;
        uint256 shares;
        uint256 fillableFundingTokenAmount;
        uint256 maxSlippage;
        FundingAttemptState state;
    }

    /// @dev The different states of a funding attempt
    enum FundingAttemptState {
        PENDING,
        EXECUTED,
        REJECTED,
        FAILED
    }

    /// @dev Enforces a function can only be executed by the vaults delegate
    modifier onlyDelegate() {
        if (delegate != _msgSender()) {
            revert Errors.CallerMustBeDelegate();
        }
        _;
    }

    /// @dev Enforces a function can only be executed by the vaults delegate
    modifier onlyFundApprover() {
        if (fundApprover != _msgSender()) {
            revert Errors.CallerMustBeFundApprover();
        }
        _;
    }

    /// @dev Delegate of the vault. Can create/cancel FundingRequests and call loan control functions
    address public delegate;

    /// @dev PrimaryFunders are allowed to fill open and partially filled FundingRequests. address => primaryFunder status [true/false]
    mapping(address => bool) private primaryFunders;

    /// @dev Contains all funding requests
    FundingRequest[] public fundingRequests;

    /// @dev Id of the last processed funding request
    uint256 public lastProcessedFundingRequestId;

    /// @dev Token => whether the token can be used to fill FundingRequests
    mapping(IERC20Upgradeable => bool) private fundingTokens;

    /// @dev All funding tokens
    IERC20Upgradeable[] private _fundingTokens;

    /// @dev FundingToken => ChainLink feed which provides a conversion rate for the fundingToken to the vaults loans base currency (e.g. USDC => EURSUD)
    mapping(IERC20Upgradeable => AggregatorV3Interface) private fundingTokenChainLinkFeeds;

    /// @dev FundingToken => whether the data provided by the ChainLink feed should be inverted (not all ChainLink feeds are Token->BaseCurrency, some could be BaseCurrency->Token)
    mapping(IERC20Upgradeable => bool) private invertFundingTokenChainLinkFeedAnswer;

    /// @dev ChainLink => uint256 After how many seconds the ChainLink Feed is updated // e.g. EUR/USD: 60 * 60 * 24 = 86400 seconds per day
    mapping(IERC20Upgradeable => uint256) private chainLinkFeedHeartBeat;

    /// Array including all open funding requests
    FundingAttempt[] public fundingAttempts;

    /// @dev The address of the approver who approves pending funding attempts
    address public fundApprover;

    /// @dev Used to correct the exchange rate of the Loan Vault when funding [16 decimals] (e.g. 1%=0.01*10^18)
    uint256 public fundingFee;

    /////////////////////////////////////////////////////////////////////////
    /////////////////////////////ALPHA///////////////////////////////////////
    /////////////////////////////////////////////////////////////////////////

    /// ONLY FOR GOERLI UPGRADE. REMOVE BEFORE UPGRADING MAINNET
    // mapping(address => bool) private whitelistedDepositors;

    /// ONLY FOR GOERLI UPGRADE. REMOVE BEFORE UPGRADING MAINNET
    // bool public depositorWhitelistingEnabled;

    /// @dev if set, the vault is in whitelisting mode for deposits
    WhitelistManager public whitelistManager;

    //<INSERT NEW STATE VARIABLES ABOVE THIS LINE>

    /////////////////////////////////////////////////////////////////////////
    /////////////////////////////CORE////////////////////////////////////////
    /////////////////////////////////////////////////////////////////////////

    /// @custom:oz-upgrades-unsafe-allow constructor
    constructor() initializer {} // solhint-disable-line

    /// @dev Initializes the LoanVault
    /// @param name ERC20 name
    /// @param symbol ERC20 symbol
    /// @param florinTreasury_ see FlorinTreasury contract
    function initialize(string calldata name, string calldata symbol, FlorinTreasury florinTreasury_) external initializer {
        florinTreasury = florinTreasury_;

        // solhint-disable-next-line not-rely-on-time
        outstandingRewardsSnapshotTimestamp = block.timestamp;
        __ERC20_init_unchained(name, symbol);
        __ERC20Permit_init(name);
        __Context_init_unchained();
        __Ownable_init_unchained();
        __Pausable_init_unchained();
        __ERC4626_init_unchained(IERC20MetadataUpgradeable(address(florinTreasury.florinToken())));

        inflationAttackProtectionInitalization();

        _pause();
    }

    /// @dev Minting some dead shares on initialization to avoid inflation attacks against the first depositor
    //       see https://github.com/OpenZeppelin/openzeppelin-contracts/issues/3706#issuecomment-1297230505
    function inflationAttackProtectionInitalization() internal {
        //The below two lines are equivalent of depositting 1 FLR to the vault in our case
        _mint(address(this), 10 ** 18); //Mint 1 share
        outstandingRewardsSnapshot += 10 ** 18; //Add 1 FLR as a reward this effectively increases totalAssets() by 1 FLR

        loansOutstanding += 10 ** 18; //Increase loansOutstanding to make sure this deposit has no impact on loan logic
    }

    /// @dev Overwritten to return always 18 decimals for Loan Vault asset.
    function decimals() public view virtual override(ERC4626Upgradeable, ERC20Upgradeable) returns (uint8) {
        return 18;
    }

    /// @dev Pauses the LoanVault. Check functions with whenPaused/whenNotPaused modifier
    function pause() external onlyOwner {
        _pause();
    }

    /// @dev Unpauses the LoanVault. Check functions with whenPaused/whenNotPaused modifier
    function unpause() external onlyOwner {
        _unpause();
    }

    /// @dev Unique identifier of the LoanVault
    /// @return the id which is the symbol of the vaults asset token
    function id() external view returns (string memory) {
        return symbol();
    }

    /// @dev See {IERC4626-maxDeposit}. Overridden to cap investment to loansOutstanding
    /// @dev Determines how many FLR can currently be deposited into the LoanVault.
    ///      To avoid oversubscription of investment and consequent dilution of rewards this is capped to loansOutstanding.
    /// @return amount of FLR that can be deposited in the LoanVault currently.
    function maxDeposit(address) public view override returns (uint256) {
        if (loansOutstanding <= totalAssets() || debt > 0 || super.paused()) return 0;
        return loansOutstanding - totalAssets();
    }

    /// @dev Increase the vaults assets by minting Florin. If the vault is in debt the debt will be reduced first.
    /// @param amount of FLR to mint into the vault
    function _increaseAssets(uint256 amount) internal {
        if (debt < amount) {
            florinTreasury.mint(address(this), amount - debt);
            debt = 0;
        } else {
            debt -= amount;
        }
    }

    /////////////////////////////////////////////////////////////////////////
    /////////////////////////////LOAN////////////////////////////////////////
    /////////////////////////////////////////////////////////////////////////

    /// @dev Repayment of a matured loan.
    /// @param loanAmount to be repaid in FlorinTreasury.eurToken [18 decimals, see FlorinTreasury.depositEUR]
    function repayLoan(uint256 loanAmount) external onlyDelegate whenNotPaused {
        if (loanAmount > loansOutstanding) {
            revert Errors.LoanAmountMustBeLessOrEqualLoansOutstanding();
        }

        _snapshotOutstandingRewards();
        loansOutstanding -= loanAmount;

        depositEURToTreasury(loanAmount);
        emit RepayLoan(loanAmount);
    }

    /// @dev Write down of loansOutstanding in case of a suspected loan default
    /// @param estimatedDefaultAmount the estimated default amount. Can be corrected via writeUpLoan in terms of recovery
    function writeDownLoan(uint256 estimatedDefaultAmount) external onlyDelegate whenNotPaused {
        if (estimatedDefaultAmount > loansOutstanding) {
            revert Errors.EstimatedDefaultAmountMustBeLessOrEqualLoansOutstanding();
        }
        _snapshotOutstandingRewards();
        uint256 flrBurnAmount = MathUpgradeable.min(estimatedDefaultAmount, totalAssets());
        // uint256 flrBurnAmount = MathUpgradeable.min(estimatedDefaultAmount, IERC20Upgradeable(asset()).balanceOf(address(this)));
        florinTreasury.florinToken().burn(flrBurnAmount);
        loansOutstanding -= estimatedDefaultAmount;
        debt += estimatedDefaultAmount - flrBurnAmount;
        loanWriteDown += estimatedDefaultAmount;
        emit WriteDownLoan(estimatedDefaultAmount);
    }

    /// @dev Write up of loansOutstanding in case of a previously written down loan recovering
    /// @param recoveredAmount the amount the loan has recovered for
    function writeUpLoan(uint256 recoveredAmount) external onlyDelegate whenNotPaused {
        if (recoveredAmount > loanWriteDown) {
            revert Errors.RecoveredAmountMustBeLessOrEqualLoanWriteDown();
        }

        _snapshotOutstandingRewards();

        loansOutstanding += recoveredAmount;
        loanWriteDown -= recoveredAmount;
        _increaseAssets(recoveredAmount);
        emit WriteUpLoan(recoveredAmount);
    }

    /// @dev Lock-in a previously written down loan once it is clear it will not recover any more.
    /// @param definiteDefaultAmount the amount of the loan that has defaulted
    function finalizeDefault(uint256 definiteDefaultAmount) external onlyDelegate whenNotPaused {
        if (definiteDefaultAmount > loanWriteDown) {
            revert Errors.DefiniteDefaultAmountMustBeLessOrEqualLoanWriteDown();
        }

        loanWriteDown -= definiteDefaultAmount;
        emit FinalizeDefault(definiteDefaultAmount);
    }

    /////////////////////////////////////////////////////////////////////////
    /////////////////////////////REWARDS/////////////////////////////////////
    /////////////////////////////////////////////////////////////////////////

    /// @dev Persists the currently outstanding rewards as calculated by calculateOutstandingRewards to protect it
    /// from being distorted by changes to the underlying variables. This should be called before every deposit/withdraw or other
    //  operation that potentially affects the result of calculateOutstandingRewards
    function _snapshotOutstandingRewards() internal {
        outstandingRewardsSnapshot = calculateOutstandingRewards();
        // solhint-disable-next-line not-rely-on-time
        outstandingRewardsSnapshotTimestamp = block.timestamp;
    }

    /// @dev Calculates the amount of rewards that are owed to the vault at the current moment.
    /// This calculation is based on apr as well as the amount of depositors at the current moment.
    /// @return amount of outstanding rewards [18 decimals]
    function calculateOutstandingRewards() public view returns (uint256) {
        uint256 vaultFlrBalance = IERC20Upgradeable(asset()).balanceOf(address(this));
        // solhint-disable-next-line not-rely-on-time
        uint256 timeSinceLastOutstandingRewardsSnapshot = block.timestamp - outstandingRewardsSnapshotTimestamp;

        if (loansOutstanding == 0 || vaultFlrBalance == 0 || apr == 0 || timeSinceLastOutstandingRewardsSnapshot == 0) {
            return outstandingRewardsSnapshot;
        }

        uint256 absoluteFundingRequestSupplied = MathUpgradeable.min(vaultFlrBalance, loansOutstanding);
        uint256 rewardsPerSecondWeighted = absoluteFundingRequestSupplied.mulDiv(apr, (10 ** 18) * 365 * 24 * 60 * 60, MathUpgradeable.Rounding.Down);
        return outstandingRewardsSnapshot + rewardsPerSecondWeighted * timeSinceLastOutstandingRewardsSnapshot;
    }

    /** @dev See {IERC4626-totalAssets}. */
    function totalAssets() public view virtual override returns (uint256) {
        return IERC20Upgradeable(asset()).balanceOf(address(this)) + calculateOutstandingRewards();
    }

    /// @dev Deposit outstanding rewards to the vault. This function expects the rewards in FlorinTreasury.eurToken
    /// and mints an equal amount of FLR into the vault
    /// @param rewards to be deposited in FlorinTreasury.eurToken [18 decimals, see FlorinTreasury.depositEUR]
    function depositRewards(uint256 rewards) external whenNotPaused {
        _snapshotOutstandingRewards();

        rewards = MathUpgradeable.min(outstandingRewardsSnapshot, rewards);
        outstandingRewardsSnapshot -= rewards;

        if (rewards == 0) {
            revert Errors.EffectiveRewardAmountMustBeGreaterThanZero();
        }

        _increaseAssets(rewards);
        depositEURToTreasury(rewards);

        emit DepositRewards(_msgSender(), rewards);
    }

    function depositEURToTreasury(uint256 amountEur) internal {
        IERC20Upgradeable eurToken = florinTreasury.eurToken();

        uint256 transferAmount = Util.convertDecimals(amountEur, 18, Util.getERC20Decimals(eurToken));
        if (transferAmount == 0) {
            revert Errors.TransferAmountMustBeGreaterThanZero();
        }
        SafeERC20Upgradeable.safeTransferFrom(eurToken, _msgSender(), address(florinTreasury), transferAmount);
    }

    /// @dev Set the APR for the vault. This does NOT affect rewards retroactively.
    /// @param _apr the APR
    function setApr(uint256 _apr) external onlyOwner {
        if (_apr != 0) {
            if (_apr < 1e14 || _apr > 1e18) {
                // 0.01% - 100%
                revert Errors.AprOutOfBounds();
            }
        }

        _snapshotOutstandingRewards();
        apr = _apr;
        emit SetApr(apr);
    }

    /// @dev Set the funding fee for the vault. Do not change this fee in between a funding request and funding approval.
    /// @param _fundingFee the funding fee
    function setFundingFee(uint256 _fundingFee) external onlyOwner {
        if (_fundingFee != 0) {
            if (_fundingFee < 1e14 || _fundingFee > 1e17) {
                // 0.01% - 10%
                revert Errors.FundingFeeOutOfBounds();
            }
        }
        fundingFee = _fundingFee;
        emit SetFundingFee(_fundingFee);
    }

    /**
     * @dev Deposit/mint common workflow. Overriden to inject _snapshotOutstandingRewards call and whenNotPaused
     */
    function _deposit(address caller, address receiver, uint256 assets, uint256 shares) internal virtual override whenNotPaused {
        if (!isDepositorWhitelisted(_msgSender())) {
            revert Errors.DepositorNotWhitelisted();
        }
        _snapshotOutstandingRewards();
        return super._deposit(caller, receiver, assets, shares);
    }

    /**
     * @dev Withdraw/redeem common workflow. Overriden to inject _snapshotOutstandingRewards call and whenNotPaused
     */
    function _withdraw(address caller, address receiver, address owner, uint256 assets, uint256 shares) internal virtual override whenNotPaused {
        _snapshotOutstandingRewards();
        return super._withdraw(caller, receiver, owner, assets, shares);
    }

    /////////////////////////////////////////////////////////////////////////
    /////////////////////////////FUNDING/////////////////////////////////////
    /////////////////////////////////////////////////////////////////////////

    /// @dev Create a pending open funding request that will be approved or rejected by the fund approver
    /// The funds will be sent to the delegate in the process. In return the funder receive FLR based on the current exchange rate of their currency
    /// @param fundingToken The funding Token address (e.g. ERC20 USDT)
    /// @param fundingTokenAmount The amount of funding Token to use for creating the open funding request
    /// @param maxSlippage The maximum accepted slippage allowed by the primary funder between creating and approving the pendingOpenFundingRequest (e.g. 1% slippage = 0.01 * 10^18)
    function createFundingAttempt(IERC20Upgradeable fundingToken, uint256 fundingTokenAmount, uint256 maxSlippage) external whenNotPaused {
        (, uint256 flrFundingAmount, uint256 shares, uint256 fillableFundingTokenAmount) = _previewFund(_msgSender(), fundingToken, fundingTokenAmount);

        if (fundingToken.allowance(_msgSender(), address(this)) < fillableFundingTokenAmount) {
            revert Errors.InsufficientAllowance();
        }

        uint256 openPendingFundingRequestId = fundingAttempts.length;
        fundingAttempts.push(
            FundingAttempt(
                openPendingFundingRequestId,
                _msgSender(),
                fundingToken,
                fundingTokenAmount,
                flrFundingAmount,
                shares,
                fillableFundingTokenAmount,
                maxSlippage,
                FundingAttemptState.PENDING
            )
        );
        emit CreateFundingAttempt(_msgSender(), fundingToken, fillableFundingTokenAmount, flrFundingAmount, shares);
    }

    /// @dev execute an open pending funding request. The funds will be sent to the delegate in the process. In return the funder receives FLR
    /// based on the current exchange rate of their currency
    /// @param fundingToken The funding Token address (e.g. ERC20 USDT)
    /// @param fundingTokenAmount The amount of funding Token to use for executing the open funding request
    /// @param funder The funder's address
    function executeFundingAttempt(IERC20Upgradeable fundingToken, uint256 fundingTokenAmount, address funder) internal {
        (uint256 nextOpenFundingRequestId, uint256 flrFundingAmount, uint256 shares, uint256 fillableFundingTokenAmount) = _previewFund(funder, fundingToken, fundingTokenAmount);

        FundingRequest storage currentFundingRequest = fundingRequests[nextOpenFundingRequestId];

        lastProcessedFundingRequestId = currentFundingRequest.id;

        currentFundingRequest.state = FundingRequestState.PARTIALLY_FILLED;

        currentFundingRequest.amountFilled += flrFundingAmount;

        if (currentFundingRequest.amountRequested == currentFundingRequest.amountFilled) {
            currentFundingRequest.state = FundingRequestState.FILLED;
        }

        _snapshotOutstandingRewards();

        loansOutstanding += flrFundingAmount;

        _mint(funder, shares);

        florinTreasury.mint(address(this), flrFundingAmount);

        SafeERC20Upgradeable.safeTransferFrom(fundingToken, funder, currentFundingRequest.delegate, fillableFundingTokenAmount);

        emit ExecuteFundingAttempt(funder, fundingToken, fillableFundingTokenAmount, flrFundingAmount, shares);
    }

    /// @dev Preview the amount of shares that a user will receive according to the amount of funding Token sent to the Loan Vault and converted into assets (FLRs)
    /// In case that fundingToken is USDT, the current exchange rate is taken into account
    /// @param wallet The funder's wallet address
    /// @param fundingToken The funding Token address (e.g. ERC20 USDT)
    /// @param fundingTokenAmount The amount of the funding Token that will be used to fund
    /// @return Amount of shares
    function previewFund(address wallet, IERC20Upgradeable fundingToken, uint256 fundingTokenAmount) external view returns (uint256) {
        (, , uint256 shares, ) = _previewFund(wallet, fundingToken, fundingTokenAmount);
        return shares;
    }

    /// @dev Preview the amount of shares that a user will receive according to the amount of funding Token sent to the Loan Vault and converted into assets (FLRs)
    /// In case that fundingToken is USDT, the current exchange rate is taken into account
    /// @param funder The funder's wallet address
    /// @param fundingToken The funding Token address (e.g. ERC20 USDT)
    /// @param fundingTokenAmount The amount of the funding Token that will be used to fund
    /// @return current funding request id, corrected FLR funding amount, shares, corrected funding token amount
    function _previewFund(address funder, IERC20Upgradeable fundingToken, uint256 fundingTokenAmount) internal view returns (uint256, uint256, uint256, uint256) {
        if (!isPrimaryFunder(funder)) revert Errors.CallerMustBePrimaryFunder();
        if (fundingTokenAmount == 0) revert Errors.FundingAmountMustBeGreaterThanZero();
        if (!isFundingToken(fundingToken)) revert Errors.UnrecognizedFundingToken();
        if (getNextFundingRequestId() == NO_FUNDING_REQUEST) revert Errors.NoOpenFundingRequest();

        FundingRequest storage currentFundingRequest = fundingRequests[getNextFundingRequestId()];

        (uint256 exchangeRate, uint256 exchangeRateDecimals) = getFundingTokenExchangeRate(fundingToken);

        uint256 currentFundingNeedInFLR = currentFundingRequest.amountRequested - currentFundingRequest.amountFilled;

        uint256 currentFundingNeedInFundingToken = (Util.convertDecimalsERC20(currentFundingNeedInFLR, florinTreasury.florinToken(), fundingToken) * exchangeRate) /
            (uint256(10) ** exchangeRateDecimals);

        uint256 flrFundingAmount;

        if (fundingTokenAmount > currentFundingNeedInFundingToken) {
            fundingTokenAmount = currentFundingNeedInFundingToken;
            flrFundingAmount = currentFundingNeedInFLR;
        } else {
            flrFundingAmount = ((Util.convertDecimalsERC20(fundingTokenAmount, fundingToken, florinTreasury.florinToken()) * (uint256(10) ** exchangeRateDecimals)) / exchangeRate);
        }
        uint256 correctedFlrFundingAmount = (flrFundingAmount * (10 ** 18 - fundingFee)) / 10 ** 18;

        return (currentFundingRequest.id, correctedFlrFundingAmount, previewDeposit(correctedFlrFundingAmount), fundingTokenAmount);
    }

    /// @dev A Delegate creates a new OPEN funding request
    /// enables the delegate to raise money from primaryFunders
    /// emits event AddFundingRequest if successful
    /// @param amountRequested the requested amount in FLR
    function addFundingRequest(uint256 amountRequested) external onlyDelegate whenNotPaused {
        if (amountRequested == 0) {
            revert Errors.AmountRequestedMustBeGreaterThanZero();
        }

        uint256 fundingRequestId = fundingRequests.length;
        fundingRequests.push(FundingRequest(fundingRequestId, _msgSender(), amountRequested, 0, FundingRequestState.OPEN));
        emit AddFundingRequest(fundingRequestId, amountRequested);
    }

    /// @dev A Delegate cancels an OPEN funding request by its funding request id
    /// emits event CancelFundingRequest if successful
    /// @param fundingRequestId The funding request id
    function cancelFundingRequest(uint256 fundingRequestId) public whenNotPaused {
        if (fundingRequestId >= fundingRequests.length) {
            revert Errors.FundingRequestDoesNotExist();
        }

        FundingRequest storage fundingRequest = fundingRequests[fundingRequestId];

        if (_msgSender() != owner()) {
            if (fundingRequest.delegate != _msgSender()) {
                revert Errors.CallerMustBeOwnerOrDelegate();
            }

            if (fundingRequest.state != FundingRequestState.OPEN) {
                revert Errors.DelegateCanOnlyCancelOpenFundingRequests();
            }
        }

        fundingRequest.state = FundingRequestState.CANCELLED;
        emit CancelFundingRequest(fundingRequestId);
    }

    /// @dev Get the next open or partially filled funding request id in the array of fundingRequests
    /// @return Funding request id of next open or partially filled funding request or NO_FUNDING_REQUEST
    function getNextFundingRequestId() public view returns (uint256) {
        for (uint256 i = lastProcessedFundingRequestId; i < fundingRequests.length; i++) {
            FundingRequest memory fundingRequest = fundingRequests[i];
            if (fundingRequest.state == FundingRequestState.OPEN || fundingRequest.state == FundingRequestState.PARTIALLY_FILLED) return fundingRequest.id;
        }
        return NO_FUNDING_REQUEST;
    }

    /// @dev Get the last funding request id from the array of fundingRequests
    /// @return Last funding request id of the array or NO_FUNDING_REQUEST when array contains no funding requests
    function getLastFundingRequestId() public view returns (uint256) {
        if (fundingRequests.length == 0) return NO_FUNDING_REQUEST;
        return fundingRequests[fundingRequests.length - 1].id;
    }

    /// @dev Get data of a funding request using its id
    /// @param fundingRequestId id of funding request
    /// @return funding request data
    function getFundingRequest(uint256 fundingRequestId) public view returns (FundingRequest memory) {
        if (fundingRequestId >= fundingRequests.length) {
            revert Errors.FundingRequestDoesNotExist();
        }
        return fundingRequests[fundingRequestId];
    }

    /// @dev Get data of all funding requests in the array
    /// @return array containing all funding requests data
    function getFundingRequests() public view returns (FundingRequest[] memory) {
        return fundingRequests;
    }

    /// @dev  Get the exchange rate of a funding token via ChainLinkFeed
    /// @param fundingToken The funding Token address (e.g. ERC20 USDC)
    /// @return exchange rate and exchange rate decimals
    function getFundingTokenExchangeRate(IERC20Upgradeable fundingToken) public view returns (uint256, uint8) {
        if (!isFundingToken(fundingToken)) revert Errors.UnrecognizedFundingToken();

        if (address(fundingTokenChainLinkFeeds[fundingToken]) == address(0)) {
            revert Errors.NoChainLinkFeedAvailable();
        }

        (, int256 exchangeRate, , uint256 updatedAt, ) = fundingTokenChainLinkFeeds[fundingToken].latestRoundData();

        if (exchangeRate <= 0) {
            revert Errors.ZeroOrNegativeExchangeRate();
        }
        // solhint-disable-next-line not-rely-on-time
        if (updatedAt < block.timestamp - chainLinkFeedHeartBeat[fundingToken]) {
            revert Errors.ChainLinkFeedHeartBeatOutOfBoundary();
            // _pause();
        }

        uint8 exchangeRateDecimals = fundingTokenChainLinkFeeds[fundingToken].decimals();

        if (invertFundingTokenChainLinkFeedAnswer[fundingToken]) {
            exchangeRate = int256(10 ** (exchangeRateDecimals * 2)) / exchangeRate;
        }

        return (uint256(exchangeRate), exchangeRateDecimals);
    }

    /// @dev Adds/modifies a fundingToken <-> ChainLinkFeed mapping
    /// @param fundingToken funding token address
    /// @param fundingTokenChainLinkFeed the ChainLinkFeed address
    /// @param invertFundingTokenChainLinkFeedAnswer_ whether the answer should be inverted
    function setFundingTokenChainLinkFeed(
        IERC20Upgradeable fundingToken,
        AggregatorV3Interface fundingTokenChainLinkFeed,
        bool invertFundingTokenChainLinkFeedAnswer_,
        uint256 chainLinkFeedHeartBeat_
    ) external onlyOwner {
        fundingTokenChainLinkFeeds[fundingToken] = fundingTokenChainLinkFeed;
        invertFundingTokenChainLinkFeedAnswer[fundingToken] = invertFundingTokenChainLinkFeedAnswer_;
        chainLinkFeedHeartBeat[fundingToken] = chainLinkFeedHeartBeat_;
        emit SetFundingTokenChainLinkFeed(fundingToken, fundingTokenChainLinkFeed, invertFundingTokenChainLinkFeedAnswer_, chainLinkFeedHeartBeat_);
    }

    /// @dev Get ChainLinkFeed for a funding token
    /// @param fundingToken the funding token address
    /// @return the ChainLinkFeed address and whether the answer should be inverted
    function getFundingTokenChainLinkFeed(IERC20Upgradeable fundingToken) external view returns (AggregatorV3Interface, bool, uint256) {
        return (fundingTokenChainLinkFeeds[fundingToken], invertFundingTokenChainLinkFeedAnswer[fundingToken], chainLinkFeedHeartBeat[fundingToken]);
    }

    /// @dev Modifies the whitelist status of a funding token
    /// @param fundingToken the funding token
    /// @param accepted whether the funding token is accepted
    function setFundingToken(IERC20Upgradeable fundingToken, bool accepted) external onlyOwner {
        if (fundingTokens[fundingToken] != accepted) {
            fundingTokens[fundingToken] = accepted;
            emit SetFundingToken(fundingToken, accepted);
            if (accepted) {
                _fundingTokens.push(fundingToken);
            } else {
                Util.removeValueFromArray(fundingToken, _fundingTokens);
            }
        }
    }

    /// @dev Get all funding tokens
    /// @return array of all funding tokens
    function getFundingTokens() external view returns (IERC20Upgradeable[] memory) {
        return _fundingTokens;
    }

    /// @dev Check whether a funding token is accepted
    /// @param fundingToken the funding token address
    /// @return whether the token is an accepted funding token
    function isFundingToken(IERC20Upgradeable fundingToken) public view returns (bool) {
        return fundingTokens[fundingToken];
    }

    /// @dev Modifies the whitelist status of a primary funder
    /// @param primaryFunder the primary funder
    /// @param accepted whether the primary funder is accepted
    function setPrimaryFunder(address primaryFunder, bool accepted) external onlyOwner {
        if (primaryFunders[primaryFunder] != accepted) {
            primaryFunders[primaryFunder] = accepted;
            emit SetPrimaryFunder(primaryFunder, accepted);
        }
    }

    /// @dev Check whether a primary funder is accepted
    /// @param primaryFunder the primary funder address
    /// @return whether the primary funder is accepted
    function isPrimaryFunder(address primaryFunder) public view returns (bool) {
        return primaryFunders[primaryFunder];
    }

    /// Changes the delegate of the vault
    /// @param delegate_ the new delegate
    function setDelegate(address delegate_) external onlyOwner {
        if (delegate != delegate_) {
            delegate = delegate_;
            emit SetDelegate(delegate);
        }
    }

    /// Attemps to get a funding attempt by its id
    /// @param fundingAttemptId id of funding attempt
    /// @return funding attempt
    function getFundingAttempt(uint256 fundingAttemptId) public view returns (FundingAttempt memory) {
        if (fundingAttemptId >= fundingAttempts.length) {
            revert Errors.FundingAttemptDoesNotExist();
        }

        return fundingAttempts[fundingAttemptId];
    }

    /// @dev Get all funding attempts
    function getFundingAttempts() public view returns (FundingAttempt[] memory) {
        return fundingAttempts;
    }

    /// @dev Alows the fund approver to approve a funding attempt
    /// @param fundingAttemptId id of funding attempt
    function approveFundingAttempt(uint256 fundingAttemptId) public onlyFundApprover {
        FundingAttempt storage fundingAttempt = fundingAttempts[fundingAttemptId];

        if (fundingAttempt.state != FundingAttemptState.PENDING) {
            revert Errors.FundingAttemptNotPending();
        }

        (, uint256 assets, , ) = _previewFund(fundingAttempt.funder, fundingAttempt.fundingToken, fundingAttempt.fundingTokenAmount);

        if (assets < fundingAttempt.flrFundingAmount) {
            uint256 slippage = 10 ** 18 - (assets * 10 ** 18) / fundingAttempt.flrFundingAmount;

            if (slippage >= fundingAttempt.maxSlippage) {
                fundingAttempt.state = FundingAttemptState.FAILED;
                emit FundingAttemptFailed(fundingAttemptId, "slippage too high");
                return;
            }
        }

        executeFundingAttempt(fundingAttempt.fundingToken, fundingAttempt.fundingTokenAmount, fundingAttempt.funder);
        fundingAttempt.state = FundingAttemptState.EXECUTED;
        emit ApproveFundingAttempt(fundingAttemptId);
    }

    /// @dev Alows the fund approver to reject a funding attempt
    /// @param fundingAttemptId id of funding attempt
    /// @param reason reason for rejection
    function rejectFundingAttempt(uint256 fundingAttemptId, string calldata reason) external onlyFundApprover {
        FundingAttempt storage fundingAttempt = fundingAttempts[fundingAttemptId];
        if (fundingAttempt.state != FundingAttemptState.PENDING) {
            revert Errors.FundingAttemptNotPending();
        }

        fundingAttempt.state = FundingAttemptState.REJECTED;
        emit RejectFundingAttempt(fundingAttemptId, reason);
    }

    /// Changes the fund approver of the vault
    /// @param fundApprover_ the new delegate
    function setFundApprover(address fundApprover_) external onlyOwner {
        fundApprover = fundApprover_;
        emit SetFundApprover(fundApprover);
    }

    /// @dev Check whether a depositor is whitelisted
    /// @param depositor the depositor to check
    /// @return whether the depositor is whitelisted
    function isDepositorWhitelisted(address depositor) public view returns (bool) {
        return address(whitelistManager) == address(0) || whitelistManager.isDepositorWhitelisted(depositor);
    }

    function setWhitelistManager(WhitelistManager whitelistManager_) external onlyOwner {
        whitelistManager = whitelistManager_;
        emit SetWhitelistManager(address(whitelistManager_));
    }
}
