from kiteconnect import KiteConnect, KiteTicker

# Read these from your .env or config
API_KEY = "your_api_key"
API_SECRET = "your_api_secret"
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

def place_order(symbol, qty, txn_type, price=None):
    return kite.place_order(
        variety=kite.VARIETY_REGULAR,
        exchange=kite.EXCHANGE_NSE,
        tradingsymbol=symbol,
        transaction_type=txn_type,  # BUY or SELL
        quantity=qty,
        product=kite.PRODUCT_MIS,
        order_type=kite.ORDER_TYPE_LIMIT if price else kite.ORDER_TYPE_MARKET,
        price=price
    )
