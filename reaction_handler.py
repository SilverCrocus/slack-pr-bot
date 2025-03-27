import os
import logging
import json
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError
from flask import Flask, request, jsonify, Response
from pr_review_bot import select_reviewers, CLAIM_EMOJI
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Slack configuration from environment variables
SLACK_BOT_TOKEN = os.environ.get("SLACK_BOT_TOKEN")
if not SLACK_BOT_TOKEN:
    logger.error("SLACK_BOT_TOKEN not found in environment variables")
    raise ValueError("SLACK_BOT_TOKEN must be set")

NIGEL_ID = os.environ.get("NIGEL_ID", "U0123456789")
PR_REVIEW_CHANNEL = os.environ.get("PR_REVIEW_CHANNEL", "pr-reviews")
CLAIM_EMOJI = "white_check_mark"

# Initialize Slack client
client = WebClient(token=SLACK_BOT_TOKEN)

def handle_reaction(event_data):
    """Handle reaction added events for PR review claims"""
    try:
        # Check if it's the claim emoji
        if event_data.get('reaction') != CLAIM_EMOJI:
            return {"status": "ignored", "reason": "Not a claim emoji"}
            
        # Get event details
        user_id = event_data.get('user')
        item = event_data.get('item', {})
        channel = item.get('channel')
        timestamp = item.get('ts')
        
        if not all([user_id, channel, timestamp]):
            return {"status": "error", "reason": "Missing required event data"}
            
        # Get the original message to check if it's a PR review message
        try:
            result = client.conversations_history(
                channel=channel,
                inclusive=True,
                latest=timestamp,
                limit=1
            )
            
            if not result['ok'] or not result['messages']:
                return {"status": "error", "reason": "Couldn't retrieve original message"}
                
            original_message = result['messages'][0]
            
            # Check if this is a PR review message (by looking for our specific text)
            if "New PR Needs Review:" not in original_message.get('text', ''):
                return {"status": "ignored", "reason": "Not a PR review message"}
                
            # Check if the user is one of the additional reviewers
            if user_id not in original_message.get('text', ''):
                return {"status": "ignored", "reason": "User not an assigned reviewer"}
                
            # Get user information
            user_info = client.users_info(user=user_id)
            if not user_info['ok']:
                logger.error(f"Failed to get user info: {user_info.get('error')}")
                reviewer_name = "Unknown User"
            else:
                reviewer_name = user_info['user'].get('real_name', user_info['user'].get('name', 'Unknown User'))
                
            # Update the original message
            updated_text = original_message.get('text', '') + f"\n\n*Review claimed by <@{user_id}> ({reviewer_name})!*"
            
            update_response = client.chat_update(
                channel=channel,
                ts=timestamp,
                text=updated_text
            )
            
            # Notify Nigel
            dm_channel = client.conversations_open(users=NIGEL_ID)
            if dm_channel['ok']:
                client.chat_postMessage(
                    channel=dm_channel['channel']['id'],
                    text=f"*PR Review Update:* <@{user_id}> ({reviewer_name}) has claimed the review for the PR.\n"
                         f"*Original Message:* https://slack.com/archives/{channel}/p{timestamp.replace('.', '')}"
                )
                
            return {"status": "success", "reviewer": reviewer_name}
            
        except SlackApiError as e:
            logger.error(f"Error processing reaction: {e.response['error']}")
            return {"status": "error", "reason": str(e.response['error'])}
            
    except Exception as e:
        logger.error(f"Unexpected error processing reaction: {str(e)}")
        return {"status": "error", "reason": str(e)}

def handle_pr_command(event_data):
    """Handle messages with -pr command for PR review assignments"""
    try:
        # Get message text and user
        text = event_data.get('text', '')
        user_id = event_data.get('user')
        channel = event_data.get('channel')
        
        # Check if this is a -pr command
        if not text.startswith('-pr '):
            return {"status": "ignored", "reason": "Not a PR command"}
            
        # Parse the command: -pr URL Title
        parts = text[4:].strip().split(' ', 1)  # Split into URL and title
        if len(parts) < 2:
            client.chat_postMessage(
                channel=channel,
                text="Error: Please use the format `-pr URL Title`"
            )
            return {"status": "error", "reason": "Invalid command format"}
            
        # ...rest of the handle_pr_command implementation...
    
    except Exception as e:
        logger.error(f"Unexpected error processing PR command: {str(e)}")
        return {"status": "error", "reason": str(e)}

def handle_mention(event_data):
    """Handle when someone mentions the bot"""
    try:
        # Get message text and user
        text = event_data.get('text', '')
        user_id = event_data.get('user')
        channel = event_data.get('channel')
        
        # Remove the bot mention from text
        # Example: "<@BOT_ID> https://github.com/repo/pull/123 Add feature"
        # We need to extract just the URL and title
        parts = text.split(' ', 1)
        if len(parts) < 2:
            client.chat_postMessage(
                channel=channel,
                text="Please include both the PR URL and title after mentioning me."
            )
            return {"status": "error", "reason": "Missing PR details"}
        
        # Split the remaining text into URL and title
        content = parts[1].strip()
        content_parts = content.split(' ', 1)
        
        if len(content_parts) < 2:
            client.chat_postMessage(
                channel=channel,
                text="Please use the format: @Bot URL Title"
            )
            return {"status": "error", "reason": "Invalid format"}
            
        url = content_parts[0]
        title = content_parts[1]
        
        # Get user info of the requester
        user_info = client.users_info(user=user_id)
        requester_name = "Unknown User"
        if user_info['ok']:
            requester_name = user_info['user'].get('real_name', user_info['user'].get('name', 'Unknown User'))
        
        # Select reviewers - pass the author's user_id to exclude them from selection
        reviewers = select_reviewers(user_id)
        
        # Primary reviewer is always the first one (Nigel)
        primary_reviewer = reviewers[0]
        additional_reviewers = reviewers[1:]
        
        # Construct the message
        message = (
            f"*New PR Needs Review:* {title}\n"
            f"*Repository:* Manual Request\n"
            f"*Author:* {requester_name}\n"
            f"*URL:* {url}\n\n"
            f"*Primary Reviewer:* <@{primary_reviewer[1]}>\n"
            f"*Additional Reviewers (one needed):* " + 
            " or ".join([f"<@{user_id}>" for _, user_id in additional_reviewers]) + "\n\n"
            f"React with :{CLAIM_EMOJI}: to claim this review."
        )
        
        # Send the message
        response = client.chat_postMessage(
            channel=channel,
            text=message
        )
        
        if response['ok']:
            return {"status": "success", "message": "PR review request created"}
        else:
            return {"status": "error", "reason": "Failed to send message"}
            
    except Exception as e:
        logger.error(f"Error processing mention: {str(e)}")
        return {"status": "error", "reason": str(e)}

# Remove the Flask app instantiation and keep only the route handler functions
def handle_pr_slash_command():
    """This is just a placeholder function that redirects to the main slash command handler"""
    from slash_commands import handle_slash_command
    return handle_slash_command()

def slack_events():
    """Handle Slack events including reactions"""
    # First, print the raw request data for debugging
    logger.info(f"Raw request data: {request.data}")
    
    try:
        # Try to parse the request body as JSON
        if request.data:
            try:
                payload = json.loads(request.data.decode('utf-8'))
                logger.info(f"Received event payload: {payload}")
                
                # Handle URL verification challenge
                if payload.get('type') == 'url_verification':
                    challenge = payload.get('challenge')
                    logger.info(f"Received URL verification challenge: {challenge}")
                    
                    # Return the exact challenge value in the expected format
                    # This is critical for Slack API validation
                    return {"challenge": challenge}
                
                # Handle reaction events
                event = payload.get('event', {})
                if event.get('type') == 'reaction_added':
                    logger.info(f"Processing reaction event: {event}")
                    handle_reaction(event)
                
                # Always return a 200 OK for events
                return jsonify({"status": "ok"})
            except json.JSONDecodeError as e:
                logger.error(f"Failed to parse JSON: {e}")
                return jsonify({"error": f"Invalid JSON: {str(e)}"}), 400
        else:
            logger.error("No data received in request")
            return jsonify({"error": "No data received"})
    
    except Exception as e:
        logger.error(f"Error processing event: {str(e)}", exc_info=True)
        return jsonify({"error": str(e)}), 500

def handle_reaction(event):
    """Handle the reaction event"""
    reaction = event.get('reaction')
    
    # Check if this is the claim emoji
    if reaction == CLAIM_EMOJI:
        user_id = event.get('user')
        item = event.get('item', {})
        channel = item.get('channel')
        ts = item.get('ts')
        
        if not (channel and ts and user_id):
            logger.error("Missing required reaction event data")
            return
        
        try:
            # Get the message that was reacted to
            message_response = client.conversations_history(
                channel=channel,
                inclusive=True,
                oldest=ts,
                latest=ts,
                limit=1
            )
            
            if not message_response['ok'] or not message_response['messages']:
                logger.error("Failed to fetch message or no messages found")
                return
            
            message = message_response['messages'][0]
            
            # Check if this is a PR review message (contains the claim emoji message)
            if "React with :" + CLAIM_EMOJI + ": to claim this review." in message.get('text', ''):
                # Update the message to show this person is reviewing
                updated_text = message['text'].split("*Primary Reviewer:*")[0]
                updated_text += f"*PR is being reviewed by:* <@{user_id}>\n\n"
                updated_text += "This PR review has been claimed."
                
                client.chat_update(
                    channel=channel,
                    ts=ts,
                    text=updated_text
                )
                logger.info(f"Updated PR review message with reviewer: <@{user_id}>")
                
                # Add a follow-up message to indicate who claimed it
                client.chat_postMessage(
                    channel=channel,
                    thread_ts=ts,
                    text=f"<@{user_id}> has claimed this PR review!"
                )
        
        except SlackApiError as e:
            logger.error(f"Error handling reaction: {e}")

# If this file is run directly
if __name__ == "__main__":
    print("This module is meant to be imported, not executed directly.")