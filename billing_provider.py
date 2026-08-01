"""Payment-provider boundary for canonical NinaOS Billing V1."""

from dataclasses import dataclass


@dataclass(frozen=True)
class ProviderResult:
    ok: bool
    reference: str = ""
    status: str = "not_configured"


class NullBillingProvider:
    key = "none"

    def create_customer(self, workspace_id, **details):
        return ProviderResult(False)

    def create_invoice(self, workspace_id, amount_minor, currency, **details):
        return ProviderResult(False)

    create_checkout_session = create_customer
    create_subscription = create_customer
    cancel_subscription = create_customer
    fetch_subscription = create_customer
    fetch_invoice = create_customer
    def verify_webhook(self, payload, signature): return False
    def map_provider_status(self, status): return "incomplete"


class ManualBillingProvider:
    key = "manual"

    def create_customer(self, workspace_id, **details):
        return ProviderResult(True, f"manual:{workspace_id}", "active")

    def create_invoice(self, workspace_id, amount_minor, currency, **details):
        reference = str(details.get("reference") or "manual")
        return ProviderResult(True, reference, "pending")

    create_subscription = create_customer
    cancel_subscription = create_customer
    fetch_subscription = create_customer
    fetch_invoice = create_customer
    def create_checkout_session(self, *args, **kwargs): return ProviderResult(False)
    def verify_webhook(self, payload, signature): return False
    def map_provider_status(self, status):
        return str(status or "incomplete").lower() if str(status or "").lower() in {"trialing","active","past_due","suspended","cancelled","expired","incomplete"} else "incomplete"


def billing_provider(name=None):
    return ManualBillingProvider() if str(name or "").lower() == "manual" else NullBillingProvider()
