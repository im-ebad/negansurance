"""Payout Settlement Service - orchestrates payouts via Razorpay."""

import logging
from datetime import datetime
from typing import Optional

from .client import RazorpayClient
from .models import PayoutStatus, PayoutInstruction, SettlementInput

logger = logging.getLogger(__name__)


class SettlementError(Exception):
    """Raised when settlement fails."""

    pass


class PayoutSettlementService:
    """Service for settling claim payouts via Razorpay."""

    def __init__(self, razorpay_client: Optional[RazorpayClient] = None):
        self.razorpay = razorpay_client or RazorpayClient()
        self._payouts: dict[str, PayoutInstruction] = {}

    def enqueue(
        self,
        claim_id: str,
        recommended_action: str,
        payout_amount: float,
        destination_handle: str,
    ) -> PayoutInstruction:
        """Enqueue a payout - compatible with PayoutService.enqueue signature.

        Args:
            claim_id: The claim ID
            recommended_action: Action from fraud engine (auto_pay, manual_review, auto_deny)
            payout_amount: Amount to payout
            destination_handle: Destination handle (va_*, acc_*)

        Returns:
            PayoutInstruction
        """
        input_data = SettlementInput(
            claim_id=claim_id,
            recommended_action=recommended_action,
            payout_amount=payout_amount,
            destination_handle=destination_handle,
        )

        instruction = self.settle(input_data)
        self._payouts[claim_id] = instruction
        return instruction

    def settle(self, input_data: SettlementInput) -> PayoutInstruction:
        """Process a settlement for the given claim decision.

        Args:
            input_data: SettlementInput with claim details

        Returns:
            PayoutInstruction matching domain PayoutInstruction model
        """
        claim_id = input_data.claim_id
        payout_amount = input_data.payout_amount
        destination_handle = input_data.destination_handle
        recommended_action = input_data.recommended_action
        initiated_at = input_data.initiated_at

        payout_reference = f"PYT-{claim_id[-6:]}"

        logger.info(
            "Processing settlement for claim=%s action=%s amount=%.2f",
            claim_id,
            recommended_action,
            payout_amount,
        )

        if recommended_action == "auto_pay":
            return self._settle_auto_pay(
                claim_id,
                payout_reference,
                destination_handle,
                payout_amount,
                initiated_at,
            )
        elif recommended_action == "manual_review":
            return self._settle_pending_review(
                claim_id,
                payout_reference,
                destination_handle,
                payout_amount,
                initiated_at,
            )
        else:
            return self._settle_failed(
                claim_id,
                payout_reference,
                destination_handle,
                payout_amount,
                initiated_at,
            )

    def _settle_auto_pay(
        self,
        claim_id: str,
        payout_reference: str,
        destination_handle: str,
        payout_amount: float,
        initiated_at: datetime,
    ) -> PayoutInstruction:
        """Handle auto_pay settlement - call Razorpay and return settled or failed."""
        if payout_amount <= 0:
            logger.warning("auto_pay with zero amount for claim=%s", claim_id)
            return PayoutInstruction(
                claim_id=claim_id,
                payout_reference=payout_reference,
                destination_handle=destination_handle,
                amount=payout_amount,
                status=PayoutStatus.failed,
                initiated_at=initiated_at,
                settled_at=None,
            )

        try:
            self._create_razorpay_payment(
                destination_handle, payout_amount, payout_reference, claim_id
            )

            logger.info("Successfully settled claim=%s", claim_id)
            return PayoutInstruction(
                claim_id=claim_id,
                payout_reference=payout_reference,
                destination_handle=destination_handle,
                amount=payout_amount,
                status=PayoutStatus.settled,
                initiated_at=initiated_at,
                settled_at=datetime.utcnow(),
            )

        except Exception as e:
            logger.exception("Razorpay payment failed for claim=%s", claim_id)
            return PayoutInstruction(
                claim_id=claim_id,
                payout_reference=payout_reference,
                destination_handle=destination_handle,
                amount=payout_amount,
                status=PayoutStatus.failed,
                initiated_at=initiated_at,
                settled_at=None,
            )

    def _settle_pending_review(
        self,
        claim_id: str,
        payout_reference: str,
        destination_handle: str,
        payout_amount: float,
        initiated_at: datetime,
    ) -> PayoutInstruction:
        """Handle manual_review - mark as queued for manual processing."""
        logger.info("Claim=%s requires manual review", claim_id)
        return PayoutInstruction(
            claim_id=claim_id,
            payout_reference=payout_reference,
            destination_handle=destination_handle,
            amount=payout_amount,
            status=PayoutStatus.queued,
            initiated_at=initiated_at,
            settled_at=None,
        )

    def _settle_failed(
        self,
        claim_id: str,
        payout_reference: str,
        destination_handle: str,
        payout_amount: float,
        initiated_at: datetime,
    ) -> PayoutInstruction:
        """Handle auto_deny or other failed states."""
        logger.info("Claim=%s denied", claim_id)
        return PayoutInstruction(
            claim_id=claim_id,
            payout_reference=payout_reference,
            destination_handle=destination_handle,
            amount=payout_amount,
            status=PayoutStatus.failed,
            initiated_at=initiated_at,
            settled_at=None,
        )

    def _create_razorpay_payment(
        self,
        destination_handle: str,
        amount: float,
        reference: str,
        claim_id: str,
    ) -> dict:
        """Create payment via Razorpay based on handle type."""
        amount_in_paise = int(amount * 100)

        if destination_handle.startswith("va_"):
            return self.razorpay.create_payment(
                amount=amount_in_paise,
                fund_account_id=destination_handle,
                reference_id=reference,
                notes={"claim_id": claim_id},
            )
        elif destination_handle.startswith("acc_"):
            return self.razorpay.create_payment(
                amount=amount_in_paise,
                account_id=destination_handle,
                reference_id=reference,
                notes={"claim_id": claim_id},
            )
        else:
            raise SettlementError(f"Invalid destination handle: {destination_handle}")

    def get(self, claim_id: str) -> Optional[PayoutInstruction]:
        """Retrieve payout instruction by claim ID."""
        return self._payouts.get(claim_id)
