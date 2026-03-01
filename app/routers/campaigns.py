"""
Campaign routes: campaigns, ad groups, keywords
"""

import logging

from fastapi import APIRouter, Depends, HTTPException
from google.ads.googleads.errors import GoogleAdsException

from app.dependencies import get_google_ads_client, verify_token
from app.models import CampaignCreate

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["Campaigns"])


@router.get("/campaigns/{customer_id}")
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


@router.post("/campaigns/create")
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


@router.get("/ad-groups/{customer_id}/{campaign_id}")
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


@router.get("/keywords/{customer_id}/{ad_group_id}")
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
