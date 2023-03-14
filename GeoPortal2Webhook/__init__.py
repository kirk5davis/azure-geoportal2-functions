import logging
import os
import azure.functions as func
from FastAPIApp import app

user_name = os.getenv('gp2-automation-admin-username')
pw = os.getenv('gp2-automation-admin-password')

@app.get("/sample")
async def index():
    return {
    "info": f"Looked up values from Key Vault: username - {user_name}, pw - {pw}",
    } 

@app.get("/hello/{name}")
async def get_name(name: str):
    return {
        "name": name,
    }

async def main(req: func.HttpRequest, context: func.Context) -> func.HttpResponse:
    return await func.AsgiMiddleware(app).handle_async(req, context)