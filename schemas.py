"""
Database Schemas for Restaurant POS

Each Pydantic model represents a collection in your database.
Class name lowercased is used as the collection name.
"""
from typing import List, Optional
from pydantic import BaseModel, Field

class MenuItem(BaseModel):
    name: str = Field(..., description="Dish name")
    price: float = Field(..., ge=0, description="Unit price")
    category: Optional[str] = Field(None, description="Menu category, e.g., Mains, Drinks")
    is_available: bool = Field(True, description="Whether item is available")

class OrderItem(BaseModel):
    item_id: str = Field(..., description="Menu item _id as string")
    name: str = Field(..., description="Menu item name snapshot")
    quantity: int = Field(..., ge=1, description="Quantity ordered")
    unit_price: float = Field(..., ge=0, description="Unit price at time of order")
    notes: Optional[str] = Field(None, description="Special instructions")

class Order(BaseModel):
    table_number: Optional[str] = Field(None, description="Table number or customer name for pickup")
    items: List[OrderItem] = Field(..., description="List of ordered items")
    subtotal: float = Field(..., ge=0)
    tax: float = Field(..., ge=0)
    total: float = Field(..., ge=0)
    status: str = Field("open", description="open, paid, void")
    payment_method: Optional[str] = Field(None, description="cash, card, etc.")
