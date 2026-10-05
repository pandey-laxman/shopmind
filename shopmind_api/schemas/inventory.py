from pydantic import BaseModel, ConfigDict, Field


class InventoryUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    quantity: int = Field(ge=0, le=2147483647, strict=True)


class InventoryResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    product_id: int
    quantity: int
    is_in_stock: bool
