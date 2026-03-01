"""
Dashboard routes: performance reports and account info
"""

import logging

from fastapi import APIRouter, Depends, HTTPException
from google.ads.googleads.errors import GoogleAdsException

from app.dependencies import get_google_ads_client, verify_token
from app.models import DateRange

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["Dashboard"])


@router.post("/performance-report")
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


@router.get("/account-info/{customer_id}")
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
