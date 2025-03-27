import os
import logging
from flask import Flask, request, jsonify
from dotenv import load_dotenv
from pr_review_bot import pr_webhook, notify_pr_review
from reaction_handler import slack_events
from slash_commands import handle_slash_command
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError

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

# Initialize Slack client with your bot token
slack_token = os.environ.get('SLACK_BOT_TOKEN')
client = WebClient(token=slack_token)

# Add a root route handler
@app.route("/", methods=["GET", "POST", "HEAD"])
def home():
    if request.method == "HEAD" or request.method == "GET":
        return "Slack PR Bot is running!"
    elif request.method == "POST":
        # Since your slash command URL is pointing to the root URL,
        # we need to process the slash command here or redirect it
        data = request.form
        
        if 'command' in data and data['command'] == '/pr':
            # Forward to the slash command handler
            return handle_slash_command()
        
        return jsonify({"text": "Please use the proper slash command endpoint"})
    else:
        # Default case to ensure we always return something
        return "Method not allowed", 405

# Add a test endpoint for webhook debugging
@app.route('/webhook/test', methods=['GET', 'POST'])
def webhook_test():
    """Test endpoint for webhook debugging"""
    if request.method == 'GET':
        return jsonify({"status": "ok", "message": "Webhook test endpoint is working"}), 200
    elif request.method == 'POST':
        logger.info(f"Received test webhook POST with headers: {dict(request.headers)}")
        logger.info(f"Request data: {request.data}")
        
        try:
            if request.is_json:
                data = request.json
                logger.info(f"JSON data: {data}")
            else:
                logger.info(f"Raw data (not JSON): {request.data}")
        except Exception as e:
            logger.error(f"Error parsing request: {str(e)}")
        
        return jsonify({"status": "success", "message": "Test webhook received"}), 200

# Register routes
app.add_url_rule('/webhook/pr', view_func=pr_webhook, methods=['GET', 'POST'])

@app.route('/slack/events', methods=['POST'])
def events_endpoint():
    """Wrapper for slack_events to add more logging"""
    logger.info(f"Received event at /slack/events with data: {request.data}")
    return slack_events()

app.add_url_rule('/slack/commands', view_func=handle_slash_command, methods=['POST'])
# No need for a separate route for help commands
# app.add_url_rule('/slack/help-commands', view_func=handle_help_commands, methods=['POST'])

if __name__ == '__main__':
    # Get port from environment variable or use default
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port)
