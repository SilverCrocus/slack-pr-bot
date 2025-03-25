import os
import logging
from flask import Flask, request, jsonify
from dotenv import load_dotenv
from pr_review_bot import pr_webhook
from reaction_handler import slack_events, handle_pr_slash_command
from slash_commands import handle_slash_command as handle_help_commands

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Initialize Flask app
app = Flask(__name__)

# Add a root route handler
@app.route("/", methods=["GET", "POST", "HEAD"])
def home():
    if request.method == "HEAD" or request.method == "GET":
        return "Slack PR Bot is running!"
    elif request.method == "POST":
        # Handle your Slack POST requests here
        return jsonify({"status": "ok"})
    else:
        # Default case to ensure we always return something
        return "Method not allowed", 405

# Register routes
app.add_url_rule('/webhook/pr', view_func=pr_webhook, methods=['POST'])
app.add_url_rule('/slack/events', view_func=slack_events, methods=['POST'])
app.add_url_rule('/slack/commands', view_func=handle_pr_slash_command, methods=['POST'])
app.add_url_rule('/slack/help-commands', view_func=handle_help_commands, methods=['POST'])

if __name__ == '__main__':
    # Get port from environment variable or use default
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port)
