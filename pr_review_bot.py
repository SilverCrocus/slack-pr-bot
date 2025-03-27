import os
import random
import hmac
import hashlib
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError
from flask import request, jsonify
import logging
from dotenv import load_dotenv
import json
import traceback

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

# Team configuration
NIGEL_ID = os.environ.get("NIGEL_ID", "U0123456789")
TEAM_MEMBERS = {}

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
        # "Member5": "U5555555555",
        # "Member6": "U6666666666",
    }

# Last selected reviewers to ensure fair rotation
last_selected = []

# Emoji that indicates claiming a review
CLAIM_EMOJI = "white_check_mark"

# GitHub webhook secret for verification
GITHUB_WEBHOOK_SECRET = os.environ.get("GITHUB_WEBHOOK_SECRET", "")

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
    # Extract author ID if present
    author = pr_data.get('author', 'Unknown')
    author_id = None
    
    # If author is in the format "<@USER_ID>", extract the USER_ID
    if author.startswith('<@') and author.endswith('>'):
        author_id = author[2:-1]  # Remove "<@" and ">"
    
    # Select reviewers excluding the author
    reviewers = select_reviewers(author_id)
    
    # Primary reviewer is always the first one (Nigel)
    primary_reviewer = reviewers[0]
    additional_reviewers = reviewers[1:]
    
    # Get the URL and title
    url = pr_data.get('url', '#')
    title = pr_data.get('title', 'No title provided')
    
    # Log values for debugging
    logger.info(f"Creating PR review notification with URL: {url}, Title: {title}")
    
    # Format the message based on testing mode
    if TESTING_MODE:
        # Testing mode - use plain text instead of tags
        message = (
            f"*New PR Needs Review*\n"
            f"*Repository:* {title}\n"
            f"*Author:* {pr_data.get('author', 'Unknown')}\n"
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
            f"*Repository:* {title}\n"
            f"*Author:* {pr_data.get('author', 'Unknown')}\n"
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

def verify_github_signature(request_data, signature_header):
    """Verify that the webhook request came from GitHub by checking the signature"""
    if not GITHUB_WEBHOOK_SECRET:
        logger.warning("GITHUB_WEBHOOK_SECRET not set, skipping webhook signature verification")
        return True
        
    if not signature_header:
        logger.error("No X-Hub-Signature-256 header in request")
        return False
        
    # Get expected signature
    expected_signature = "sha256=" + hmac.new(
        GITHUB_WEBHOOK_SECRET.encode('utf-8'),
        request_data,
        hashlib.sha256
    ).hexdigest()
    
    return hmac.compare_digest(signature_header, expected_signature)

def pr_webhook():
    """Webhook endpoint to receive PR notifications from GitHub"""
    try:
        # Log raw request data for debugging
        logger.info(f"Received webhook request at /webhook/pr")
        logger.info(f"Headers: {dict(request.headers)}")
        
        # Check if we're getting JSON data
        is_json = request.is_json
        logger.info(f"Request contains JSON: {is_json}")
        
        # Get the signature header
        signature_header = request.headers.get('X-Hub-Signature-256')
        logger.info(f"Signature header present: {signature_header is not None}")
        
        # For now, temporarily disable signature verification for debugging
        # if GITHUB_WEBHOOK_SECRET and signature_header:
        #     if not verify_github_signature(request.data, signature_header):
        #         logger.error("Invalid webhook signature")
        #         return jsonify({"status": "error", "message": "Invalid signature"}), 401
        
        # Get the event type
        event_type = request.headers.get('X-GitHub-Event')
        logger.info(f"GitHub event type: {event_type}")
        
        # Try to parse JSON, with fallback
        try:
            if is_json:
                data = request.json
            else:
                logger.warning("Request not in JSON format, attempting to parse body as JSON")
                data = json.loads(request.data.decode('utf-8'))
        except Exception as json_error:
            logger.error(f"Failed to parse JSON: {str(json_error)}")
            logger.error(f"Raw request data: {request.data}")
            return jsonify({"status": "error", "message": "Invalid JSON payload"}), 400
        
        logger.info(f"Parsed webhook data action: {data.get('action', 'unknown')}")
        
        # For debugging, accept all pull_request events temporarily
        if event_type == 'pull_request':
            # For debugging, allow all PR actions temporarily  
            # if data.get('action') not in ['opened', 'reopened']:
            #     return jsonify({"status": "ignored", "message": f"PR action {data.get('action')} ignored"}), 200
            
            # Extract PR data with more error handling
            try:
                pr_data = {
                    'title': data.get('repository', {}).get('full_name', 'Unknown repository'),
                    'repository': data.get('repository', {}).get('full_name', 'Unknown repository'),
                    'author': f"<@{data.get('pull_request', {}).get('user', {}).get('login', 'Unknown')}>",
                    'url': data.get('pull_request', {}).get('html_url', '#')
                }
                
                logger.info(f"Processed PR data: {pr_data}")
                
                # Notify about the PR
                response = notify_pr_review(pr_data)
                
                if response and response.get('ok'):
                    return jsonify({"status": "success", "message": "PR notification sent"}), 200
                else:
                    logger.error(f"Failed to send notification: {response}")
                    return jsonify({"status": "error", "message": "Failed to send PR notification"}), 500
            
            except Exception as extract_error:
                logger.error(f"Error extracting PR data: {str(extract_error)}")
                logger.error(traceback.format_exc())
                return jsonify({"status": "error", "message": f"Error processing PR data: {str(extract_error)}"}), 500
        else:
            logger.info(f"Ignoring non-pull_request event: {event_type}")
            # Return 200 OK for ignored events (GitHub expects this)
            return jsonify({"status": "ignored", "message": f"Event type {event_type} ignored"}), 200
    
    except Exception as e:
        logger.error(f"Error processing webhook: {str(e)}")
        logger.error(traceback.format_exc())
        return jsonify({"status": "error", "message": str(e)}), 500

# Export these values and functions to be used by reaction_handler.py
__all__ = ['select_reviewers', 'notify_pr_review', 'CLAIM_EMOJI']
