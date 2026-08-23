from enum import StrEnum

from pymongo.errors import DuplicateKeyError

from app.domain.enums import InvoiceStatus
from app.models.documents import Invoice
from app.repositories.base import Repository, strip_id


class InsertOutcome(StrEnum):
    CREATED = "created"
    DUPLICATE_INVOICE = "duplicate_invoice"
    DUPLICATE_BILLING_CYCLE = "duplicate_billing_cycle"


class InvoiceRepository(Repository):
    @property
    def col(self):
        return self.db["invoices"]

    async def insert(self, invoice: Invoice) -> InsertOutcome:
        """Insert an invoice, distinguishing the two ways it can already exist.

        A repeated invoice_id is a replay. A different invoice_id for a
        billing cycle that is already invoiced is a genuine conflict — the
        platform believes it is billing the same period twice — and the caller
        must be able to tell those apart.
        """
        try:
            await self.col.insert_one(invoice.model_dump())
            return InsertOutcome.CREATED
        except DuplicateKeyError as exc:
            index_name = (exc.details or {}).get("keyPattern", {})
            if "invoice_id" in index_name:
                return InsertOutcome.DUPLICATE_INVOICE
            return InsertOutcome.DUPLICATE_BILLING_CYCLE

    async def get(self, invoice_id: str) -> Invoice | None:
        doc = strip_id(await self.col.find_one({"invoice_id": invoice_id}))
        return Invoice.model_validate(doc) if doc else None

    async def mark_paid(self, invoice_id: str) -> bool:
        """Returns True only if this call performed the transition to PAID."""
        result = await self.col.update_one(
            {"invoice_id": invoice_id, "status": InvoiceStatus.ISSUED_UNPAID.value},
            {"$set": {"status": InvoiceStatus.PAID.value}},
        )
        return result.modified_count > 0

    async def list_for_ids(self, invoice_ids: list[str]) -> list[Invoice]:
        if not invoice_ids:
            return []
        cursor = self.col.find({"invoice_id": {"$in": invoice_ids}}).sort(
            [("period_start", 1)]
        )
        return [Invoice.model_validate(strip_id(d)) async for d in cursor]

    async def list_for_subscription(self, subscription_id: str) -> list[Invoice]:
        cursor = self.col.find({"subscription_id": subscription_id}).sort(
            [("period_start", 1)]
        )
        return [Invoice.model_validate(strip_id(d)) async for d in cursor]
