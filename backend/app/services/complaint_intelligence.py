"""Product complaint pattern analysis (Hidden Defect Pattern Detector)."""

from collections import Counter
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.enums import DocumentType, ReturnReason
from app.models.tables import DocumentMetadata, OrderItem, Product, Return


def analyze_product_complaint_patterns(
    session: Session,
    *,
    product_id: str | None = None,
    model_keyword: str | None = None,
    min_mentions: int = 3,
) -> dict[str, Any]:
    """Group return/complaint signals for a product or model keyword."""
    returns_q = select(Return, OrderItem, Product).join(
        OrderItem, Return.order_item_id == OrderItem.order_item_id
    ).join(Product, OrderItem.product_id == Product.product_id)

    if product_id:
        returns_q = returns_q.where(Product.product_id == product_id)
    elif model_keyword:
        like = f"%{model_keyword.lower()}%"
        returns_q = returns_q.where(func.lower(Product.product_name).like(like))

    rows = session.execute(returns_q).all()
    reason_counts: Counter[str] = Counter()
    return_ids: list[str] = []
    for ret, _item, product in rows:
        return_ids.append(ret.return_id)
        reason_counts[ret.return_reason] += 1

    complaint_docs = 0
    if return_ids:
        complaint_docs = session.execute(
            select(func.count())
            .select_from(DocumentMetadata)
            .where(
                DocumentMetadata.document_type == DocumentType.CUSTOMER_COMPLAINT.value,
                DocumentMetadata.return_id.in_(return_ids[:200]),
            )
        ).scalar_one()

    top_reasons = [{"reason": k, "count": v} for k, v in reason_counts.most_common(5)]
    pattern_detected = len(rows) >= min_mentions and (
        reason_counts.get(ReturnReason.DEFECTIVE.value, 0)
        + reason_counts.get(ReturnReason.NOT_FUNCTIONING.value, 0)
        >= min_mentions
    )

    return {
        "product_id": product_id,
        "model_keyword": model_keyword,
        "return_count": len(rows),
        "complaint_document_count": complaint_docs,
        "top_return_reasons": top_reasons,
        "pattern_suspected": pattern_detected,
        "interpretation": (
            "Multiple returns share similar defect-related reasons; consider supplier-quality review."
            if pattern_detected
            else "No strong recurring defect pattern at current thresholds."
        ),
        "sample_return_ids": return_ids[:10],
    }
