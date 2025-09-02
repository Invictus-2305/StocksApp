from kiteconnect import KiteConnect, KiteTicker
import os
from dotenv import load_dotenv
load_dotenv()

# Read these from your .env or config
API_KEY = os.environ.get("KITE_API_KEY")
API_SECRET = os.environ.get("KITE_API_SECRET")
ACCESS_TOKEN = None  # will be set after login

kite = KiteConnect(api_key=API_KEY)

def generate_login_url():
    return kite.login_url()

def set_access_token(request_token):
    global ACCESS_TOKEN
    data = kite.generate_session(request_token, api_secret=API_SECRET)
    ACCESS_TOKEN = data["access_token"]
    kite.set_access_token(ACCESS_TOKEN)
    return ACCESS_TOKEN

def place_parsed_order(parsed):
    try:
        tradingsymbol = f"{parsed['Instrument']}25AUG{parsed['Premium']}{parsed['Option']}"
        lot_size = 75  # adjust dynamically later

        # Auto-switch order type depending on market hours
        from datetime import datetime
        import pytz
        now = datetime.now(pytz.timezone("Asia/Kolkata"))
        variety = kite.VARIETY_REGULAR if (now.hour >= 9 and (now.hour < 15 or (now.hour == 15 and now.minute <= 30))) else kite.VARIETY_AMO

        print(f"Placing orders for {tradingsymbol}")

        # 1. Entry BUY at Price (LIMIT order)
        entry_price = parsed["Price"]
        entry_order = kite.place_order(
            variety=variety,
            exchange=kite.EXCHANGE_NFO,
            tradingsymbol=tradingsymbol,
            transaction_type=kite.TRANSACTION_TYPE_BUY,
            quantity=lot_size,
            product=kite.PRODUCT_MIS,
            order_type=kite.ORDER_TYPE_LIMIT,   # <- Buy at specific price
            price=entry_price
        )
        print(f"✅ Entry order placed at {entry_price}: {entry_order}")

        # 2. Target SELL at Target1
        target_price = parsed["Target1"]
        target_order = kite.place_order(
            variety=variety,
            exchange=kite.EXCHANGE_NFO,
            tradingsymbol=tradingsymbol,
            transaction_type=kite.TRANSACTION_TYPE_SELL,
            quantity=lot_size,
            product=kite.PRODUCT_MIS,
            order_type=kite.ORDER_TYPE_LIMIT,   # <- Sell at target price
            price=target_price
        )
        print(f"🎯 Target order placed at {target_price}: {target_order}")

        # 3. Stoploss SELL (SL-M)
        stoploss_price = parsed["SL"]
        sl_order = kite.place_order(
            variety=variety,
            exchange=kite.EXCHANGE_NFO,
            tradingsymbol=tradingsymbol,
            transaction_type=kite.TRANSACTION_TYPE_SELL,
            quantity=lot_size,
            product=kite.PRODUCT_MIS,
            order_type=kite.ORDER_TYPE_SLM,     # <- Stoploss-Market
            trigger_price=stoploss_price
        )
        print(f"🛑 Stoploss order placed at {stoploss_price}: {sl_order}")

        return entry_order, target_order, sl_order

    except Exception as e:
        print(f"❌ Failed to place order: {e}")
        return None


