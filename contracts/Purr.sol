// SPDX-License-Identifier: MIT
pragma solidity 0.8.28;

import "@openzeppelin/contracts/token/ERC20/extensions/ERC20Permit.sol";

contract Purr is ERC20Permit {
    constructor() ERC20("Purr", "PURR") ERC20Permit("Purr") {
        _mint(0x2000000000000000000000000000000000000001, 600000000 * 10 ** decimals());
        // Royalty logic would be custom, e.g., 8% to 0x996994...
    }
}
