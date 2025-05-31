from http import HTTPMethod
import json
from typing import List
from agents import Runner
import azure.functions as func
import logging
from cosmos_chat_history_store import MAX_CHAT_HISTORY, ChatHistoryItem, store
from ynab_agent import Context, ynab_agent
from typing import cast
import uuid

app = func.FunctionApp(http_auth_level=func.AuthLevel.FUNCTION)

def is_clearchat_command(message: dict) -> bool:
    text = message.get("text", "")
    entities = message.get("entities", [])
    has_command = "/clearchat" in text
    has_bot_command_entity = any(e.get("type") == "bot_command" for e in entities)
    return has_command and has_bot_command_entity

@app.route(route="chat_completion", methods=[HTTPMethod.POST])
async def chat_completion(req: func.HttpRequest) -> func.HttpResponse:

    req_body = req.get_json()

    if (is_clearchat_command(req_body['message'])):
        store.delete_chat_history(str(req_body['message']['chat']['id']))
        return func.HttpResponse(
            json.dumps([
                {
                    "id": "clearchat",
                    "content": [
                    {
                        "text": "chat history cleared",
                        "type": "output_text"
                    }
                    ],
                    "role": "assistant",
                    "status": "completed",
                    "type": "message"
                }
            ]),
            mimetype="application/json",
        )

    new_chat_item: ChatHistoryItem = {
        'id': str(uuid.uuid4()),
        'chat_id': str(req_body['message']['chat']['id']),
        'input': {
            'role': 'user',
            'content': req_body['message']['text']
        }
    }

    history = cast(List[ChatHistoryItem], store.get_chat_history(
        chat_id=new_chat_item['chat_id'],
        limit=MAX_CHAT_HISTORY
    ))

    new_history = history + [new_chat_item]

    input = [item['input'] for item in new_history]

    result = await Runner.run(ynab_agent, input, context=Context())

    new_items = [item.to_input_item() for item in result.new_items]
    new_chat: List[ChatHistoryItem] = [new_chat_item] + [
        {
            'id': str(uuid.uuid4()),
            'chat_id': new_chat_item['chat_id'],
            'input': item
        } for item in new_items
    ]

    logging.info(json.dumps(new_chat, indent=4))

    store.upsert_bulk_history_items(new_chat)

    # Filter the new items to get only those with role 'assistant' and content type 'output_text'
    assistent_messages = []
    for item in new_items:
        if item.get("role") == "assistant":
            content = item.get("content", None)
            if isinstance(content, list) and len(content) > 0:
                if content[0].get("type") == "output_text":
                    assistent_messages.append(item)
            
    return func.HttpResponse(
        json.dumps(assistent_messages),
        mimetype="application/json",
    )

