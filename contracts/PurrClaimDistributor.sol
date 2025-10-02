// SPDX-License-Identifier: MIT
pragma solidity 0.8.28;

import "@openzeppelin/contracts/utils/cryptography/MerkleProof.sol";
import "@openzeppelin/contracts/token/ERC20/IERC20.sol";

contract PurrClaimDistributor {
    bytes32 public merkleRoot;
    IERC20 public purr;
    mapping(address => bool) public claimed;

    constructor(bytes32 _root, address token) {
        merkleRoot = _root;
        purr = IERC20(token);
    }

    function claim(uint256 amount, bytes32[] calldata proof) external {
        require(!claimed[msg.sender], "Already claimed");

        bytes32 leaf = keccak256(abi.encodePacked(msg.sender, amount));
        require(MerkleProof.verify(proof, merkleRoot, leaf), "Invalid proof");

        claimed[msg.sender] = true;
        purr.transfer(msg.sender, amount);
    }
}
