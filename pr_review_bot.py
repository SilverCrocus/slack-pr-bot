import os
import random
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError
from flask import request, jsonify
import logging
from dotenv import load_dotenv
import json
import traceback
import hmac
import hashlib

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Slack configuration
SLACK_BOT_TOKEN = os.environ.get("SLACK_BOT_TOKEN")
if not SLACK_BOT_TOKEN:
    logger.error("SLACK_BOT_TOKEN not found in environment variables")
    raise ValueError("SLACK_BOT_TOKEN must be set")

client = WebClient(token=SLACK_BOT_TOKEN)

# PR review channel
PR_REVIEW_CHANNEL = os.environ.get("PR_REVIEW_CHANNEL", "model-pr-review")

# Testing mode
TESTING_MODE = os.environ.get("TESTING_MODE", "true").lower() == "false"

# Team configuration - Hard-coded Nigel ID as requested
NIGEL_ID = "UR78CM4LX"
TEAM_MEMBERS = {}

# GitHub username to Slack user ID mapping
GITHUB_TO_SLACK = {
    "diyagamah": "U07B1GFGSF7",  # Hivin
    "khert": "U07AQFHKWJ3",  # Tanvi
    "mortimerme": "UE8MRHUV8",  # Melinda
    "glascottl": "UPK3LK5EX",  # Lachlan
    "huisi": "U048MPX0KK7",  # Sally
    "chinnn": "UR78CM4LX", # Nigel
}

if TESTING_MODE:
    # Use string names for testing
    TEAM_MEMBERS = {
        "Nigel": "Nigel (Test)",
        "Sally": "Sally (Test)",
        "John": "John (Test)",
        "Mary": "Mary (Test)",
    }
else:
    # Use real Slack IDs in production
    TEAM_MEMBERS = {
        "Nigel": NIGEL_ID,
        "Sally": "U048MPX0KK7",
        "Tanvi": "U07AQFHKWJ3",
        "Hivin": "U07B1GFGSF7",
        "Melinda": "UE8MRHUV8",
        "Lachlan": "UPK3LK5EX",
    }

# Last selected reviewers to ensure fair rotation
last_selected = []

# Emoji that indicates claiming a review
CLAIM_EMOJI = "white_check_mark"

def send_slack_message(text, channel=PR_REVIEW_CHANNEL, username='PR Review Bot', icon_emoji=':robot_face:'):
    """Send a message to Slack channel"""
    try:
        response = client.chat_postMessage(
            channel=channel,
            text=text,
            username=username,
            icon_emoji=icon_emoji
        )
        logger.info(f"Message sent to channel {channel}")
        return response
    except SlackApiError as e:
        logger.error(f"Failed to send Slack message: {e.response['error']}")
        return None

def select_reviewers(author_id=None):
    """Select reviewers for PR review"""
    global last_selected
    
    if TESTING_MODE:
        # In testing mode, just use predefined reviewers
        reviewers = [("Nigel", "Nigel (Test)")]
        available_members = [(name, name_display) for name, name_display in TEAM_MEMBERS.items() 
                          if name != "Nigel" and name_display != author_id]
        
        # Select 2 random members
        if len(available_members) >= 2:
            selected = random.sample(available_members, 2)
        else:
            selected = available_members
            
        return reviewers + selected
    
    # Normal production mode
    # Nigel is always a reviewer
    reviewers = [("Nigel", NIGEL_ID)]
    
    # Get all team members except Nigel and the author
    available_members = [(name, user_id) for name, user_id in TEAM_MEMBERS.items() 
                        if name != "Nigel" and user_id != NIGEL_ID and user_id != author_id]
    
    # Prioritize members who haven't been selected recently
    not_recently_selected = [member for member in available_members 
                           if member[0] not in last_selected]
    
    if len(not_recently_selected) >= 2:
        selected = random.sample(not_recently_selected, 2)
    else:
        # If we don't have enough not recently selected, mix in some previously selected
        selected = not_recently_selected + random.sample(
            [m for m in available_members if m[0] not in [nm[0] for nm in not_recently_selected]],
            2 - len(not_recently_selected)
        )
    
    # Update last selected
    last_selected = [s[0] for s in selected]
    
    # Return Nigel plus the two selected members
    return reviewers + selected

def notify_pr_review(pr_data):
    """Notify about a new PR that needs review"""
    # Use mapped Slack ID if available, otherwise use the author name
    author = pr_data.get('author', 'Unknown')
    author_id = pr_data.get('author_slack_id')  # This can be None if no mapping exists
    
    # Log the author information
    logger.info(f"PR Author: GitHub username={author}, Slack ID={author_id}")
    
    # Select reviewers excluding the author's Slack ID
    reviewers = select_reviewers(author_id)
    
    # Primary reviewer is always the first one (Nigel)
    primary_reviewer = reviewers[0]
    additional_reviewers = reviewers[1:]
    
    # Get the URL and title
    url = pr_data.get('url', '#')
    title = pr_data.get('title', 'No title provided')
    
    # Log values for debugging
    logger.info(f"Creating PR review notification with URL: {url}, Title: {title}")
    
    # Format author display - use Slack tag if ID is available
    author_display = author
    if author_id:
        author_display = f"<@{author_id}>"
    
    # Format the message based on testing mode
    if TESTING_MODE:
        # Testing mode - use plain text instead of tags
        message = (
            f"*New PR Needs Review*\n"
            f"*Title:* {title}\n"
            f"*Author:* {author_display}\n"
            f"*URL:* {url}\n\n"
            f"*Primary Reviewer:* {primary_reviewer[1]}\n"
            f"*Additional Reviewers (one needed):* " + 
            " or ".join([reviewer[1] for reviewer in additional_reviewers]) + "\n\n"
            f"React with :{CLAIM_EMOJI}: to claim this review."
        )
    else:
        # Normal mode with user tags
        message = (
            f"*New PR Needs Review*\n"
            f"*Title:* {title}\n"
            f"*Author:* {author_display}\n"
            f"*URL:* {url}\n\n"
            f"*Primary Reviewer:* <@{primary_reviewer[1]}>\n"
            f"*Additional Reviewers (one needed):* " + 
            " or ".join([f"<@{user_id}>" for _, user_id in additional_reviewers]) + "\n\n"
            f"React with :{CLAIM_EMOJI}: to claim this review."
        )
    
    # Use the specified channel if provided, otherwise use the default PR_REVIEW_CHANNEL
    channel = pr_data.get('channel', PR_REVIEW_CHANNEL)
    
    # Send the message
    response = send_slack_message(message, channel=channel)
    
    if response and response['ok']:
        logger.info(f"PR review notification sent, timestamp: {response['ts']}")
        return response
    else:
        logger.error("Failed to send PR review notification")
        return None

# GitHub webhook secret
GITHUB_WEBHOOK_SECRET = os.environ.get("GITHUB_WEBHOOK_SECRET")

def verify_github_webhook(request_data, signature_header):
    """Verify that the webhook request came from GitHub"""
    if not GITHUB_WEBHOOK_SECRET:
        logger.warning("GITHUB_WEBHOOK_SECRET not configured, skipping verification")
        return True
        
    if not signature_header:
        logger.warning("No X-Hub-Signature-256 header in request")
        return False
        
    # Compute the HMAC signature
    expected_signature = 'sha256=' + hmac.new(
        GITHUB_WEBHOOK_SECRET.encode(),
        request_data,
        hashlib.sha256
    ).hexdigest()
    
    # Compare signatures
    return hmac.compare_digest(signature_header, expected_signature)

def pr_webhook():
    """Webhook endpoint to receive PR notifications"""
    try:
        # Log headers for debugging
        logger.info(f"Headers: {dict(request.headers)}")
        
        # Get the event type
        event_type = request.headers.get('X-GitHub-Event')
        logger.info(f"GitHub Event Type: {event_type}")
        
        # Get the signature
        signature = request.headers.get('X-Hub-Signature-256')
        
        # Verify webhook if signature is provided
        if signature and not verify_github_webhook(request.data, signature):
            logger.error("Invalid GitHub webhook signature")
            return jsonify({"status": "error", "message": "Invalid signature"}), 403
        
        data = request.json
        logger.info(f"Received webhook payload: {data}")
        
        # Different event types have different payload structures
        pr_data = {}
        
        # Extract GitHub username for author
        github_author = None
        
        if event_type == 'pull_request':
            # Handle pull_request event
            if data.get('action') == 'opened' or data.get('action') == 'reopened':
                github_author = data.get('pull_request', {}).get('user', {}).get('login')
                
                # Map GitHub username to Slack ID if possible
                slack_author = GITHUB_TO_SLACK.get(github_author)
                logger.info(f"Mapped GitHub author {github_author} to Slack ID {slack_author}")
                
                pr_data = {
                    'title': data.get('pull_request', {}).get('title', 'No title provided'),
                    'repository': data.get('repository', {}).get('full_name', 'Unknown repository'),
                    'author': github_author,
                    'author_slack_id': slack_author,  # This is the key change
                    'url': data.get('pull_request', {}).get('html_url', '#')
                }
            else:
                # Not an event we care about
                return jsonify({"status": "skipped", "message": f"Ignoring pull_request action: {data.get('action')}"}), 200
                
        elif event_type == 'pull_request_review':
            # Handle pull_request_review event
            github_author = data.get('pull_request', {}).get('user', {}).get('login')
            
            # Map GitHub username to Slack ID if possible
            slack_author = GITHUB_TO_SLACK.get(github_author)
            logger.info(f"Mapped GitHub author {github_author} to Slack ID {slack_author}")
            
            pr_data = {
                'title': data.get('pull_request', {}).get('title', 'No title provided'),
                'repository': data.get('repository', {}).get('full_name', 'Unknown repository'),
                'author': github_author,
                'author_slack_id': slack_author,
                'url': data.get('pull_request', {}).get('html_url', '#'),
                'reviewer': data.get('review', {}).get('user', {}).get('login', 'Unknown')
            }
        else:
            return jsonify({"status": "error", "message": f"Unsupported event type: {event_type}"}), 400
        
        # Only proceed if we have valid PR data
        if pr_data:
            # Notify about the PR
            response = notify_pr_review(pr_data)
            
            if response and response['ok']:
                return jsonify({"status": "success", "message": "PR notification sent"}), 200
            else:
                return jsonify({"status": "error", "message": "Failed to send PR notification"}), 500
        else:
            return jsonify({"status": "skipped", "message": "No PR data to process"}), 200
    
    except Exception as e:
        logger.error(f"Error processing webhook: {str(e)}")
        logger.error(traceback.format_exc())
        return jsonify({"status": "error", "message": str(e)}), 500

# Export these values and functions to be used by reaction_handler.py
__all__ = ['select_reviewers', 'notify_pr_review', 'CLAIM_EMOJI']