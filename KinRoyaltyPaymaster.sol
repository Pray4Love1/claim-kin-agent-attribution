// SPDX-License-Identifier: UNLICENSED
pragma solidity ^0.8.20;

/**
 * @title KinRoyaltyPaymaster
 * @notice Sovereign royalty contract with built-in paymaster logic.
 *         Relayers can cover gas for Keeper’s transactions and
 *         recover fees from the royalty cut (post-settlement).
 */
interface IVault {
    function deposit(uint256 amount) external;
    function withdraw(uint256 amount) external;
}

contract KinRoyaltyPaymaster {
    address public immutable keeper;
    address public immutable targetVault;
    uint256 public immutable royaltyBps;

    mapping(address => uint256) public relayerCredits;

    event RoyaltyPaid(address indexed relayer, uint256 fee);
    event DepositForwarded(uint256 netAmount, uint256 royalty);
    event WithdrawForwarded(uint256 netAmount, uint256 royalty);

    constructor(address _keeper, address _targetVault, uint256 _royaltyBps) {
        require(_royaltyBps <= 10000, "Invalid royalty");
        keeper = _keeper;
        targetVault = _targetVault;
        royaltyBps = _royaltyBps;
    }

    /**
     * @notice Relayer submits a deposit on behalf of user.
     * @param user The end-user depositing
     * @param amount Total deposit amount
     * @param relayerGasFee Fee claimed by relayer
     */
    function depositFor(address user, uint256 amount, uint256 relayerGasFee) external {
        uint256 royalty = (amount * royaltyBps) / 10000;
        uint256 net = amount - royalty - relayerGasFee;

        // Credit relayer
        relayerCredits[msg.sender] += relayerGasFee;

        // Send royalty to Keeper
        payable(keeper).transfer(royalty);

        // Forward net deposit into vault
        IVault(targetVault).deposit(net);

        emit RoyaltyPaid(msg.sender, relayerGasFee);
        emit DepositForwarded(net, royalty);
    }

    /**
     * @notice Relayer submits a withdrawal on behalf of user.
     * @param user The end-user withdrawing
     * @param amount Total withdrawal amount
     * @param relayerGasFee Fee claimed by relayer
     */
    function withdrawFor(address user, uint256 amount, uint256 relayerGasFee) external {
        IVault(targetVault).withdraw(amount);

        uint256 royalty = (amount * royaltyBps) / 10000;
        uint256 net = amount - royalty - relayerGasFee;

        // Credit relayer
        relayerCredits[msg.sender] += relayerGasFee;

        // Send royalty to Keeper
        payable(keeper).transfer(royalty);

        // Return net to user
        payable(user).transfer(net);

        emit RoyaltyPaid(msg.sender, relayerGasFee);
        emit WithdrawForwarded(net, royalty);
    }

    /**
     * @notice Relayer withdraws accumulated credits.
     */
    function claimRelayerFees() external {
        uint256 credit = relayerCredits[msg.sender];
        require(credit > 0, "No credits");
        relayerCredits[msg.sender] = 0;
        payable(msg.sender).transfer(credit);
    }

    receive() external payable {}
}
