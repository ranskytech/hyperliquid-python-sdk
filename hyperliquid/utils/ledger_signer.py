from ledgereth.accounts import get_account_by_path
from ledgereth.objects import LedgerAccount
from ledgereth.messages import sign_typed_data_draft
from eth_account.messages import encode_typed_data
from eth_utils import to_hex


class LedgerSigner:
    """
    A wallet wrapper that uses a Ledger hardware device for signing.
    Mimics the interface expected by the Hyperliquid SDK.
    """

    def __init__(self, account_path: str = "44'/60'/0'/0/0"):
        """
        Initialize the Ledger signer.

        Args:
            account_path: BIP44 derivation path (default is first Ethereum account)
        """
        self._account_path = account_path
        # Get account from the Ledger device using the specified derivation path
        try:
            self._account: LedgerAccount = get_account_by_path(account_path)
            print(f"Ledger address: {self._account.address}")
        except Exception as e:
            raise RuntimeError(
                f"Failed to connect to Ledger device: {e}\n"
                "Make sure your Ledger is: "
                "1) Connected via USB, 2) Unlocked, 3) Ethereum app is open"
            ) from e

    @property
    def address(self) -> str:
        """Return the Ethereum address from the Ledger."""
        return self._account.address

    def sign_typed_data(self, typed_data: dict) -> dict:
        """
        Sign EIP-712 typed data directly with the Ledger.

        Args:
            typed_data: Dict containing domain, types, primaryType, message

        Returns:
            Dict with r, s, v signature components
        """
        # Use full_message form to preserve primaryType (important for L1 actions)
        # This ensures the encoding matches what the verifier expects
        signable = encode_typed_data(full_message=typed_data)

        # Pass raw bytes - ledgereth expects 32-byte hashes, not hex strings
        domain_hash = bytes(signable.header)
        message_hash = bytes(signable.body)

        # Sign with Ledger using the pre-computed hashes
        signed = sign_typed_data_draft(
            domain_hash=domain_hash,
            message_hash=message_hash,
            sender_path=self._account_path,
        )

        return {
            "r": to_hex(signed.r),
            "s": to_hex(signed.s),
            "v": signed.v,
        }