"""
Pydantic request/response models
"""

from pydantic import BaseModel


class TokenRequest(BaseModel):
    refresh_token: str
    customer_id: str


class CampaignCreate(BaseModel):
    customer_id: str
    campaign_name: str
    budget_amount: float
    campaign_type: str = "SEARCH"


class AdGroupCreate(BaseModel):
    customer_id: str
    campaign_id: str
    ad_group_name: str
    cpc_bid_micros: int = 1000000  # Default $1.00


class KeywordCreate(BaseModel):
    customer_id: str
    ad_group_id: str
    keyword_text: str
    match_type: str = "BROAD"


class DateRange(BaseModel):
    start_date: str  # YYYY-MM-DD
    end_date: str    # YYYY-MM-DD
