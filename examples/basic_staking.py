import json

import example_utils

from hyperliquid.utils import constants

# Set to True to use Ledger hardware wallet for signing
USE_LEDGER = True 
LEDGER_ACCOUNT_PATH = "44'/60'/11'/0/0"  # Default Ethereum derivation path


def main():
    address, info, exchange = example_utils.setup(
        base_url=constants.MAINNET_API_URL,
        skip_ws=True,
        use_ledger=USE_LEDGER,
        ledger_account_path=LEDGER_ACCOUNT_PATH,
    )

    # Get the user staking summary and print information
    user_staking_summary = info.user_staking_summary(address)
    print("Staking summary:")
    print(json.dumps(user_staking_summary, indent=2))

    # Get the user staking delegations and print information
    user_delegations = info.user_staking_delegations(address)
    print("Staking breakdown:")
    print(json.dumps(user_delegations, indent=2))

    # Get the user staking reward history and print information
    user_staking_rewards = info.user_staking_rewards(address)
    print("Most recent staking rewards:")
    print(json.dumps(user_staking_rewards[:5], indent=2))


if __name__ == "__main__":
    main()
