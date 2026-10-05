from dataclasses import dataclass
from uuid import uuid4


@dataclass(frozen=True)
class MockPaymentResult:
    succeeded: bool
    provider_reference: str
    card_brand: str
    card_last4: str


class MockPaymentGateway:
    """Deterministic local adapter; never persists or logs card credentials."""

    SUCCESS_CARD = "4242424242424242"
    DECLINED_CARD = "4000000000000002"

    def authorize(
        self, card_number: str, expiry_month: int, expiry_year: int, cvv: str
    ) -> MockPaymentResult:
        card_brand = self._card_brand(card_number)
        return MockPaymentResult(
            succeeded=card_number == self.SUCCESS_CARD,
            provider_reference=f"mock_{uuid4().hex}",
            card_brand=card_brand,
            card_last4=card_number[-4:],
        )

    @staticmethod
    def _card_brand(card_number: str) -> str:
        if card_number.startswith("4"):
            return "Visa"
        if card_number.startswith(("34", "37")):
            return "American Express"
        if card_number.startswith(("51", "52", "53", "54", "55")):
            return "Mastercard"
        if card_number.startswith(("6011", "65")):
            return "Discover"
        return "Unknown"
