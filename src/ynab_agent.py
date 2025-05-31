from dataclasses import dataclass
import json
from openai.types.responses import ResponseTextDeltaEvent
from agents import Agent,function_tool, TResponseInputItem, trace, InputGuardrail, GuardrailFunctionOutput, Runner, RunContextWrapper
from pydantic import BaseModel
import asyncio
import os
import setup_azure_openai_client
from datetime import datetime
import requests
import logging

model_name = "gpt-4.1"

class Context(BaseModel):
    today: str | None = None

BUDGET_ID = os.getenv("YNAB_BUDGET_ID")
ACCESS_TOKEN = os.getenv("YNAB_API_KEY")
YNAB_CREATE_TRANSACTION_URL = f"https://api.ynab.com/v1/budgets/{BUDGET_ID}/transactions"

@function_tool
def store_transaction_to_ynab_tool(amount: float, currency: str, payee: str, date: str, account_last_4_digits: int) -> bool:
    """
    Store a transaction in YNAB (You Need A Budget).

    Args:
        amount (float): The transaction amount. Positive for credit, negative for debit.
        currency (str): ISO currency code (e.g., 'KWD', 'USD').
        payee (str): The payee or merchant name.
        date (str): Transaction date in 'YYYY-MM-DD' format.
        account_last_4_digits (str): Last 4 digits of the account or card number.

    Returns:
        bool: True if the transaction was stored successfully, False otherwise.
    """
    # Placeholder function to simulate storing transaction in YNAB
    logging.info(f"Storing transaction in YNAB: {amount} {currency} to {payee} on {date} (Account: {account_last_4_digits})")

    account_lookup = {
        9226: "8abb8fba-a913-41c8-bfa4-1944be548eaa",
        1849: "98df622c-509e-4230-a243-56d6d625e740",
        5893: "c5f83ca5-a2a8-4628-b0e7-f299d5a6e452",
        3642: "ae0f189f-99fc-4902-a8f8-95630635a4d9",
    }
    
    account_id = account_lookup.get(account_last_4_digits, None)
    if account_id is None:
        logging.info(f"Account with last 4 digits {account_last_4_digits} not found.")
        return False
    if not BUDGET_ID:
        logging.info("YNAB_BUDGET_ID environment variable is not set.")
        return False
    
    response = requests.post(
        YNAB_CREATE_TRANSACTION_URL,
        headers={ "Authorization": f"Bearer {ACCESS_TOKEN}" },
        json = {
            "transaction": {
                "account_id": account_id,
                "date": date,
                "amount": int(amount * 1000),  # YNAB uses milliunits
                "memo": f"AI GENERATED - {payee}",
                "cleared": "uncleared",
                "flag_color": "red"
            }
        }
    )

    if (response.status_code != 201):
        logging.info(f"Failed to store transaction in YNAB: {response.status_code} - {response.text}")
        return False

    return True

def prompt(context: RunContextWrapper[Context],  agent: Agent[Context]) -> str:  
    # store date in yyyy-MM-dd format
    context.context.today = datetime.now().strftime("%Y-%m-%d")
    return f""""
# Instructions 
You are an AI agent that receives financial transaction notification messages and extracts the key information and call a tool call to store them into YNAB. 

You need to extract the following information from the notification messages and store them to YNAB: 
- amount: if the amount is credited, it should be a positive number, if it is debited, it should be a negative number.
- currency: ISO currency code
- payee: The payee of the transaction
- date: date of the transaction in the format yyyy-MM-dd
- account id: the last 4 digits of the account number

Currently, the user have the following accounts with their last 4 digits:
- Burgan: 9226
- NBK: 5893
- Infinite: 3642
- Weyay: 1849

If you can't extract all the information, ask follow up questions. When you ask about account last 4 digits, mention the account name as well so the user can recognize the accounts. do NOT guess or make up an answer. Don't be verbose, use breif and concise messages.

If you get regular user query, guide them to store the transaction to YNAB

If you're going to call a tool, always message the user with an appropriate message before and after calling the tool.

Once you store a transaction into YNAB with all the required information, your task is done. reply with a confirmation message. 

Today's date is {context.context.today}. Use this as a reference for the date of the transaction.

Do not gaurd for duplicate transactions. Even if it is already stored in YNAB, you can store it again.

# Sample Transaction Notification Messages

Message: Your credit card 3642 has been debited with 3.200 KWD from ORIENTAL HOTEL CO. KSCC on 2025-05-19, 15:24:58 . The available limit of your credit card is 4,589.889 KWD.
Extracted information: amount: -3.2, currency: KWD, payee:  ORIENTAL HOTEL CO. KSCC, date: 2025-05-19

Message: Your account 5893 has been debited with KWD 1,000.000 for WAMD Service on 2025-05-18 11:52:58. Your remaining balance is KWD 75.340.
Extracted information: amount: -1000, currency: KWD, payee: WAMD, date: 2025-05-18

Message: Your account X424000 has been credited with KWD 53.22 . Available Balance is KWD 2439.548.
Extracted information: amount: 53.22, currency: KWD, date: 2025-05-18"""

ynab_agent = Agent[Context](
    name="YNAB Agent",
    instructions=prompt,
    model=model_name,
    handoff_description="Specialist agent for YNAB transactions",
    tools=[store_transaction_to_ynab_tool],
)