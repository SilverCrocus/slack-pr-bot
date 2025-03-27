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
    """Process incoming Slack slash commands"""
    data = request.form
    
    logger.info(f"Received slash command: {data}")
    
    command = data.get('command')
    channel_id = data.get('channel_id')
    user_id = data.get('user_id')
    text = data.get('text', '')
    
    if command == '/pr':
        parts = text.strip().split(' ', 1)
        
        if not parts or not parts[0]:
            return jsonify({
                "response_type": "ephemeral",
                "text": "Please provide both a URL and title. Format: `/pr [URL] [Title]`"
            })
            
        url = parts[0]
        title = parts[1] if len(parts) > 1 else 'PR Review Request'
        
        logger.info(f"Parsed URL: {url}, Title: {title}")
        
        pr_data = {
            'title': title,
            'repository': title,
            'author': f"<@{user_id}>",
            'url': url,
            'channel': channel_id
        }
        
        response_data = {"response_type": "ephemeral", "text": "Processing your PR review request..."}
        
        try:
            notify_pr_review(pr_data)
        except Exception as e:
            logger.error(f"Error processing PR review request: {str(e)}")
            response_data = {"response_type": "ephemeral", "text": f"Error processing your request: {str(e)}"}
        
        return jsonify(response_data)
    
    return jsonify({"response_type": "ephemeral", "text": "Unknown command"})

def handle_pr_command(text, user_id):
    """Create a new PR review request from slash command text"""
    parts = text.strip().split(' ', 1)
    
    if len(parts) < 2:
        return jsonify({
            'response_type': 'ephemeral',
            'text': 'Please provide both URL and title for the PR. Format: `/pr [URL] [Title]`'
        })
    
    url = parts[0]
    title = parts[1]
    
    try:
        user_info = client.users_info(user=user_id)
        author = user_info['user']['name']
    except SlackApiError:
        author = "Unknown"
    
    message = (
        f"*New PR Needs Review:* {title}\n"
        f"*Repository:* Manual PR Request\n"
        f"*Author:* {author}\n"
        f"*URL:* {url}\n\n"
        f"*Requested by:* <@{user_id}>"
    )
    
    return jsonify({
        'response_type': 'in_channel',
        'text': message
    })

def select_reviewers_safely(author_id=None):
    """Safely select reviewers, handling any exceptions"""
    try:
        from pr_review_bot import select_reviewers, CLAIM_EMOJI
        return select_reviewers(author_id)
    except Exception as e:
        logger.error(f"Error selecting reviewers: {e}")
        return []

if __name__ == '__main__':
    app.run(debug=True, port=5000)
