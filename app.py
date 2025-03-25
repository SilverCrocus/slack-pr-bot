import os
import logging
from flask import Flask, request, jsonify
from dotenv import load_dotenv
from pr_review_bot import pr_webhook
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
        data = request.form
        
        # Handle slash command
        if 'command' in data and data['command'] == '/pr':
            # Get the channel ID and user ID
            channel_id = data.get('channel_id')
            user_id = data.get('user_id')
            
            # Acknowledge the command immediately to prevent timeout
            # This sends the "only visible to you" message
            
            # Then post a visible message to the channel
            try:
                # Post message using the WebClient
                response = client.chat_postMessage(
                    channel=channel_id,
                    text=f"<@{user_id}> requested a PR review! @channel Please review when you have a chance."
                )
            except SlackApiError as e:
                # Print error to console for debugging
                print(f"Error posting message: {e}")
                
            return jsonify({"response_type": "ephemeral", "text": "Processing your PR request..."})
        
        return jsonify({"text": "Command not recognized"})
    else:
        # Default case to ensure we always return something
        return "Method not allowed", 405

# Register routes
app.add_url_rule('/webhook/pr', view_func=pr_webhook, methods=['POST'])
app.add_url_rule('/slack/events', view_func=slack_events, methods=['POST'])
app.add_url_rule('/slack/commands', view_func=handle_slash_command, methods=['POST'])
# No need for a separate route for help commands
# app.add_url_rule('/slack/help-commands', view_func=handle_help_commands, methods=['POST'])

if __name__ == '__main__':
    # Get port from environment variable or use default
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port)
