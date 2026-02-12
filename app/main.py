"""
Google Ads SaaS Platform - FastAPI Backend
Main application file with all Google Ads API endpoints
"""

from fastapi import FastAPI, HTTPException, Depends, Header
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta
import os
from google.ads.googleads.client import GoogleAdsClient
from google.ads.googleads.errors import GoogleAdsException
import logging
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):

    # Google Ads
    GOOGLE_ADS_DEVELOPER_TOKEN: str
    GOOGLE_CLIENT_ID: str
    GOOGLE_CLIENT_SECRET: str

    # Optional but recommended later
    DATABASE_URL: str | None = None

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",  # prevents crashes from unused vars
    )

settings = Settings()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Google Ads SaaS API",
    description="FastAPI backend for Google Ads management platform",
    version="1.0.0"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:3001"],  # Update with your frontend URL
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Pydantic models for request/response
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
    end_date: str  # YYYY-MM-DD


# Helper function to create Google Ads client
def get_google_ads_client(refresh_token: str, customer_id: str = None) -> GoogleAdsClient:
    """
    Create and return a Google Ads API client
    """
    logging.basicConfig(level=logging.INFO, force=True)

    try:
        if not refresh_token:
            raise HTTPException(status_code=400, detail="No refresh token provided")
            
        # Build credentials dictionary
        credentials = {
            
            "developer_token": settings.GOOGLE_ADS_DEVELOPER_TOKEN,
            "client_id": settings.GOOGLE_CLIENT_ID,
            "client_secret": settings.GOOGLE_CLIENT_SECRET,
            "refresh_token": refresh_token,
            "token_uri": "https://oauth2.googleapis.com/token",
            "use_proto_plus": True,
        }
        
        # Debug: print all keys
        print(f"Credentials keys: {list(credentials.keys())}")
        for key, value in credentials.items():
            if key == "refresh_token":
                print(f"  {key}: {value[:30]}..." if value else f"  {key}: NONE")
            elif key == "client_secret":
                print(f"  {key}: {'***' if value else 'NONE'}")
            else:
                print(f"  {key}: {value}")
        
        if customer_id:
            credentials["login_customer_id"] = customer_id.replace("-", "")
            print(f"Login customer ID: {credentials['login_customer_id']}")
            
        print("Creating GoogleAdsClient...")
        client = GoogleAdsClient.load_from_dict(credentials)
        print("✓ Google Ads client created successfully")
        return client
        
    except Exception as e:
        print(f"✗ Error creating client: {str(e)}")
        logger.error(f"Error creating Google Ads client: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to create Google Ads client: {str(e)}")
    
# Dependency to verify authorization
async def verify_token(authorization: Optional[str] = Header(None)):
    """
    Verify the authorization token from the frontend
    In production, this should validate JWT tokens from NextAuth
    """
    if not authorization:
        raise HTTPException(status_code=401, detail="Authorization header missing")
    
    # TODO: Implement proper JWT verification with NextAuth
    # For now, we'll extract the refresh token from the header
    return authorization.replace("Bearer ", "")


@app.get("/")
async def root():
    """Health check endpoint"""
    return {
        "status": "ok",
        "service": "Google Ads SaaS API",
        "version": "1.0.0"
    }


@app.get("/api/customers")
async def list_accessible_customers(
    refresh_token: str = Depends(verify_token)
):
    """
    List all Google Ads accounts accessible to the authenticated user
    """
    try:
        client = get_google_ads_client(refresh_token)
        customer_service = client.get_service("CustomerService")  # This should auto-detect the latest version
        
        # Get accessible customers
        accessible_customers = customer_service.list_accessible_customers()
        customer_resource_names = accessible_customers.resource_names
        
        # Extract customer IDs from resource names
        customers = []
        for resource_name in customer_resource_names:
            customer_id = resource_name.split("/")[-1]
            
            # Get customer details
            try:
                ga_service = client.get_service("GoogleAdsService")
                query = f"""
                    SELECT
                        customer.id,
                        customer.descriptive_name,
                        customer.currency_code,
                        customer.time_zone
                    FROM customer
                    WHERE customer.id = {customer_id}
                """
                
                # Remove login_customer_id if not needed
                response = ga_service.search(customer_id=customer_id, query=query)
                
                for row in response:
                    customers.append({
                        "customer_id": str(row.customer.id),
                        "name": row.customer.descriptive_name,
                        "currency_code": row.customer.currency_code,
                        "time_zone": row.customer.time_zone,
                        "resource_name": resource_name
                    })
            except Exception as e:
                logger.warning(f"Could not fetch details for customer {customer_id}: {str(e)}")
                customers.append({
                    "customer_id": customer_id,
                    "name": "Unknown",
                    "resource_name": resource_name
                })
        
        return {"customers": customers}
        
    except GoogleAdsException as ex:
        logger.error(f"Google Ads API error: {ex}")
        raise HTTPException(status_code=400, detail=str(ex))
    except Exception as e:
        logger.error(f"Error listing customers: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/campaigns/{customer_id}")
async def get_campaigns(
    customer_id: str,
    refresh_token: str = Depends(verify_token)
):
    """
    Get all campaigns for a specific customer account
    """
    try:
        client = get_google_ads_client(refresh_token, customer_id)
        ga_service = client.get_service("GoogleAdsService")
        
        query = """
            SELECT
                campaign.id,
                campaign.name,
                campaign.status,
                campaign.advertising_channel_type,
                campaign_budget.amount_micros,
                metrics.impressions,
                metrics.clicks,
                metrics.cost_micros,
                metrics.conversions,
                metrics.ctr,
                metrics.average_cpc
            FROM campaign
            WHERE campaign.status != 'REMOVED'
            ORDER BY campaign.name
        """
        
        response = ga_service.search(customer_id=customer_id, query=query)
        
        campaigns = []
        for row in response:
            campaigns.append({
                "id": str(row.campaign.id),
                "name": row.campaign.name,
                "status": row.campaign.status.name,
                "type": row.campaign.advertising_channel_type.name,
                "budget": row.campaign_budget.amount_micros / 1_000_000 if row.campaign_budget.amount_micros else 0,
                "metrics": {
                    "impressions": row.metrics.impressions,
                    "clicks": row.metrics.clicks,
                    "cost": row.metrics.cost_micros / 1_000_000,
                    "conversions": row.metrics.conversions,
                    "ctr": round(row.metrics.ctr * 100, 2),
                    "avg_cpc": row.metrics.average_cpc / 1_000_000 if row.metrics.average_cpc else 0
                }
            })
        
        return {"campaigns": campaigns}
        
    except GoogleAdsException as ex:
        logger.error(f"Google Ads API error: {ex}")
        raise HTTPException(status_code=400, detail=str(ex))
    except Exception as e:
        logger.error(f"Error fetching campaigns: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/ad-groups/{customer_id}/{campaign_id}")
async def get_ad_groups(
    customer_id: str,
    campaign_id: str,
    refresh_token: str = Depends(verify_token)
):
    """
    Get all ad groups for a specific campaign
    """
    try:
        client = get_google_ads_client(refresh_token, customer_id)
        ga_service = client.get_service("GoogleAdsService")
        
        query = f"""
            SELECT
                ad_group.id,
                ad_group.name,
                ad_group.status,
                ad_group.cpc_bid_micros,
                metrics.impressions,
                metrics.clicks,
                metrics.cost_micros,
                metrics.conversions
            FROM ad_group
            WHERE campaign.id = {campaign_id}
                AND ad_group.status != 'REMOVED'
            ORDER BY ad_group.name
        """
        
        response = ga_service.search(customer_id=customer_id, query=query)
        
        ad_groups = []
        for row in response:
            ad_groups.append({
                "id": str(row.ad_group.id),
                "name": row.ad_group.name,
                "status": row.ad_group.status.name,
                "cpc_bid": row.ad_group.cpc_bid_micros / 1_000_000 if row.ad_group.cpc_bid_micros else 0,
                "metrics": {
                    "impressions": row.metrics.impressions,
                    "clicks": row.metrics.clicks,
                    "cost": row.metrics.cost_micros / 1_000_000,
                    "conversions": row.metrics.conversions
                }
            })
        
        return {"ad_groups": ad_groups}
        
    except GoogleAdsException as ex:
        logger.error(f"Google Ads API error: {ex}")
        raise HTTPException(status_code=400, detail=str(ex))
    except Exception as e:
        logger.error(f"Error fetching ad groups: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/keywords/{customer_id}/{ad_group_id}")
async def get_keywords(
    customer_id: str,
    ad_group_id: str,
    refresh_token: str = Depends(verify_token)
):
    """
    Get all keywords for a specific ad group
    """
    try:
        client = get_google_ads_client(refresh_token, customer_id)
        ga_service = client.get_service("GoogleAdsService")
        
        query = f"""
            SELECT
                ad_group_criterion.keyword.text,
                ad_group_criterion.keyword.match_type,
                ad_group_criterion.status,
                ad_group_criterion.cpc_bid_micros,
                metrics.impressions,
                metrics.clicks,
                metrics.cost_micros,
                metrics.conversions
            FROM keyword_view
            WHERE ad_group.id = {ad_group_id}
                AND ad_group_criterion.status != 'REMOVED'
            ORDER BY ad_group_criterion.keyword.text
        """
        
        response = ga_service.search(customer_id=customer_id, query=query)
        
        keywords = []
        for row in response:
            keywords.append({
                "text": row.ad_group_criterion.keyword.text,
                "match_type": row.ad_group_criterion.keyword.match_type.name,
                "status": row.ad_group_criterion.status.name,
                "cpc_bid": row.ad_group_criterion.cpc_bid_micros / 1_000_000 if row.ad_group_criterion.cpc_bid_micros else 0,
                "metrics": {
                    "impressions": row.metrics.impressions,
                    "clicks": row.metrics.clicks,
                    "cost": row.metrics.cost_micros / 1_000_000,
                    "conversions": row.metrics.conversions
                }
            })
        
        return {"keywords": keywords}
        
    except GoogleAdsException as ex:
        logger.error(f"Google Ads API error: {ex}")
        raise HTTPException(status_code=400, detail=str(ex))
    except Exception as e:
        logger.error(f"Error fetching keywords: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/performance-report")
async def get_performance_report(
    customer_id: str,
    date_range: DateRange,
    refresh_token: str = Depends(verify_token)
):
    """
    Get performance report for a date range
    """
    try:
        client = get_google_ads_client(refresh_token, customer_id)
        ga_service = client.get_service("GoogleAdsService")
        
        query = f"""
            SELECT
                segments.date,
                metrics.impressions,
                metrics.clicks,
                metrics.cost_micros,
                metrics.conversions,
                metrics.ctr,
                metrics.average_cpc,
                metrics.conversion_rate
            FROM campaign
            WHERE segments.date BETWEEN '{date_range.start_date}' AND '{date_range.end_date}'
            ORDER BY segments.date DESC
        """
        
        response = ga_service.search(customer_id=customer_id, query=query)
        
        report_data = []
        for row in response:
            report_data.append({
                "date": row.segments.date,
                "impressions": row.metrics.impressions,
                "clicks": row.metrics.clicks,
                "cost": row.metrics.cost_micros / 1_000_000,
                "conversions": row.metrics.conversions,
                "ctr": round(row.metrics.ctr * 100, 2),
                "avg_cpc": row.metrics.average_cpc / 1_000_000 if row.metrics.average_cpc else 0,
                "conversion_rate": round(row.metrics.conversion_rate * 100, 2)
            })
        
        # Calculate totals
        totals = {
            "impressions": sum(d["impressions"] for d in report_data),
            "clicks": sum(d["clicks"] for d in report_data),
            "cost": sum(d["cost"] for d in report_data),
            "conversions": sum(d["conversions"] for d in report_data),
        }
        
        if totals["impressions"] > 0:
            totals["ctr"] = round((totals["clicks"] / totals["impressions"]) * 100, 2)
        else:
            totals["ctr"] = 0
            
        if totals["clicks"] > 0:
            totals["avg_cpc"] = round(totals["cost"] / totals["clicks"], 2)
            totals["conversion_rate"] = round((totals["conversions"] / totals["clicks"]) * 100, 2)
        else:
            totals["avg_cpc"] = 0
            totals["conversion_rate"] = 0
        
        return {
            "data": report_data,
            "totals": totals,
            "date_range": {
                "start_date": date_range.start_date,
                "end_date": date_range.end_date
            }
        }
        
    except GoogleAdsException as ex:
        logger.error(f"Google Ads API error: {ex}")
        raise HTTPException(status_code=400, detail=str(ex))
    except Exception as e:
        logger.error(f"Error generating report: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/campaigns/create")
async def create_campaign(
    campaign_data: CampaignCreate,
    refresh_token: str = Depends(verify_token)
):
    """
    Create a new campaign
    """
    try:
        client = get_google_ads_client(refresh_token, campaign_data.customer_id)
        
        # Create campaign budget
        campaign_budget_service = client.get_service("CampaignBudgetService")
        campaign_budget_operation = client.get_type("CampaignBudgetOperation")
        campaign_budget = campaign_budget_operation.create
        campaign_budget.name = f"Budget for {campaign_data.campaign_name}"
        campaign_budget.amount_micros = int(campaign_data.budget_amount * 1_000_000)
        campaign_budget.delivery_method = client.enums.BudgetDeliveryMethodEnum.STANDARD
        
        budget_response = campaign_budget_service.mutate_campaign_budgets(
            customer_id=campaign_data.customer_id,
            operations=[campaign_budget_operation]
        )
        budget_resource_name = budget_response.results[0].resource_name
        
        # Create campaign
        campaign_service = client.get_service("CampaignService")
        campaign_operation = client.get_type("CampaignOperation")
        campaign = campaign_operation.create
        campaign.name = campaign_data.campaign_name
        campaign.advertising_channel_type = client.enums.AdvertisingChannelTypeEnum[campaign_data.campaign_type]
        campaign.status = client.enums.CampaignStatusEnum.PAUSED
        campaign.campaign_budget = budget_resource_name
        campaign.network_settings.target_google_search = True
        campaign.network_settings.target_search_network = True
        
        campaign_response = campaign_service.mutate_campaigns(
            customer_id=campaign_data.customer_id,
            operations=[campaign_operation]
        )
        
        return {
            "success": True,
            "campaign_id": campaign_response.results[0].resource_name.split("/")[-1],
            "message": f"Campaign '{campaign_data.campaign_name}' created successfully"
        }
        
    except GoogleAdsException as ex:
        logger.error(f"Google Ads API error: {ex}")
        raise HTTPException(status_code=400, detail=str(ex))
    except Exception as e:
        logger.error(f"Error creating campaign: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/account-info/{customer_id}")
async def get_account_info(
    customer_id: str,
    refresh_token: str = Depends(verify_token)
):
    """
    Get detailed account information
    """
    try:
        client = get_google_ads_client(refresh_token, customer_id)
        ga_service = client.get_service("GoogleAdsService")
        
        query = f"""
            SELECT
                customer.id,
                customer.descriptive_name,
                customer.currency_code,
                customer.time_zone,
                customer.auto_tagging_enabled,
                customer.has_partners_badge,
                customer.manager
            FROM customer
            WHERE customer.id = {customer_id}
        """
        
        response = ga_service.search(customer_id=customer_id, query=query)
        
        for row in response:
            return {
                "customer_id": str(row.customer.id),
                "name": row.customer.descriptive_name,
                "currency_code": row.customer.currency_code,
                "time_zone": row.customer.time_zone,
                "auto_tagging_enabled": row.customer.auto_tagging_enabled,
                "has_partners_badge": row.customer.has_partners_badge,
                "is_manager": row.customer.manager
            }
        
        raise HTTPException(status_code=404, detail="Customer not found")
        
    except GoogleAdsException as ex:
        logger.error(f"Google Ads API error: {ex}")
        raise HTTPException(status_code=400, detail=str(ex))
    except Exception as e:
        logger.error(f"Error fetching account info: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
