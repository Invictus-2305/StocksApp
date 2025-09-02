import asyncio
from flask import Flask, redirect, render_template, jsonify, request
from pymongo import MongoClient
from bson.json_util import dumps
import datetime
import os
from dotenv import load_dotenv
import certifi
import threading
import kite
import signal

import teleScript
load_dotenv()

app = Flask(__name__)
ca = certifi.where()
# MongoDB connection
client = MongoClient(os.environ['MONGO_URI'], tlsCAFile=ca)
db = client['test']
collection = db['test']

def delete_session_file():
    try:
        os.remove("session_name.session")
        print("File deleted: 'session_name.session'")
    except:
        print("Failed to delete file: 'session_name.session'")


loop = asyncio.new_event_loop()

def start_background_loop():
    asyncio.set_event_loop(loop)
    loop.run_forever()

threading.Thread(target=start_background_loop, daemon=True).start()


@app.route('/')
def index():
    return render_template("index.html")

@app.route('/data')
def data():
    # Sort by Date and Time, latest first
    records = list(collection.find().sort([("Date", -1), ("Time", -1)]))
    # Convert MongoDB types to plain Python types
    for r in records:
        r['_id'] = str(r['_id'])
        r['Price'] = float(r['Price']) if r.get('Price') is not None else None
        r['SL'] = float(r['SL']) if r.get('SL') is not None else None
        r['Target1'] = float(r['Target1']) if r.get('Target1') is not None else None
        r['Target2'] = float(r['Target2']) if r.get('Target2') is not None else None
        r['Target3'] = float(r['Target3']) if r.get('Target3') is not None else None
    return jsonify(records)

@app.route("/start", methods=['POST'])
def start():

    future = asyncio.run_coroutine_threadsafe(teleScript.is_session_active(), loop)
    session_active = future.result()
    if session_active:
        return jsonify({"status": "already_logged_in"})

    asyncio.run_coroutine_threadsafe(teleScript.request_otp(), loop)
    return jsonify({"status": "otp_required"})


@app.route("/submit-otp", methods=["POST"])
def submit():
    otp = request.json.get("otp")
    asyncio.run_coroutine_threadsafe(teleScript.submit_otp(otp), loop)
    return jsonify({"status": "OTP submitted"})


@app.route("/kite-login")
def kite_login():
    return redirect(kite.generate_login_url())

@app.route("/kite-callback")
def kite_callback():
    request_token = request.args.get("request_token")
    if not request_token:
        return "No request token provided", 400
    access_token = kite.set_access_token(request_token)
    return redirect("/?kite=success")  # Redirect to home page with success query param


# @app.route("/stop-server", methods=["POST"])
# def stop_server():
#     os.kill(os.getpid(), signal.SIGINT)  # Gracefully stop Flask
#     return jsonify({"status": "server_stopped"})

@app.route("/stop-server", methods=["POST"])
def stop_server():
    try:
        with open("gunicorn.pid", "r") as f:
            pid = int(f.read().strip())
        os.kill(pid, signal.SIGTERM)  # stop Gunicorn master
        delete_session_file()  # Delete session file
        loop.call_soon_threadsafe(loop.stop)  # Stop the event loop
        return jsonify({"status": "server_stopped"})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

if __name__ == '__main__': 
    app.run()
