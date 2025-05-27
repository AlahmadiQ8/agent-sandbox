from dataclasses import asdict, dataclass
import os
from agents import TResponseInputItem
from azure.cosmos import CosmosClient, PartitionKey, exceptions
from typing import Any, Dict, Optional, List, TypedDict

@dataclass
class ChatHistoryItem(TypedDict):
    id: str
    chat_id: str
    input: TResponseInputItem


class CosmosChatHistoryStore:
    def __init__(self, endpoint: str, key: str, database_name: str, container_name: str):
        self.client = CosmosClient(endpoint, key)
        self.database = self.client.get_database_client(database_name)
        self.container = self.database.get_container_client(container_name)
    
    def upsert_bulk_history_items(self, items: List[ChatHistoryItem]) -> List[Any]:
        """Insert or update multiple chat history items."""
        upserted_items = []
        for item in items:
            upserted_item = self.container.upsert_item(dict(item))
            upserted_items.append(upserted_item)
        return upserted_items

    def get_chat_history(self, chat_id: str, limit: int) -> List[Dict[str, ChatHistoryItem]]:
        """Retrieve the last x history items for a given chat_id. ordered by _ts ascending."""
        query = "SELECT * FROM c WHERE c.chat_id=@chat_id ORDER BY c._ts DESC OFFSET 0 LIMIT @limit"
        parameters = [
            {"name": "@chat_id", "value": chat_id},
            {"name": "@limit", "value": limit}
        ]
        items = list(self.container.query_items(
            query=query,
            parameters=parameters,
            enable_cross_partition_query=False
        ))

        items.reverse()
        return items
        

    def delete_chat_history(self, chat_id: str) -> None:
        """Delete all history items for a given chat_id."""
        query = "SELECT * FROM c WHERE c.chat_id=@chat_id"
        items = list(self.container.query_items(
            query=query,
            parameters=[{"name": "@chat_id", "value": chat_id}],
            enable_cross_partition_query=False
        ))
        for item in items:
            self.container.delete_item(item=item['id'], partition_key=chat_id)

MAX_CHAT_HISTORY = 10
COSMOS_ENDPOINT = os.getenv("COSMOS_DB_ENDPOINT")
COSMOS_KEY = os.getenv("COSMOS_DB_KEY")
COSMOS_DB = os.getenv("COSMOS_DB_NAME", "testdb")
COSMOS_CONTAINER = os.getenv("COSMOS_CONTAINER", "chathistory2")

if not COSMOS_ENDPOINT or not COSMOS_KEY:
    raise EnvironmentError("COSMOS_DB_ENDPOINT and COSMOS_DB_KEY environment variables must be set.")

store = CosmosChatHistoryStore(COSMOS_ENDPOINT, COSMOS_KEY, COSMOS_DB, COSMOS_CONTAINER)

