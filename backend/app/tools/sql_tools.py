"""LangGraph SQL retrieval tools (parameterized queries only)."""

from langchain_core.tools import tool

from app.tools.compact import compact_json
from sqlalchemy import select

from app.agents.context import get_agent_db
from app.models.tables import (
    Customer,
    Delivery,
    Inspection,
    Order,
    OrderItem,
    Product,
    ProductUnit,
    Refund,
    Return,
    ReturnShipment,
)
from app.services.refundable import calculate_refundable_amount_paise
from app.services.return_workflow import build_return_workflow_snapshot


@tool
def get_return_workflow_status(return_id: str) -> str:
    """Current workflow for all personas: warehouse step, inspection count, analyst queue stage.

    Call this for status questions after any persona completes a step — data is read live from SQLite."""
    session = get_agent_db()
    return compact_json(build_return_workflow_snapshot(session, return_id))


@tool
def get_return_details(return_id: str) -> str:
    """Fetch a return record and its status from SQLite."""
    session = get_agent_db()
    session.expire_all()
    row = session.get(Return, return_id)
    if row is None:
        return compact_json({"error": "return_not_found", "return_id": return_id})
    workflow = build_return_workflow_snapshot(session, return_id)
    return compact_json(
        {
            "return_id": row.return_id,
            "order_item_id": row.order_item_id,
            "return_reason": row.return_reason,
            "return_status": row.return_status,
            "request_date": row.request_date,
            "received_date": row.received_date,
            "requested_resolution": row.requested_resolution,
            "customer_description": row.customer_description,
            "workflow": workflow,
        }
    )


@tool
def get_order_details(order_id: str) -> str:
    """Fetch order header and line items."""
    session = get_agent_db()
    order = session.get(Order, order_id)
    if order is None:
        return compact_json({"error": "order_not_found", "order_id": order_id})
    items = session.execute(select(OrderItem).where(OrderItem.order_id == order_id)).scalars().all()
    return compact_json(
        {
            "order_id": order.order_id,
            "customer_id": order.customer_id,
            "order_date": order.order_date,
            "total_amount_paise": order.total_amount,
            "order_status": order.order_status,
            "items": [
                {
                    "order_item_id": item.order_item_id,
                    "product_id": item.product_id,
                    "quantity": item.quantity,
                    "unit_price_paise": item.unit_price,
                    "purchased_serial_number": item.purchased_serial_number,
                }
                for item in items
            ],
        }
    )


@tool
def get_product_details(product_id: str) -> str:
    """Fetch product catalog metadata."""
    session = get_agent_db()
    product = session.get(Product, product_id)
    if product is None:
        return compact_json({"error": "product_not_found", "product_id": product_id})
    return compact_json(
        {
            "product_id": product.product_id,
            "product_name": product.product_name,
            "category": product.category,
            "brand": product.brand,
            "original_price_paise": product.original_price,
            "warranty_months": product.warranty_months,
            "serial_tracked": product.serial_tracked,
        }
    )


@tool
def get_delivery_details(order_id: str) -> str:
    """Fetch delivery record for an order."""
    session = get_agent_db()
    delivery = session.execute(select(Delivery).where(Delivery.order_id == order_id)).scalar_one_or_none()
    if delivery is None:
        return compact_json({"error": "delivery_not_found", "order_id": order_id})
    return compact_json(
        {
            "delivery_id": delivery.delivery_id,
            "order_id": delivery.order_id,
            "dispatch_date": delivery.dispatch_date,
            "delivery_date": delivery.delivery_date,
            "delivery_status": delivery.delivery_status,
            "delivery_issue": delivery.delivery_issue,
        }
    )


@tool
def get_inspection_results(return_id: str) -> str:
    """Fetch warehouse inspection rows for a return."""
    session = get_agent_db()
    session.expire_all()
    rows = session.execute(select(Inspection).where(Inspection.return_id == return_id)).scalars().all()
    items = [
        {
            "inspection_id": row.inspection_id,
            "inspection_date": row.inspection_date,
            "returned_serial_number": row.returned_serial_number,
            "product_condition": row.product_condition,
            "accessories_complete": row.accessories_complete,
            "defect_verified": row.defect_verified,
            "inspection_result": row.inspection_result,
            "inspector_notes": row.inspector_notes,
        }
        for row in rows
    ]
    workflow = build_return_workflow_snapshot(session, return_id)
    return compact_json(
        {
            "return_id": return_id,
            "inspection_count": len(items),
            "warehouse_work_complete": len(items) > 0,
            "inspections": items,
            "workflow": workflow,
        }
    )


@tool
def get_refund_status(return_id: str) -> str:
    """Fetch refund rows for a return."""
    session = get_agent_db()
    session.expire_all()
    rows = session.execute(select(Refund).where(Refund.return_id == return_id)).scalars().all()
    workflow = build_return_workflow_snapshot(session, return_id)
    return compact_json(
        {
            "refunds": [
                {
                    "refund_id": row.refund_id,
                    "refund_amount_paise": row.refund_amount,
                    "refund_status": row.refund_status,
                    "approval_status": row.approval_status,
                    "processed_date": row.processed_date,
                }
                for row in rows
            ],
            "workflow": workflow,
        }
    )


@tool
def get_customer_return_history(customer_id: str) -> str:
    """List returns linked to a customer via their orders."""
    session = get_agent_db()
    customer = session.get(Customer, customer_id)
    if customer is None:
        return compact_json({"error": "customer_not_found", "customer_id": customer_id})

    order_ids = session.execute(select(Order.order_id).where(Order.customer_id == customer_id)).scalars().all()
    if not order_ids:
        return compact_json({"customer_id": customer_id, "returns": []})

    item_ids = session.execute(
        select(OrderItem.order_item_id).where(OrderItem.order_id.in_(order_ids))
    ).scalars().all()
    returns = session.execute(select(Return).where(Return.order_item_id.in_(item_ids))).scalars().all()
    return compact_json(
        {
            "customer_id": customer_id,
            "returns": [
                {
                    "return_id": row.return_id,
                    "return_status": row.return_status,
                    "return_reason": row.return_reason,
                    "request_date": row.request_date,
                }
                for row in returns
            ],
        }
    )


@tool
def get_order_item(order_item_id: int) -> str:
    """Fetch a single order line item."""
    session = get_agent_db()
    item = session.get(OrderItem, order_item_id)
    if item is None:
        return compact_json({"error": "order_item_not_found", "order_item_id": order_item_id})
    return compact_json(
        {
            "order_item_id": item.order_item_id,
            "order_id": item.order_id,
            "product_id": item.product_id,
            "quantity": item.quantity,
            "unit_price_paise": item.unit_price,
            "purchased_serial_number": item.purchased_serial_number,
        }
    )


@tool
def get_product_unit(serial_number: str) -> str:
    """Lookup a serialized product unit by serial number."""
    session = get_agent_db()
    unit = session.execute(
        select(ProductUnit).where(ProductUnit.serial_number == serial_number)
    ).scalar_one_or_none()
    if unit is None:
        return compact_json({"error": "unit_not_found", "serial_number": serial_number})
    return compact_json(
        {
            "product_unit_id": unit.product_unit_id,
            "order_item_id": unit.order_item_id,
            "serial_number": unit.serial_number,
            "unit_status": unit.unit_status,
        }
    )


@tool
def get_return_shipment(return_id: str) -> str:
    """Fetch return pickup / warehouse receipt shipment record."""
    session = get_agent_db()
    row = session.execute(
        select(ReturnShipment).where(ReturnShipment.return_id == return_id)
    ).scalar_one_or_none()
    if row is None:
        return compact_json({"return_id": return_id, "shipment": None})
    return compact_json(
        {
            "return_id": return_id,
            "tracking_id": row.tracking_id,
            "pickup_scheduled_at": row.pickup_scheduled_at,
            "pickup_completed_at": row.pickup_completed_at,
            "warehouse_received_at": row.warehouse_received_at,
            "receipt_discrepancy": row.receipt_discrepancy,
            "lost_in_transit": row.lost_in_transit,
        }
    )


@tool
def calculate_refundable_amount(return_id: str) -> str:
    """Deterministic remaining refundable amount for partial refunds."""
    session = get_agent_db()
    try:
        amounts = calculate_refundable_amount_paise(session, return_id)
    except ValueError as exc:
        return compact_json({"error": "not_found", "message": str(exc)})
    return compact_json(amounts)


SQL_TOOLS = [
    get_return_workflow_status,
    get_return_details,
    get_order_details,
    get_order_item,
    get_product_details,
    get_product_unit,
    get_delivery_details,
    get_return_shipment,
    get_inspection_results,
    get_refund_status,
    calculate_refundable_amount,
    get_customer_return_history,
]
