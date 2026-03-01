"""
Customer routes: list and manage accessible Google Ads accounts
"""

import logging

from fastapi import APIRouter, Depends, HTTPException
from google.ads.googleads.errors import GoogleAdsException

from app.dependencies import get_google_ads_client, verify_token

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["Customers"])


@router.get("/customers")
async def list_accessible_customers(
    refresh_token: str = Depends(verify_token)
):
    """
    List all Google Ads accounts accessible to the authenticated user
    """
    try:
        client = get_google_ads_client(refresh_token)
        customer_service = client.get_service("CustomerService")

        # Get accessible customers
        accessible_customers = customer_service.list_accessible_customers()
        customer_resource_names = accessible_customers.resource_names

        # Extract customer IDs and fetch details
        customers = []
        for resource_name in customer_resource_names:
            customer_id = resource_name.split("/")[-1]

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
