"""Payout Settlement Service models."""

from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Optional


class PayoutStatus(str, Enum):
    queued = "queued"
    processing = "processing"
    settled = "settled"
    failed = "failed"


@dataclass(frozen=True)
class SettlementInput:
    """Input model for payout settlement."""

    claim_id: str
    recommended_action: str  # from fraud engine: auto_pay, manual_review, auto_deny
    payout_amount: float
    destination_handle: str
    initiated_at: datetime = None

    def __post_init__(self):
        if self.initiated_at is None:
            object.__setattr__(self, "initiated_at", datetime.utcnow())


@dataclass(frozen=True)
class PayoutInstruction:
    """Payout instruction output matching domain PayoutInstruction model."""

    claim_id: str
    payout_reference: str
    destination_handle: str
    amount: float
    status: PayoutStatus
    initiated_at: datetime
    settled_at: Optional[datetime] = None
