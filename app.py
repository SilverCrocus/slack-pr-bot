from flask import Flask, request
import os
from slack_bolt.adapter.flask import SlackRequestHandler
from slack_bot import app as slack_app

flask_app = Flask(__name__)
handler = SlackRequestHandler(slack_app)

@flask_app.route("/slack/events", methods=["POST"])
def slack_events():
    return handler.handle(request)

@flask_app.route('/', methods=['GET'])
def home():
    return "Slack Bot is up and running!"

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    flask_app.run(host='0.0.0.0', port=port)
