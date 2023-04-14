import logging
import os
import azure.functions as func
# from FastAPIApp import app
from fastapi import FastAPI, Body
from pydantic import BaseModel
from enum import Enum
import requests
import json
from typing import Any, Dict, List, Union
from typing_extensions import Annotated
from pydantic import BaseModel, ValidationError, validator
from arcgis.gis import GIS

from .settings import get_settings

settings = get_settings()

app = FastAPI(
    title=settings.API_TITLE,
    description=settings.API_DESC,
    version=settings.API_VERSION,
    contact=settings.API_CONTACT_INFO
)

# grab environment variables
user_name = os.getenv('Gp2AutomationAdminUser') 
pw = os.getenv('Gp2AutomationAdminPw')
teams_notification_url = os.getenv("Gp2TeamsChannelNotificationURI")
portal_url = os.getenv("Gp2ApplicationUrl")
tag_service_guid = os.getenv("Gp2AdminTagResultServiceGUID")


class OperationTypes(str, Enum):
    ADD = "add"
    UPDATE = "update"

# models
class Event(BaseModel):
    id: str
    operation: OperationTypes
    properties: Dict[str, Any]
    source: str
    userId: str
    username: str
    when: int


class Info(BaseModel):
    portalURL: str
    webhookId: str
    webhookName: str
    when: int


class Webhook(BaseModel):
    events: List[Event]
    info: Info
    properties: Dict[str, Any]

class WebhookRegistry(BaseModel):
    name: str

class WebhookRegistration(BaseModel):
    WebhookRegistry: WebhookRegistry

class TeamsNotification(BaseModel):
    title: str
    text: str

def _connect_to_gis() -> GIS:
    return GIS(url=portal_url, user_name=user_name, pw=pw)

def send_notification(teams_notification: TeamsNotification) -> None:
    requests.post(teams_notification_url, data=json.dumps(teams_notification.dict())) 

def check_for_tags():
    pass


@app.get("/reciever")
async def test():
    return {
        "content": "GET request successful",
        "response": "accepted",
    }

@app.post("/reciever")
async def test(webhook: Union[Webhook, WebhookRegistration, None] = Body(...)):

    if type(webhook) == Webhook:
        print(type(webhook))
        message = {"title": "recieved a webhook again!",
                    "text": json.dumps(webhook.dict())}
        send_notification(teams_notification=TeamsNotification(**message))
        print("I got here!")
    
    if type(webhook) == WebhookRegistration:
        print(type(webhook))
        message = {"title": "recieved a webhook registration!",
                    "text": json.dumps(webhook.dict())}
        send_notification(teams_notification=TeamsNotification(**message))
        print("I got here!")
        
    # if webhook_registration:
    #     print(webhook_registration)
    #     message = {"title": "New webhook registered",
    #                 "text": json.dumps(webhook_registration.dict())}
    #     send_notification(teams_notification=TeamsNotification(**message))
        

    return {
        "response": "accepted",
    }

@app.get("/test")
async def test_gis():
    gis = _connect_to_gis()
    return {
        "response": "gis object created",
        "content": f"Portal URL: {gis.url}"
    }


async def main(req: func.HttpRequest, context: func.Context) -> func.HttpResponse:
    return await func.AsgiMiddleware(app).handle_async(req, context)