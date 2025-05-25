from http import HTTPMethod
import json
from agents import RunItem, Runner, TResponseInputItem
import azure.functions as func
import logging
from main_agent import Context, ynab_agent

app = func.FunctionApp(http_auth_level=func.AuthLevel.FUNCTION)

@app.route(route="chat_completion", methods=[HTTPMethod.POST])
async def chat_completion(req: func.HttpRequest) -> func.HttpResponse:
    # logging.info('Python HTTP trigger function processed a request.')

    req_body: list[TResponseInputItem] = req.get_json()

    result = await Runner.run(ynab_agent, req_body, context=Context())
    
    logging.info(result.new_items)
            
    return func.HttpResponse(
        json.dumps([item.to_input_item() for item in result.new_items]),
        mimetype="application/json",
    )