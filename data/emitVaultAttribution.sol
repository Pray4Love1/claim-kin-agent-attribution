// SPDX-License-Identifier: UNLICENSED
pragma solidity ^0.8.0;

contract VaultAttribution {
    event VaultAttribution(bytes32 commitHash, string author);

    function record(bytes32 commitHash) public {
        emit VaultAttribution(commitHash, "Jon S.");
    }
}
