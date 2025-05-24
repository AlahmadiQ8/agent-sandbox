from dataclasses import dataclass
import json
from openai.types.responses import ResponseTextDeltaEvent
from agents import Agent,function_tool, TResponseInputItem, trace, InputGuardrail, GuardrailFunctionOutput, Runner, RunContextWrapper
from pydantic import BaseModel
import asyncio
import setup_azure_openai_client
from datetime import datetime

model_name = "gpt-4.1"

class Context(BaseModel):
    today: str | None = None

@function_tool
def store_transaction_to_ynab_tool(amount: float, currency: str, payee: str, date: str) -> bool:
    # Placeholder function to simulate storing transaction in YNAB
    print(f"Storing transaction in YNAB: {amount} {currency} to {payee} on {date}")
    return True

def prompt(context: RunContextWrapper[Context],  agent: Agent[Context]) -> str:  
    # store date in yyyy-MM-dd format
    today = datetime.now().strftime("%Y-%m-%d")
    return f""""
# Instructions 
You are an AI agent that receives financial transaction notification messages and extracts the key information and call a tool call to store them into YNAB. 

You need to extract the following information from the notification messages and store them to YNAB: 
- amount: positive or negative number depending on whether the amount is credited or debited
- currency: ISO currency code
- payee: The payee of the transaction
- date: date of the transaction in the format yyyy-MM-dd

If you cant extract all the information, ask follow up questions. do NOT guess or make up an answer. 

If you get regular user query, guide them to store the transaction to YNAB

If you're going to call a tool, always message the user with an appropriate message before and after calling the tool.

Once you store a transaction into YNAB with all the required information, your task is done. reply with a confirmation message. 

Today's date is {today}. Use this as a reference for the date of the transaction.

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
    # output_type=YNABTransactionOutput,
    tools=[store_transaction_to_ynab_tool],
)

async def main():
    input_items: list[TResponseInputItem] = []
    context = Context()
    while True:
        user_input = input("Enter your message: ")

        with trace("YNAB Agent", group_id="ynab"):
            input_items.append({"content": user_input, "role": "user"})
            result = await Runner.run(ynab_agent, input_items, context=context)
            print(result.final_output)
            input_items = result.to_input_list()
            # print input_items as formatted json data using json dump
            print(json.dumps(input_items, indent=4))


if __name__ == "__main__":
    asyncio.run(main())