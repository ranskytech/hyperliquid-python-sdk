#!/usr/bin/env python3
"""
Command-line interface for Hyperliquid staking and validator operations.

Examples:
    # Deposit 1 HYPE into staking using Ledger (account 0)
    python -m hyperliquid.cli cDeposit --wei 100000000 --ledger-account 0

    # Withdraw from staking using Ledger (account 11)
    python -m hyperliquid.cli cWithdraw --wei 100000000 --ledger-account 11

    # Jail self (validator signer action)
    python -m hyperliquid.cli cSignerJailSelf --ledger-account 0

    # Unjail self (validator signer action)
    python -m hyperliquid.cli cSignerUnjailSelf --ledger-account 0

    # Register a validator
    python -m hyperliquid.cli cValidatorRegister --ledger-account 0 --json '{
        "node_ip": "1.2.3.4",
        "name": "My Validator",
        "description": "A great validator",
        "delegations_disabled": false,
        "commission_bps": 1000,
        "signer": "0x...",
        "unjailed": true,
        "initial_wei": 100000000
    }'

    # Change validator profile
    python -m hyperliquid.cli cValidatorChangeProfile --ledger-account 0 --json '{
        "node_ip": "1.2.3.4",
        "name": null,
        "description": null,
        "unjailed": true,
        "disable_delegations": null,
        "commission_bps": null,
        "signer": null
    }'

    # Unregister validator
    python -m hyperliquid.cli cValidatorUnregister --ledger-account 0

    # Use testnet
    python -m hyperliquid.cli cDeposit --wei 100000000 --ledger-account 0 --testnet
"""

import argparse
import json
import sys

from hyperliquid.exchange import Exchange
from hyperliquid.utils.constants import MAINNET_API_URL, TESTNET_API_URL
from hyperliquid.utils.ledger_signer import LedgerSigner


def get_ledger_account_path(account_index: int) -> str:
    """Convert account index to BIP44 derivation path."""
    return f"44'/60'/{account_index}'/0/0"


def normalize_validator_register_params(params: dict) -> dict:
    """
    Normalize cValidatorRegister params to flat format.
    Supports both flat format and nested API format.
    """
    # Check if it's the nested API format
    if "register" in params:
        reg = params["register"]
        profile = reg.get("profile", {})
        # Extract node_ip from {"Ip": "..."} format if present
        node_ip = profile.get("node_ip")
        if isinstance(node_ip, dict) and "Ip" in node_ip:
            node_ip = node_ip["Ip"]
        return {
            "node_ip": node_ip,
            "name": profile.get("name"),
            "description": profile.get("description"),
            "delegations_disabled": profile.get("delegations_disabled", False),
            "commission_bps": profile.get("commission_bps", 0),
            "signer": profile.get("signer"),
            "unjailed": reg.get("unjailed", True),
            "initial_wei": reg.get("initial_wei"),
        }
    # Already flat format, but handle node_ip if it's {"Ip": "..."} format
    if isinstance(params.get("node_ip"), dict) and "Ip" in params["node_ip"]:
        params = params.copy()
        params["node_ip"] = params["node_ip"]["Ip"]
    return params


def normalize_validator_change_profile_params(params: dict) -> dict:
    """
    Normalize cValidatorChangeProfile params to flat format.
    Supports both flat format and nested API format.
    """
    # Check if it's the nested API format
    if "changeProfile" in params:
        cp = params["changeProfile"]
        # Extract node_ip from {"Ip": "..."} format if present
        node_ip = cp.get("node_ip")
        if isinstance(node_ip, dict) and "Ip" in node_ip:
            node_ip = node_ip["Ip"]
        return {
            "node_ip": node_ip,
            "name": cp.get("name"),
            "description": cp.get("description"),
            "unjailed": cp.get("unjailed", True),
            "disable_delegations": cp.get("disable_delegations"),
            "commission_bps": cp.get("commission_bps"),
            "signer": cp.get("signer"),
        }
    # Already flat format, but handle node_ip if it's {"Ip": "..."} format
    if isinstance(params.get("node_ip"), dict) and "Ip" in params["node_ip"]:
        params = params.copy()
        params["node_ip"] = params["node_ip"]["Ip"]
    return params


def confirm_action(action_description: str) -> None:
    """Print action details and wait for user confirmation before signing."""
    print()
    print("=" * 50)
    print(f"Action: {action_description}")
    print("=" * 50)
    print()
    input("Press Enter to continue to signing (Ctrl+C to cancel)...")


def main():
    parser = argparse.ArgumentParser(
        description="Hyperliquid CLI for staking and validator operations",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Deposit 1 HYPE into staking (1 HYPE = 1e8 wei)
  python -m hyperliquid.cli cDeposit --wei 100000000 --ledger-account 0

  # Withdraw 0.5 HYPE from staking
  python -m hyperliquid.cli cWithdraw --wei 50000000 --ledger-account 0

  # Jail self (validator signer action)
  python -m hyperliquid.cli cSignerJailSelf --ledger-account 0

  # Unjail self (validator signer action)
  python -m hyperliquid.cli cSignerUnjailSelf --ledger-account 0

  # Register a validator (see --help for JSON format)
  python -m hyperliquid.cli cValidatorRegister --ledger-account 0 --json '{"node_ip": "1.2.3.4", ...}'

  # Change validator profile
  python -m hyperliquid.cli cValidatorChangeProfile --ledger-account 0 --json '{"unjailed": true, ...}'

  # Unregister validator
  python -m hyperliquid.cli cValidatorUnregister --ledger-account 0

  # Use testnet
  python -m hyperliquid.cli cDeposit --wei 100000000 --ledger-account 0 --testnet
        """,
    )

    parser.add_argument(
        "command",
        choices=[
            "cDeposit",
            "cWithdraw",
            "cSignerJailSelf",
            "cSignerUnjailSelf",
            "cValidatorRegister",
            "cValidatorChangeProfile",
            "cValidatorUnregister",
        ],
        help="Command to execute",
    )
    parser.add_argument(
        "--wei",
        type=int,
        required=False,
        help="Amount in wei (1 HYPE = 1e8 wei). Required for cDeposit/cWithdraw.",
    )
    parser.add_argument(
        "--json",
        type=str,
        required=False,
        help="JSON parameters for validator actions (cValidatorRegister, cValidatorChangeProfile).",
    )
    parser.add_argument(
        "--ledger-account",
        type=int,
        required=True,
        help="Ledger account index (e.g., 0 for first account, 11 for twelfth)",
    )
    parser.add_argument(
        "--testnet",
        action="store_true",
        help="Use testnet instead of mainnet",
    )

    args = parser.parse_args()

    # Setup Ledger
    account_path = get_ledger_account_path(args.ledger_account)
    print(f"Connecting to Ledger device (account path: {account_path})...")

    try:
        wallet = LedgerSigner(account_path=account_path)
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)

    # Setup Exchange
    network = "TESTNET" if args.testnet else "MAINNET"
    base_url = TESTNET_API_URL if args.testnet else MAINNET_API_URL
    print(f"Network: {network}")
    exchange = Exchange(wallet, base_url)

    # Validate arguments based on command
    if args.command in ["cDeposit", "cWithdraw"] and args.wei is None:
        print(f"Error: --wei is required for {args.command}", file=sys.stderr)
        sys.exit(1)

    if args.command in ["cValidatorRegister", "cValidatorChangeProfile"] and args.json is None:
        print(f"Error: --json is required for {args.command}", file=sys.stderr)
        sys.exit(1)

    # Parse JSON if provided
    json_params = None
    if args.json:
        try:
            json_params = json.loads(args.json)
        except json.JSONDecodeError as e:
            print(f"Error: Invalid JSON: {e}", file=sys.stderr)
            sys.exit(1)

        # Normalize JSON params based on command
        if args.command == "cValidatorRegister":
            json_params = normalize_validator_register_params(json_params)
        elif args.command == "cValidatorChangeProfile":
            json_params = normalize_validator_change_profile_params(json_params)

    # Build action description and confirm before signing
    if args.command == "cDeposit":
        action_desc = f"Deposit {args.wei} wei into staking"
    elif args.command == "cWithdraw":
        action_desc = f"Withdraw {args.wei} wei from staking"
    elif args.command == "cSignerJailSelf":
        action_desc = "Jail self (validator signer)"
    elif args.command == "cSignerUnjailSelf":
        action_desc = "Unjail self (validator signer)"
    elif args.command == "cValidatorRegister":
        action_desc = f"Register validator: {json_params.get('name', 'unnamed')}"
    elif args.command == "cValidatorChangeProfile":
        action_desc = f"Change validator profile\n{json.dumps(json_params, indent=2)}"
    elif args.command == "cValidatorUnregister":
        action_desc = "Unregister validator"

    try:
        confirm_action(action_desc)
    except KeyboardInterrupt:
        print("\nCancelled.")
        sys.exit(0)

    # Execute command
    try:
        if args.command == "cDeposit":
            result = exchange.c_deposit(wei=args.wei)
        elif args.command == "cWithdraw":
            result = exchange.c_withdraw(wei=args.wei)
        elif args.command == "cSignerJailSelf":
            result = exchange.c_signer_jail_self()
        elif args.command == "cSignerUnjailSelf":
            result = exchange.c_signer_unjail_self()
        elif args.command == "cValidatorRegister":
            result = exchange.c_validator_register(
                node_ip=json_params["node_ip"],
                name=json_params["name"],
                description=json_params["description"],
                delegations_disabled=json_params["delegations_disabled"],
                commission_bps=json_params["commission_bps"],
                signer=json_params["signer"],
                unjailed=json_params["unjailed"],
                initial_wei=json_params["initial_wei"],
            )
        elif args.command == "cValidatorChangeProfile":
            result = exchange.c_validator_change_profile(
                node_ip=json_params.get("node_ip"),
                name=json_params.get("name"),
                description=json_params.get("description"),
                unjailed=json_params["unjailed"],
                disable_delegations=json_params.get("disable_delegations"),
                commission_bps=json_params.get("commission_bps"),
                signer=json_params.get("signer"),
            )
        elif args.command == "cValidatorUnregister":
            result = exchange.c_validator_unregister()

        print(json.dumps(result, indent=2))
    except KeyError as e:
        print(f"Error: Missing required JSON field: {e}", file=sys.stderr)
        if args.command == "cValidatorRegister":
            print("\nExpected JSON format for cValidatorRegister:", file=sys.stderr)
            print(json.dumps({
                "node_ip": "1.2.3.4",
                "name": "Validator Name",
                "description": "Description",
                "delegations_disabled": False,
                "commission_bps": 1000,
                "signer": "0x...",
                "unjailed": True,
                "initial_wei": 100000000,
            }, indent=2), file=sys.stderr)
        elif args.command == "cValidatorChangeProfile":
            print("\nExpected JSON format for cValidatorChangeProfile:", file=sys.stderr)
            print(json.dumps({
                "unjailed": True,
                "node_ip": "1.2.3.4 (optional)",
                "name": "null or string (optional)",
                "description": "null or string (optional)",
                "disable_delegations": "null or bool (optional)",
                "commission_bps": "null or int (optional)",
                "signer": "null or address (optional)",
            }, indent=2), file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
