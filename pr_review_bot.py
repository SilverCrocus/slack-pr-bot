import os
import random
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
        "Hivin": "U07B1GFGSF7"
        # "Member3": "U3333333333",
        # "Member4": "U4444444444",
        # "Member5": "U5555555555",
        # "Member6": "U6666666666",
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

def select_reviewers():
    """Select reviewers for PR review"""
    global last_selected
    
    if TESTING_MODE:
        # In testing mode, just use predefined reviewers
        reviewers = [("Nigel", "Nigel (Test)")]
        available_members = [(name, name_display) for name, name_display in TEAM_MEMBERS.items() 
                          if name != "Nigel"]
        
        # Select 2 random members
        if len(available_members) >= 2:
            selected = random.sample(available_members, 2)
        else:
            selected = available_members
            
        return reviewers + selected
    
    # Normal production mode
    # Nigel is always a reviewer
    reviewers = [("Nigel", NIGEL_ID)]
    
    # Get all team members except Nigel
    available_members = [(name, user_id) for name, user_id in TEAM_MEMBERS.items() 
                        if name != "Nigel" and user_id != NIGEL_ID]
    
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
    reviewers = select_reviewers()
    
    # Primary reviewer is always the first one (Nigel)
    primary_reviewer = reviewers[0]
    additional_reviewers = reviewers[1:]
    
    # Format the message based on testing mode
    if TESTING_MODE:
        # Testing mode - use plain text instead of tags
        message = (
            f"*[TEST MODE] New PR Needs Review:* {pr_data.get('title', 'No title provided')}\n"
            f"*Repository:* {pr_data.get('repository', 'Unknown')}\n"
            f"*Author:* {pr_data.get('author', 'Unknown')}\n"
            f"*URL:* {pr_data.get('url', '#')}\n\n"
            f"*Primary Reviewer:* {primary_reviewer[1]}\n"
            f"*Additional Reviewers (one needed):* " + 
            " or ".join([reviewer[1] for reviewer in additional_reviewers]) + "\n\n"
            f"React with :{CLAIM_EMOJI}: to claim this review."
        )
    else:
        # Normal mode with user tags
        message = (
            f"*New PR Needs Review:* {pr_data.get('title', 'No title provided')}\n"
            f"*Repository:* {pr_data.get('repository', 'Unknown')}\n"
            f"*Author:* {pr_data.get('author', 'Unknown')}\n"
            f"*URL:* {pr_data.get('url', '#')}\n\n"
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

def pr_webhook():
    """Webhook endpoint to receive PR notifications"""
    try:
        data = request.json
        logger.info(f"Received webhook: {data}")
        
        # Process the PR data
        pr_data = {
            'title': data.get('pull_request', {}).get('title', 'No title provided'),
            'repository': data.get('repository', {}).get('full_name', 'Unknown repository'),
            'author': data.get('pull_request', {}).get('user', {}).get('login', 'Unknown'),
            'url': data.get('pull_request', {}).get('html_url', '#')
        }
        
        # Notify about the PR
        response = notify_pr_review(pr_data)
        
        if response and response['ok']:
            return jsonify({"status": "success", "message": "PR notification sent"}), 200
        else:
            return jsonify({"status": "error", "message": "Failed to send PR notification"}), 500
    
    except Exception as e:
        logger.error(f"Error processing webhook: {str(e)}")
        logger.error(traceback.format_exc())
        return jsonify({"status": "error", "message": str(e)}), 500

# Export these values and functions to be used by reaction_handler.py
__all__ = ['select_reviewers', 'notify_pr_review', 'CLAIM_EMOJI']
