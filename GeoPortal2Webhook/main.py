import logging
import os
import azure.functions as func
# from FastAPIApp import app
from fastapi import FastAPI, Body, Depends, BackgroundTasks
from pydantic import BaseModel
from enum import Enum
import requests
import json
from typing import Any, Dict, List, Union, Optional
from typing_extensions import Annotated
from pydantic import BaseModel, ValidationError, validator
from arcgis.gis import GIS, Item, Group, User
from .settings import get_settings
from attrs import define

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


def connect_to_gis() -> GIS:
    return GIS(url=portal_url, username=user_name, password=pw)

# create GIS object
gis = connect_to_gis()

class OperationTypes(str, Enum):
    ADD = "add"
    UPDATE = "update"

    def __repr__(self):
        return self.value

class SharingTargets(str, Enum):
    GROUP = "group"
    ORGANIZATION = "organization"

    def __repr__(self):
        return self.value

class SharingMechanism(str, Enum):
    SHARE = "share"
    UNSHARE = "unshare"

    def __repr__(self):
        return self.value

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

# this model represents select information from Survey123
class TagShareSpecifics(BaseModel):
    sharing_mechanism: SharingMechanism
    sharing_target: SharingTargets
    group_global_id: Optional[str] = None


def process_share_tag(tag: str, specs: TagShareSpecifics, item: Item, gis: GIS):

    message = None

    if specs.sharing_target == SharingTargets.ORGANIZATION:
        if specs.sharing_mechanism == SharingMechanism.SHARE:
            if not item.shared_with['org']:
                item.share(org=True)
                message = TeamsNotification(title="Successful Org Share!", text=f"Org Share Tag ({tag}) processed for Item: {item.name} - {item.id}")

        if specs.sharing_mechanism == SharingMechanism.UNSHARE:
            if item.shared_with['org']:
                item.share(org=False)
                message = TeamsNotification(title="Successful Org Unshare!", text=f"Org Unshare Tag ({tag}) processed for Item: {item.name} - {item.id}")

    if specs.sharing_target == SharingTargets.GROUP:
        item_shared_with:dict = item.shared_with
        current_groups: list = [i.id for i in item_shared_with["groups"]]

        if specs.sharing_mechanism == SharingMechanism.SHARE:            
            if not specs.group_global_id in current_groups:
                # verify folks are a part of the group first
                target_group = Group(gis=gis, groupid=specs.group_global_id)
                target_group.add_users([item.owner, user_name])
                if not item_shared_with['org']:
                    item.share(org=True)  # force a quick org share to change the access
                    item.share(groups=specs.group_global_id, org=False)
                    message = TeamsNotification(title="Successful Group Share!", text=f"Group Share Tag ({tag}) processed for Item: {item.name} - {item.id} added to Group: {specs.group_global_id}")
                else:
                    item.share(groups=specs.group_global_id)
                    message = TeamsNotification(title="Successful Group Share!", text=f"Group Share Tag ({tag}) processed for Item: {item.name} - {item.id} added to Group: {specs.group_global_id}")
                    
        if specs.sharing_mechanism == SharingMechanism.UNSHARE:
            if specs.group_global_id in current_groups:
                item.unshare(groups=specs.group_global_id)
                message = TeamsNotification(title="Successful Group Unshare!", text=f"Group Unshare Tag ({tag}) processed for Item: {item.name} - {item.id} removed from Group: {specs.group_global_id}")
    
    if message:
        send_notification(message)
    





def send_notification(teams_notification: TeamsNotification) -> None:
    requests.post(teams_notification_url, data=json.dumps(teams_notification.dict())) 

def check_for_admin_tags(webhook: Webhook) -> None:
    admin_tags: dict = gis.content.get(tag_service_guid).layers[0].query(as_df=True).set_index("administrative_tag").to_dict(orient="index")
    for event in webhook.events:
        try:
            src: Item = Item(gis=gis, itemid=event.id)
        except Exception as e:
            print(f"Error looking up Item ({event.id}) - {e}")
            return None
        
        # check for any tag before iterating
        src_tags: list = src.tags
        if any(_ for _ in src_tags if _ in admin_tags):
            for tag in src_tags:
                try:
                    share_specs: dict = admin_tags[tag]
                    share_specs_obj: TagShareSpecifics = TagShareSpecifics(**share_specs)
                    process_share_tag(tag, share_specs_obj, src, gis)
                except KeyError:
                    pass



@app.get("/reciever")
async def test():
    return {
        "content": "GET request successful",
        "response": "accepted",
    }

@app.post("/reciever")
async def test(background_tasks: BackgroundTasks, webhook: Union[Webhook, WebhookRegistration, None] = Body(...)):

    if type(webhook) == Webhook:
        print(type(webhook))
        message = {"title": f"Webhook Triggered: {webhook.info.webhookName}",
                    "text": json.dumps(webhook.dict())}
        send_notification(teams_notification=TeamsNotification(**message))
        background_tasks.add_task(check_for_admin_tags, webhook=webhook)
    
    if type(webhook) == WebhookRegistration:
        print(type(webhook))
        message = {"title": "New Webhook registration recieved.",
                    "text": json.dumps(webhook.dict())}
        send_notification(teams_notification=TeamsNotification(**message))

    return {
        "response": "accepted",
    }

@app.get("/test")
async def test_gis():
    gis = connect_to_gis()
    return {
        "response": "gis object created",
        "content": f"Portal URL: {gis.url}"
    }


async def main(req: func.HttpRequest, context: func.Context) -> func.HttpResponse:
    return await func.AsgiMiddleware(app).handle_async(req, context)