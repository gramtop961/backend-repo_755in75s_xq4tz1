import os
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from typing import List
from bson import ObjectId

from database import db, create_document, get_documents
from schemas import MenuItem, Order, OrderItem

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Utility to convert Mongo documents to serializable dicts

def serialize_doc(doc):
    if not doc:
        return doc
    d = dict(doc)
    if "_id" in d:
        d["_id"] = str(d["_id"])
    return d


@app.get("/")
def read_root():
    return {"message": "Restaurant POS Backend Running"}


@app.get("/test")
def test_database():
    response = {
        "backend": "✅ Running",
        "database": "❌ Not Available",
        "database_url": None,
        "database_name": None,
        "connection_status": "Not Connected",
        "collections": []
    }

    try:
        if db is not None:
            response["database"] = "✅ Available"
            response["database_url"] = "✅ Set" if os.getenv("DATABASE_URL") else "❌ Not Set"
            response["database_name"] = db.name if hasattr(db, 'name') else "✅ Connected"
            response["connection_status"] = "Connected"
            try:
                collections = db.list_collection_names()
                response["collections"] = collections[:10]
                response["database"] = "✅ Connected & Working"
            except Exception as e:
                response["database"] = f"⚠️ Connected but Error: {str(e)[:80]}"
        else:
            response["database"] = "⚠️ Available but not initialized"
    except Exception as e:
        response["database"] = f"❌ Error: {str(e)[:80]}"

    return response


# ============ MENU ENDPOINTS ============
@app.get("/menu")
def list_menu():
    items = get_documents("menuitem")
    return [serialize_doc(i) for i in items]


@app.post("/menu", status_code=201)
def add_menu_item(item: MenuItem):
    inserted_id = create_document("menuitem", item)
    doc = db["menuitem"].find_one({"_id": ObjectId(inserted_id)})
    return serialize_doc(doc)


# ============ ORDER ENDPOINTS ============
@app.get("/orders")
def list_orders():
    orders = get_documents("order")
    return [serialize_doc(o) for o in orders]


@app.get("/orders/{order_id}")
def get_order(order_id: str):
    try:
        doc = db["order"].find_one({"_id": ObjectId(order_id)})
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid order id")
    if not doc:
        raise HTTPException(status_code=404, detail="Order not found")
    return serialize_doc(doc)


@app.post("/orders", status_code=201)
def create_order(order: Order):
    # Basic validation and recompute totals to avoid tampering
    subtotal = sum(oi.quantity * oi.unit_price for oi in order.items)
    tax = round(subtotal * 0.1, 2)  # 10% tax example
    total = round(subtotal + tax, 2)

    order_data = order.model_dump()
    order_data["subtotal"] = round(subtotal, 2)
    order_data["tax"] = tax
    order_data["total"] = total

    inserted_id = create_document("order", order_data)
    doc = db["order"].find_one({"_id": ObjectId(inserted_id)})
    return serialize_doc(doc)


@app.get("/orders/{order_id}/receipt")
def get_receipt(order_id: str):
    try:
        order = db["order"].find_one({"_id": ObjectId(order_id)})
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid order id")
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")

    order = serialize_doc(order)

    # Build plain-text receipt; frontend can render nicely and print
    lines = []
    lines.append("=== Restaurant Receipt ===")
    lines.append(f"Order: {order['_id']}")
    if order.get("table_number"):
        lines.append(f"Table/Name: {order['table_number']}")
    lines.append("")
    for it in order.get("items", []):
        name = it.get("name", "Item")
        qty = it.get("quantity", 1)
        price = it.get("unit_price", 0)
        total = round(qty * price, 2)
        lines.append(f"{name} x{qty}  ${total:.2f}")
        if it.get("notes"):
            lines.append(f"  - {it['notes']}")
    lines.append("")
    lines.append(f"Subtotal: ${order.get('subtotal', 0):.2f}")
    lines.append(f"Tax: ${order.get('tax', 0):.2f}")
    lines.append(f"Total: ${order.get('total', 0):.2f}")
    if order.get("payment_method"):
        lines.append(f"Payment: {order['payment_method']}")
    lines.append("==========================")

    return {"receipt_text": "\n".join(lines), "order": order}


if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
