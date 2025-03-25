import os
from flask import Flask, request, jsonify
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError
import logging
from dotenv import load_dotenv
from pr_review_bot import TEAM_MEMBERS, notify_pr_review, CLAIM_EMOJI

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
    
    # Create a simple message
    message = (
        f"*New PR Needs Review:* {title}\n"
        f"*Repository:* Manual PR Request\n"
        f"*Author:* {author}\n"
        f"*URL:* {url}\n\n"
        f"*Requested by:* <@{user_id}>"
    )
    
    # Return a response that will be visible to everyone in the channel
    return jsonify({
        'response_type': 'in_channel',  # This is the key - it makes the message public
        'text': message
    })

def select_reviewers_safely():
    """A safer version of select_reviewers that handles missing team members"""
    try:
        from pr_review_bot import select_reviewers, CLAIM_EMOJI
        return select_reviewers()
    except Exception as e:
        logger.error(f"Error selecting reviewers: {e}")
        # Return an empty list if there's an error
        return []

# Export the app to be used in the main application
if __name__ == '__main__':
    app.run(debug=True, port=5000)
