from pymongo.errors import DuplicateKeyError

from app.models.documents import Customer
from app.repositories.base import Repository, strip_id


class CustomerRepository(Repository):
    @property
    def col(self):
        return self.db["customers"]

    async def create(self, customer: Customer) -> bool:
        """Return False if the customer_id already exists."""
        try:
            await self.col.insert_one(customer.model_dump())
            return True
        except DuplicateKeyError:
            return False

    async def get(self, customer_id: str) -> Customer | None:
        doc = strip_id(await self.col.find_one({"customer_id": customer_id}))
        return Customer.model_validate(doc) if doc else None

    async def get_many(self, customer_ids: list[str]) -> dict[str, Customer]:
        if not customer_ids:
            return {}
        cursor = self.col.find({"customer_id": {"$in": customer_ids}})
        found = [Customer.model_validate(strip_id(d)) async for d in cursor]
        return {c.customer_id: c for c in found}
