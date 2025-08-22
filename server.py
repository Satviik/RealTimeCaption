# realtime_server.py
from flask import Response, request
from flask_cors import CORS
from flask import Flask, jsonify
import queue
import threading
from test import start_transcription, caption_queue  # import from your test.py

app = Flask(__name__)

CORS(app)
# Start your audio transcription threads once
start_transcription()

# @app.route("/get_caption")
# def get_caption():
#     try:
#         # Non-blocking fetch from queue
#         if not caption_queue.empty():
#             return jsonify({"caption": caption_queue.get()})
#         return jsonify({"caption": ""})
#     except Exception as e:
#         return jsonify({"caption": "", "error": str(e)})
@app.route("/webhook_caption", methods=["POST"])
def webhook_caption():
    try:
        data = request.get_json()
        caption = data.get("caption", "")
        caption_queue.put(caption)  # Store in queue for streaming
        return jsonify({"status": "received"}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 400
    

@app.route("/stream_caption")
def stream_caption():
    def event_stream():
        while True:
            if not caption_queue.empty():
                caption = caption_queue.get()
                yield f"data: {caption}\n\n"
    response = Response(event_stream(), mimetype="text/event-stream")
    response.headers["Cache-Control"] = "no-cache"
    response.headers["Connection"] = "keep-alive"
    response.headers["Access-Control-Allow-Origin"] = "*"
    response.headers["Access-Control-Allow-Credentials"] = "true"
    return response

if __name__ == "__main__":
    app.run(port=5000)
