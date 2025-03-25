import os
from flask import Flask, request, jsonify
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError
import logging
from dotenv import load_dotenv
from pr_review_bot import TEAM_MEMBERS, notify_pr_review

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

def handle_slash_command():
    """Handle incoming slash commands from Slack"""
    # Verify the request came from Slack (in production, implement proper verification)
    
    command = request.form.get('command', '')
    text = request.form.get('text', '')
    user_id = request.form.get('user_id', '')
    
    logger.info(f"Received slash command: {command} with text: {text} from user: {user_id}")
    
    if command == '/pr':
        return handle_pr_command(text, user_id)
    elif command == '/pr-help':
        return jsonify({
            'response_type': 'ephemeral',
            'text': 'PR Review Bot Commands:\n• `/pr-help` - Show this help message\n• `/pr-team` - Show current team members\n• `/pr [URL] [Title]` - Create a PR review request'
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

def handle_pr_command(text, user_id):
    """Handle the /pr command to create a new PR review request"""
    # Parse the command text - first part as URL, rest as title
    parts = text.strip().split(' ', 1)
    
    if len(parts) < 2:
        return jsonify({
            'response_type': 'ephemeral',
            'text': 'Please provide both URL and title for the PR. Format: `/pr [URL] [Title]`'
        })
    
    url = parts[0]
    title = parts[1]
    
    # Get user info to find out who initiated the PR review
    try:
        user_info = client.users_info(user=user_id)
        author = user_info['user']['name']
    except SlackApiError:
        author = "Unknown"
    
    # Create the PR data
    pr_data = {
        'title': title,
        'url': url,
        'repository': 'Manual PR Request',
        'author': author
    }
    
    # Send the notification
    response = notify_pr_review(pr_data)
    
    if response and response.get('ok'):
        return jsonify({
            'response_type': 'ephemeral',
            'text': 'PR review request has been posted to the channel!'
        })
    else:
        return jsonify({
            'response_type': 'ephemeral',
            'text': 'Failed to post PR review request. Please try again or contact an administrator.'
        })

# Export the app to be used in the main application
if __name__ == '__main__':
    app.run(debug=True, port=5000)
