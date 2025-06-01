from flask import Flask, request, jsonify, render_template
import time
import traceback
from collections import OrderedDict  # To keep miners in order of appearance (optional)

app = Flask(__name__)

# In-memory storage for miner statistics.
# Structure: { "wallet_address": {"cpu_usage": X, "uptime": Y, "timestamp": Z, "server_timestamp": T} }
# Using OrderedDict to potentially show miners in the order they first reported.
miner_data = OrderedDict()
MAX_MINERS_DISPLAYED = 100  # Limit the number of miners stored to prevent memory issues


@app.route('/', methods=['POST'])  # This is where your main.py will send data
def receive_stats():
    try:
        data = request.get_json()
        if not data:
            return jsonify({"status": "error", "message": "No data provided"}), 400

        wallet = data.get('wallet')
        cpu_usage = data.get('cpu_usage')
        uptime = data.get('uptime')
        client_timestamp = data.get('timestamp')  # Timestamp from the client

        if not all([wallet, cpu_usage is not None, uptime is not None, client_timestamp is not None]):
            return jsonify({"status": "error", "message": "Missing required fields"}), 400

        # Store or update the data for this wallet
        # Add a server-side timestamp to know when we last heard from it
        miner_data[wallet] = {
            "cpu_usage": float(cpu_usage),
            "uptime": int(uptime),
            "client_timestamp": int(client_timestamp),
            "server_timestamp": int(time.time())  # Timestamp when server received it
        }

        # Optional: Limit the number of miners stored to prevent unbounded memory growth
        while len(miner_data) > MAX_MINERS_DISPLAYED:
            miner_data.popitem(last=False)  # Remove the oldest entry if using OrderedDict

        print(f"Received data from {wallet}: CPU {cpu_usage}%, Uptime {uptime}s")
        return jsonify({"status": "success", "message": "Data received"}), 200

    except Exception as e:
        print(f"Error processing request: {e}")
        traceback.print_exc()
        return jsonify({"status": "error", "message": "Internal server error"}), 500


@app.route('/dashboard')
def dashboard_page():
    return render_template('dashboard.html')


@app.route('/api/stats')
def get_all_stats():
    global miner_data  # Declare miner_data as global at the start of the function

    # Simple cleanup: remove miners not seen in a while (e.g., 10 minutes)
    # This is optional and can be more sophisticated
    current_time = int(time.time())
    stale_threshold = 600  # 10 minutes

    # Create a new dictionary for active miners to avoid modifying during iteration
    active_miner_data = OrderedDict()
    # Now it's safe to read from the global miner_data
    for wallet, data in miner_data.items():
        if current_time - data.get("server_timestamp", 0) < stale_threshold:
            active_miner_data[wallet] = data

    # Update the global miner_data with only active ones
    # This is a simple way; for many miners, a proper DB or cleanup task is better
    miner_data = active_miner_data # Assignment to the global miner_data

    return jsonify(miner_data)


if __name__ == '__main__':
    # For local testing. Render will use gunicorn.
    app.run(debug=True, host='0.0.0.0', port=5000)
