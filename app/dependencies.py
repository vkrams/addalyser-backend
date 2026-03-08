"""
Shared dependencies: Google Ads client factory and auth token verification
"""

import logging
from typing import Optional

from fastapi import HTTPException, Header
from google.ads.googleads.client import GoogleAdsClient

from app.config import settings

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


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
        for key, value in credentials.items():
            if key == "refresh_token":
                print(f"  {key}: {value[:30]}..." if value else f"  {key}: NONE")
            elif key == "client_secret":
                print(f"  {key}: {'***' if value else 'NONE'}")
            else:
                print(f"  {key}: {value}")

        if customer_id:
            credentials["login_customer_id"] = customer_id.replace("-", "")

        client = GoogleAdsClient.load_from_dict(credentials)
        return client

    except Exception as e:
        print(f"✗ Error creating client: {str(e)}")
        logger.error(f"Error creating Google Ads client: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to create Google Ads client: {str(e)}")


async def verify_token(authorization: Optional[str] = Header(None)):
    """
    Verify the authorization token from the frontend.
    In production, this should validate JWT tokens from NextAuth.
    """
    if not authorization:
        raise HTTPException(status_code=401, detail="Authorization header missing")

    # TODO: Implement proper JWT verification with NextAuth
    # For now, we extract the refresh token from the header
    return authorization.replace("Bearer ", "")
