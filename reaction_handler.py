import os
import logging
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError
from flask import Flask, request, jsonify
from pr_review_bot import select_reviewers, CLAIM_EMOJI

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Slack configuration from environment variables
SLACK_BOT_TOKEN = os.environ.get("SLACK_BOT_TOKEN")
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
        
        # Select reviewers
        reviewers = select_reviewers()
        
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

# Flask app for handling Slack events
app = Flask(__name__)

@app.route('/slack/commands', methods=['POST'])
def handle_slash_command():
    """Handle /pr slash command for PR review assignments"""
    try:
        # Verify the request is from Slack
        # In production, you should verify the request signature using SLACK_SIGNING_SECRET
        
        # Get command data
        command = request.form.get('command')
        text = request.form.get('text', '')
        user_id = request.form.get('user_id')
        channel_id = request.form.get('channel_id')
        
        # Verify this is the /pr command
        if command != '/pr':
            return jsonify({"text": "Invalid command"})
            
        # Parse the command: /pr URL Title
        parts = text.strip().split(' ', 1)  # Split into URL and title
        if len(parts) < 2:
            return jsonify({
                "response_type": "ephemeral",
                "text": "Error: Please use the format `/pr URL Title`"
            })
            
        url = parts[0]
        title = parts[1]
        
        # Get user info of the requester
        user_info = client.users_info(user=user_id)
        requester_name = "Unknown User"
        if user_info['ok']:
            requester_name = user_info['user'].get('real_name', user_info['user'].get('name', 'Unknown User'))
        
        # Select reviewers
        reviewers = select_reviewers()
        
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
        
        # Send the message to the channel where command was issued
        response = client.chat_postMessage(
            channel=channel_id,
            text=message
        )
        
        if response['ok']:
            # Return an ephemeral response to the user that submitted the command
            return jsonify({
                "response_type": "ephemeral",
                "text": "PR review request created successfully!"
            })
        else:
            return jsonify({
                "response_type": "ephemeral",
                "text": "Failed to create PR review request."
            })
            
    except Exception as e:
        logger.error(f"Error processing slash command: {str(e)}")
        return jsonify({
            "response_type": "ephemeral",
            "text": f"Error: {str(e)}"
        })

@app.route('/slack/events', methods=['POST'])
def slack_events():
    """Handle Slack events"""
    data = request.json
    
    # Verify Slack URL challenge
    if data.get('type') == 'url_verification':
        return jsonify({"challenge": data.get('challenge')})
        
    # Handle events
    if data.get('type') == 'event_callback':
        event = data.get('event', {})
        
        # Handle reaction_added event
        if event.get('type') == 'reaction_added':
            result = handle_reaction(event)
            logger.info(f"Reaction handler result: {result}")
        
        # Handle bot mentions
        elif event.get('type') == 'app_mention':
            result = handle_mention(event)
            logger.info(f"Mention handler result: {result}")
            
        # Keep the text command handler as a fallback
        elif event.get('type') == 'message' and not event.get('subtype'):
            if event.get('text', '').startswith('-pr '):
                result = handle_pr_command(event)
                logger.info(f"PR command handler result: {result}")
            
    return jsonify({"status": "ok"})

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 5001)))
