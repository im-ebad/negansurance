"""Razorpay client wrapper for payment operations."""

import os
from typing import Optional

import razorpay


class RazorpayClient:
    def __init__(
        self,
        key_id: Optional[str] = None,
        key_secret: Optional[str] = None,
        test_mode: bool = True,
    ):
        self.key_id = key_id or os.getenv("RAZORPAY_KEY_ID")
        self.key_secret = key_secret or os.getenv("RAZORPAY_KEY_SECRET")
        self.test_mode = test_mode or os.getenv("RAZORPAY_MODE") == "sandbox"

        if not self.key_id or not self.key_secret:
            raise ValueError("Razorpay credentials not configured")

        self.client = razorpay.Client(auth=(self.key_id, self.key_secret))

    def create_payment(
        self,
        amount: int,
        currency: str = "INR",
        fund_account_id: Optional[str] = None,
        account_id: Optional[str] = None,
        reference_id: Optional[str] = None,
        notes: Optional[dict] = None,
    ) -> dict:

        if self.test_mode:
            return self._mock_payment_response(reference_id)

        if fund_account_id:
            return self.client.payment.create(
                {
                    "amount": amount,
                    "currency": currency,
                    "fund_account_id": fund_account_id,
                    "reference_id": reference_id,
                    "notes": notes or {},
                }
            )
        elif account_id:
            return self.client.transfer.create(
                {
                    "amount": amount,
                    "currency": currency,
                    "account": account_id,
                    "notes": notes or {},
                }
            )
        else:
            raise ValueError("Either fund_account_id or account_id required")

    def _mock_payment_response(self, reference_id: Optional[str]) -> dict:
        """Generate mock payment response for test mode."""
        import time

        return {
            "id": f"pay_{int(time.time())}",
            "entity": "payment",
            "amount": 0,
            "currency": "INR",
            "status": "captured",
            "reference_id": reference_id,
        }

    def get_payment(self, payment_id: str) -> dict:
        """Get payment details by ID."""
        return self.client.payment.fetch(payment_id)
