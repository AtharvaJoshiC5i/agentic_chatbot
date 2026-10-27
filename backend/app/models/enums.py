"""String-backed domain enums used by the API and database records."""

from enum import Enum


class AccountStatus(str, Enum):
    ACTIVE = "active"
    SUSPENDED = "suspended"
    CLOSED = "closed"


class ActionType(str, Enum):
    CREATE_CASE = "create_case"
    ASSIGN_CASE = "assign_case"
    REQUEST_REFUND = "request_refund"
    EXECUTE_REFUND = "execute_refund"
    CREATE_REPAIR_TASK = "create_repair_task"
    CREATE_REFURBISHMENT_TASK = "create_refurbishment_task"
    CREATE_SUPPLIER_RETURN = "create_supplier_return"
    CREATE_RECYCLE_TASK = "create_recycle_task"
    CREATE_DISPOSE_TASK = "create_dispose_task"
    UPDATE_CASE_STATUS = "update_case_status"
    CREATE_INSPECTION_TASK = "create_inspection_task"
    CREATE_EVIDENCE_REQUEST = "create_evidence_request"
    CREATE_DATA_CORRECTION = "create_data_correction"
    CREATE_WARRANTY_TASK = "create_warranty_task"
    CREATE_REPLACEMENT_REQUEST = "create_replacement_request"


class ActorType(str, Enum):
    USER = "user"
    AGENT = "agent"
    SYSTEM = "system"


class AlertSeverity(str, Enum):
    INFO = "info"
    WARNING = "warning"
    HIGH = "high"
    CRITICAL = "critical"


class AlertStatus(str, Enum):
    OPEN = "open"
    ACKNOWLEDGED = "acknowledged"
    RESOLVED = "resolved"
    SUPPRESSED = "suppressed"


class AlertType(str, Enum):
    OVERDUE_INVESTIGATION = "overdue_investigation"
    PENDING_REFUND_APPROVAL = "pending_refund_approval"
    FAILED_ACTION = "failed_action"
    OVERDUE_RECOVERY_TASK = "overdue_recovery_task"
    AWAITING_INSPECTION = "awaiting_inspection"
    UNRESOLVED_INCONSISTENCY = "unresolved_inconsistency"


class ApprovalStatus(str, Enum):
    NOT_REQUIRED = "not_required"
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"


class CasePriority(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class CaseStatus(str, Enum):
    OPEN = "open"
    ASSIGNED = "assigned"
    IN_PROGRESS = "in_progress"
    AWAITING_EVIDENCE = "awaiting_evidence"
    READY_FOR_REVIEW = "ready_for_review"
    PENDING_APPROVAL = "pending_approval"
    RESOLVED = "resolved"
    CLOSED = "closed"


class DeliveryStatus(str, Enum):
    PENDING = "pending"
    DISPATCHED = "dispatched"
    IN_TRANSIT = "in_transit"
    DELIVERED = "delivered"
    FAILED = "failed"
    RETURNED_TO_SENDER = "returned_to_sender"


class DocumentAccessLevel(str, Enum):
    STANDARD = "standard"
    RESTRICTED = "restricted"


class DocumentType(str, Enum):
    RETURN_POLICY = "return_policy"
    WARRANTY = "warranty"
    INSPECTION_REPORT = "inspection_report"
    CUSTOMER_COMPLAINT = "customer_complaint"
    SUPPLIER_DEFECT_REPORT = "supplier_defect_report"
    SUPPORT_COMMUNICATION = "support_communication"
    REFURBISHMENT_GUIDELINE = "refurbishment_guideline"


class EscalationStatus(str, Enum):
    OPEN = "open"
    ACKNOWLEDGED = "acknowledged"
    RESOLVED = "resolved"


class EvidenceRequestStatus(str, Enum):
    PENDING = "pending"
    COMPLETED = "completed"
    REJECTED = "rejected"
    OVERDUE = "overdue"


class ExecutionStatus(str, Enum):
    PENDING = "pending"
    AWAITING_APPROVAL = "awaiting_approval"
    APPROVED = "approved"
    EXECUTING = "executing"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    REJECTED = "rejected"
    CANCELLED = "cancelled"


class FeasibilityStatus(str, Enum):
    FEASIBLE = "feasible"
    NOT_FEASIBLE = "not_feasible"
    REQUIRES_APPROVAL = "requires_approval"


class InspectionResult(str, Enum):
    PASS = "pass"
    FAIL = "fail"
    INCONCLUSIVE = "inconclusive"
    PENDING = "pending"


class InventoryDispositionStatus(str, Enum):
    QUARANTINE = "quarantine"
    RESERVED = "reserved"
    IN_REPAIR = "in_repair"
    LISTED_FOR_SALE = "listed_for_sale"
    SUPPLIER_RETURN = "supplier_return"
    RECYCLED = "recycled"
    DISPOSED = "disposed"


class IssueType(str, Enum):
    SERIAL_MISMATCH = "serial_mismatch"
    PRODUCT_MISMATCH = "product_mismatch"
    POLICY_EXCEPTION = "policy_exception"
    DUPLICATE_REFUND = "duplicate_refund"
    CONFLICTING_EVIDENCE = "conflicting_evidence"
    MISSING_INSPECTION = "missing_inspection"
    DELIVERY_DISPUTE = "delivery_dispute"
    WARRANTY_REVIEW = "warranty_review"
    DATA_CORRECTION = "data_correction"
    SAFETY_CONCERN = "safety_concern"
    GENERAL = "general"


class OrderStatus(str, Enum):
    PLACED = "placed"
    CONFIRMED = "confirmed"
    FULFILLED = "fulfilled"
    CANCELLED = "cancelled"
    PARTIALLY_RETURNED = "partially_returned"
    RETURNED = "returned"


class ProductCondition(str, Enum):
    NEW = "new"
    LIKE_NEW = "like_new"
    OPEN_BOX = "open_box"
    DAMAGED = "damaged"
    DEFECTIVE = "defective"
    UNSAFE = "unsafe"
    FOR_PARTS = "for_parts"


class ProductUnitStatus(str, Enum):
    IN_STOCK = "in_stock"
    RESERVED = "reserved"
    SHIPPED = "shipped"
    DELIVERED = "delivered"
    RETURNED = "returned"
    INSPECTED = "inspected"
    IN_RECOVERY = "in_recovery"
    RECOVERED = "recovered"


class RecoveryMethod(str, Enum):
    RESELL_NEW = "resell_new"
    OPEN_BOX = "open_box_resale"
    REPAIR_RESELL = "repair_and_resell"
    REFURBISH_RESELL = "refurbish_and_resell"
    SUPPLIER_RETURN = "supplier_return"
    RECYCLE = "recycle"
    DISPOSE = "dispose"


class RefundStatus(str, Enum):
    REQUESTED = "requested"
    APPROVED = "approved"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    RECONCILIATION_REQUIRED = "reconciliation_required"


class ReplacementStatus(str, Enum):
    REQUESTED = "requested"
    APPROVED = "approved"
    DISPATCHED = "dispatched"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class RequestedResolution(str, Enum):
    REFUND = "refund"
    REPLACEMENT = "replacement"
    REPAIR = "repair"
    STORE_CREDIT = "store_credit"


class ReturnReason(str, Enum):
    DAMAGED = "damaged"
    NOT_FUNCTIONING = "not_functioning"
    WRONG_PRODUCT = "wrong_product"
    SIZE_COLOR_INCORRECT = "size_color_incorrect"
    MISSING_ACCESSORIES = "missing_accessories"
    CHANGED_MIND = "changed_mind"
    DEFECTIVE = "defective"
    NOT_AS_DESCRIBED = "not_as_described"
    OTHER = "other"


class ReturnStatus(str, Enum):
    REQUESTED = "requested"
    APPROVED = "approved"
    PICKUP_SCHEDULED = "pickup_scheduled"
    IN_TRANSIT = "in_transit"
    RECEIVED = "received"
    INSPECTING = "inspecting"
    INVESTIGATING = "investigating"
    RESOLVED = "resolved"
    REJECTED = "rejected"
    CLOSED = "closed"


class SourceType(str, Enum):
    ORDER = "order"
    DELIVERY = "delivery"
    RETURN = "return"
    INSPECTION = "inspection"
    REFUND = "refund"
    CASE = "case"
    RECOVERY_TASK = "recovery_task"
    DOCUMENT = "document"
    COMPLAINT = "complaint"
    SYSTEM = "system"


class TaskStatus(str, Enum):
    PENDING = "pending"
    ASSIGNED = "assigned"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class UserRole(str, Enum):
    RETURNS_ANALYST = "returns_analyst"
    CUSTOMER_SUPPORT = "customer_support_agent"
    CUSTOMER_SUPPORT_AGENT = "customer_support_agent"
    WAREHOUSE_MANAGER = "warehouse_manager"
    RETURNS_SUPERVISOR = "returns_supervisor"
    ADMINISTRATOR = "administrator"


class WarrantyClaimStatus(str, Enum):
    OPEN = "open"
    UNDER_REVIEW = "under_review"
    APPROVED = "approved"
    DENIED = "denied"
    CLOSED = "closed"
