// SPDX-License-Identifier: UNLICENSED
pragma solidity 0.8.28;

import "@openzeppelin/contracts/token/ERC20/extensions/ERC20Burnable.sol";
import "@openzeppelin/contracts/token/ERC20/extensions/ERC20Permit.sol";
import "@openzeppelin/contracts/access/Ownable.sol";

contract SovereignPurr is ERC20Burnable, ERC20Permit, Ownable {
    address public royaltyReceiver;
    uint256 public royaltyFee; // basis points, e.g., 250 = 2.5%

    mapping(address => bool) public claimed;

    constructor(
        address _royaltyReceiver,
        uint256 _royaltyFee
    ) ERC20("P∞rr", "PURR") ERC20Permit("P∞rr") {
        royaltyReceiver = _royaltyReceiver;
        royaltyFee = _royaltyFee;
    }

    function claim(address to, uint256 amount) external onlyOwner {
        require(!claimed[to], "Already claimed");
        claimed[to] = true;
        _mint(to, amount);
    }

    function transfer(address recipient, uint256 amount) public override returns (bool) {
        uint256 fee = (amount * royaltyFee) / 10000;
        _transfer(_msgSender(), royaltyReceiver, fee);
        _transfer(_msgSender(), recipient, amount - fee);
        return true;
    }

    function updateRoyalty(address receiver, uint256 fee) external onlyOwner {
        royaltyReceiver = receiver;
        royaltyFee = fee;
    }
}
