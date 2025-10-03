// SPDX-License-Identifier: UNLICENSED
pragma solidity ^0.8.20;

import "@openzeppelin/contracts/utils/cryptography/ECDSA.sol";

contract VaultScannerV2WithSig {
    using ECDSA for bytes32;

    address public immutable keeper;
    uint256 public royaltyPercent;

    struct VaultRecord {
        bytes32 vaultId;
        uint256 balance;
        bytes32 attributionHash;
        uint256 timestamp;
    }

    mapping(address => VaultRecord[]) private vaults;
    mapping(address => mapping(bytes32 => bool)) public claimed;

    event VaultClaimed(address indexed user, bytes32 indexed vaultId, uint256 balance, bytes32 attributionHash);
    event ClaimLog(bytes32 indexed claimHash, address indexed user, uint256 value);

    constructor(address _keeper, uint256 _royaltyPercent) {
        keeper = _keeper;
        royaltyPercent = _royaltyPercent;
    }

    function claimVault(
        address user,
        bytes32 vaultId,
        uint256 balance,
        bytes32 attributionHash
    ) external {
        require(msg.sender == keeper, "Not Keeper");
        _internalClaim(user, vaultId, balance, attributionHash);
    }

    function claimVaultWithSig(
        address user,
        bytes32 vaultId,
        uint256 balance,
        bytes32 attributionHash,
        bytes memory signature
    ) external {
        bytes32 digest = keccak256(abi.encodePacked(user, vaultId, balance, attributionHash)).toEthSignedMessageHash();
        address recovered = digest.recover(signature);
        require(recovered == keeper, "Invalid signature");
        _internalClaim(user, vaultId, balance, attributionHash);
    }

    function _internalClaim(
        address user,
        bytes32 vaultId,
        uint256 balance,
        bytes32 attributionHash
    ) internal {
        require(!claimed[user][vaultId], "Already claimed");

        VaultRecord memory vr = VaultRecord({
            vaultId: vaultId,
            balance: balance,
            attributionHash: attributionHash,
            timestamp: block.timestamp
        });

        vaults[user].push(vr);
        claimed[user][vaultId] = true;

        emit VaultClaimed(user, vaultId, balance, attributionHash);
        emit ClaimLog(keccak256(abi.encodePacked(user, vaultId, balance, attributionHash)), user, balance);
    }

    function getVaults(address user) external view returns (VaultRecord[] memory) {
        return vaults[user];
    }

    function totalVaults(address user) external view returns (uint256) {
        return vaults[user].length;
    }

    function getVaultByIndex(address user, uint256 index) external view returns (VaultRecord memory) {
        return vaults[user][index];
    }
}