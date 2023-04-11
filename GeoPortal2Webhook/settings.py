from pydantic import BaseSettings
import os

class Settings(BaseSettings):

    # API metadata/details
    API_VERSION: str = "v0.1"
    API_TITLE: str = "GeoPortal 2.0 Webhook Automation API"
    API_DESC: str = (
        "An API to process webhooks from ArcGIS Enterprise and "
        "carry out automated tasks.\n\n "
    )
    API_CONTACT_INFO: dict = {"name": "WaTech", "email": "gis@watech.wa.gov"}

    # ArcGIS Enterprise specifics
    PORTAL_URL = os.getenv("Gp2ApplicationUrl")
    PORTAL_USER = os.getenv('Gp2AutomationAdminUser') 
    PORTAL_PW = os.getenv('Gp2AutomationAdminPw')
    
    # Webhook reciever within Teams Channel for notifications
    TEAMS_NOTIFICATION_CHANNEL_URL = os.getenv("Gp2TeamsChannelNotificationURI")
    
    # Feature Service GUID that holds results of the Tag Management Survey123 form
    TAG_MGMT_SERVICE_GUID = os.getenv("Gp2AdminTagResultServiceGUID")
    

def get_settings() -> Settings:
    return Settings()