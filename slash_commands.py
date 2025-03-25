import os
from flask import Flask, request, jsonify
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError
import logging
from dotenv import load_dotenv
from pr_review_bot import TEAM_MEMBERS

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

# Slack configuration
SLACK_BOT_TOKEN = os.environ.get("SLACK_BOT_TOKEN")
if not SLACK_BOT_TOKEN:
    logger.error("SLACK_BOT_TOKEN not found in environment variables")
    raise ValueError("SLACK_BOT_TOKEN must be set")

client = WebClient(token=SLACK_BOT_TOKEN)

@app.route('/slack/commands', methods=['POST'])
def handle_slash_command():
    """Handle incoming slash commands from Slack"""
    # Verify the request came from Slack (in production, implement proper verification)
    
    command = request.form.get('command', '')
    text = request.form.get('text', '')
    user_id = request.form.get('user_id', '')
    
    logger.info(f"Received slash command: {command} with text: {text} from user: {user_id}")
    
    if command == '/pr-help':
        return jsonify({
            'response_type': 'ephemeral',
            'text': 'PR Review Bot Commands:\n• `/pr-help` - Show this help message\n• `/pr-team` - Show current team members'
        })
    elif command == '/pr-team':
        team_list = "\n".join([f"• {name}" for name in TEAM_MEMBERS.keys()])
        return jsonify({
            'response_type': 'ephemeral',
            'text': f"Current PR Review Team:\n{team_list}"
        })
    else:
        return jsonify({
            'response_type': 'ephemeral',
            'text': 'Unknown command. Try `/pr-help` for available commands.'
        })

# Export the app to be used in the main application
if __name__ == '__main__':
    app.run(debug=True, port=5000)
