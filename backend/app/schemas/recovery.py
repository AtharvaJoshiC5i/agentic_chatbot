"""Recovery optimizer API schemas."""

from pydantic import BaseModel, Field


class RecoveryOptionOut(BaseModel):
    option_id: int
    return_id: str
    recovery_method: str
    expected_revenue_paise: int = Field(validation_alias="expected_revenue")
    repair_cost_paise: int = Field(validation_alias="repair_cost")
    handling_cost_paise: int = Field(validation_alias="handling_cost")
    other_cost_paise: int = Field(validation_alias="other_cost")
    expected_net_recovery_paise: int = Field(validation_alias="expected_net_recovery")
    feasibility_status: str

    model_config = {"from_attributes": True, "populate_by_name": True}


class RankedRecoveryOptionOut(BaseModel):
    option_id: int
    recovery_method: str
    expected_net_recovery_paise: int
    feasibility_status: str
    expected_revenue_paise: int
    total_cost_paise: int
    rank: int
    eligible: bool
    exclusion_reason: str | None = None


class RecoveryRecommendationOut(BaseModel):
    return_id: str
    unsafe_product: bool
    recommended_option_id: int | None
    recommended_method: str | None
    rationale: str
    requires_approval: bool
    ranked_options: list[RankedRecoveryOptionOut]
