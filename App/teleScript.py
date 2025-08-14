from telethon import TelegramClient, events
import asyncio
import pytz
import re
import datetime
import pprint
from pymongo import MongoClient
import os
from dotenv import load_dotenv
import certifi

load_dotenv()
api_id = os.getenv("TELEGRAM_API_ID")
api_hash = os.getenv("TELEGRAM_API_HASH")
phone_number = os.getenv("PHONE_NUMBER")

client = TelegramClient('session_name', api_id, api_hash)
ca = certifi.where()

MONGO_URI = os.getenv("MONGO_URI")
client_mongo = MongoClient(MONGO_URI, tlsCAFile=ca)
db = client_mongo['test']
collection = db['test']

chat1 = -4911447447
chat2 = 7025735649

ist = pytz.timezone("Asia/Kolkata")

SESSION_FILE = "session_name" 

async def is_session_active():
    if not os.path.exists(SESSION_FILE + ".session"):
        return False
    try:
        temp_client = TelegramClient(SESSION_FILE, api_id, api_hash)
        await temp_client.connect()
        authorized = await temp_client.is_user_authorized()
        await temp_client.disconnect()
        return authorized
    except Exception:
        return False


def parse_message_type1(text):
    raw_lines = text.strip().split("\n")
    lines = [ line.strip() for line in raw_lines if line != ""]
    match1 = re.match(r"([A-Z]+[0-9]*[A-Z]*)\s+(\d+[A-Z]+)?\s+NEAR\s+(\d+(\.\d+)?)", lines[0], re.IGNORECASE)
    if not match1:
        return None
    instrument = match1.group(1)
    premium = match1.group(2)
    option = "CE" if "CE" in premium else "PE"
    premium = premium.replace(option, "")
    price = float(match1.group(3))

    match2 = re.match(r"SL\s+(\d+(\.\d+)?)", lines[1], re.IGNORECASE)
    if not match2:
        return None
    sl = float(match2.group(1)) if match2 else None

    match3 = re.match(r"TGT\s+([\d\.]+)\+?(?:-([\d\.]+)\+?)?(?:-([\d\.]+)\+?)?",lines[2],re.IGNORECASE)
    targets = match3.groups()
    if not match3:
        return None
    target1 = float(targets[0]) if targets[0] else None
    target2 = float(targets[1]) if targets[1] else None
    target3 = float(targets[2]) if targets[2] else None


    return {
        "Instrument": instrument,
        "Premium": premium,
        "Option": option,
        "Price": price,
        "SL": sl,
        "Target1": target1,
        "Target2": target2,
        "Target3": target3,
    }
def parse_message_type2(text):

    match1 = match1 = re.match(r"^([A-Z]+)\s*.*?(\d+)\s*(CE|PE)$", text['instrument'], re.IGNORECASE)
    if not match1:
        return None
    instrument = match1.group(1)
    premium = match1.group(2)
    option = match1.group(3)if match1 else None

    match2 = re.match(r"ABV\s+(\d+(\.\d+)?)", text['abv'], re.IGNORECASE)
    price = float(match2.group(1)) if match2 else None

    match3 = re.match(r"SL\s+([\d\.]+)\s+TGT\s+([\d\.]+)\+*(?:,([\d\.]+)\+*)?(?:,([\d\.]+)\+*)?",text['tgt'],re.IGNORECASE)
    if not match3:
        return None

    def clean_target(val):
        return float(val.replace("+", "")) if val else None
    sl = float(match3.group(1)) if match3 else None

    target1 = clean_target(match3.group(2))
    target2 = clean_target(match3.group(3))
    target3 = clean_target(match3.group(4))


    return {
        "Instrument": instrument,
        "Premium": premium,
        "Price": price,
        "Option": option,
        "SL": sl,
        "Target1": target1,
        "Target2": target2,
        "Target3": target3,
    }

def save_to_mongo(data):
    collection.insert_one(data)

chat2_buffer = {
          "instrument": None,
          "abv": None,
          "tgt": None,
      }

async def request_otp():
    """Step 1: Send OTP request"""
    await client.connect()
    if not await client.is_user_authorized():
        await client.send_code_request(phone_number)
        print("OTP sent to Telegram account.")

async def submit_otp(otp):
    """Step 2: Submit OTP from webapp"""
    await client.sign_in(phone_number, otp)
    print("OTP verified, starting client...")
    await client.run_until_disconnected()

@client.on(events.NewMessage(chats=[chat1,chat2]))
async def handler(event):
    msg = event.message
    text = msg.text if msg.text else "<Non-text message>"
    date = msg.date.astimezone(ist).strftime("%Y-%m-%d")
    time = msg.date.astimezone(ist).strftime("%H:%M:%S")
    # if msg.sender_id == 7025735649:
    #   print(f"[{ist_time} IST] {msg.sender_id}: {text}")
    # print(f"[{ist_time}]: {text}")
    if event.chat_id == chat1:
      parsed = parse_message_type1(text)
      if parsed:
          parsed["Date"] = date
          parsed["Time"] = time
          save_to_mongo(parsed)
    elif event.chat_id == chat2:
      if re.match(r"^[A-Z]+.*\d+\s*(CE|PE)$", text, re.IGNORECASE):
          chat2_buffer["instrument"] = text.strip()

      elif re.match(r"^ABV\s+\d+", text, re.IGNORECASE):
          chat2_buffer["abv"] = text.strip()

      elif re.match(r"^SL\s+.*", text, re.IGNORECASE):
          chat2_buffer["tgt"] = text.strip()

      if chat2_buffer["instrument"] and chat2_buffer["abv"] and chat2_buffer["tgt"]:
          parsed = parse_message_type2(chat2_buffer)
          if parsed:
              parsed["Date"] = date
              parsed["Time"] = time
              save_to_mongo(parsed)
              chat2_buffer.update({"instrument": None, "sl": None, "tgt": None})


async def main():
    if await is_session_active():
        print("Session is active, starting client...")
        await client.connect()
    else:
        print("Session missing or expired, requesting OTP...")
        await client.connect()
        await client.send_code_request(phone_number)
        otp = input("Enter the OTP sent to your Telegram: ")
        await client.sign_in(phone_number, otp)

    await client.run_until_disconnected()


if __name__ == "__main__":
    asyncio.run(main())
