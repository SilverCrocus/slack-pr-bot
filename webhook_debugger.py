import os
import sys
import json
import logging
from dotenv import load_dotenv
from pr_review_bot import notify_pr_review

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def simulate_webhook(event_type='pull_request', action='opened'):
    """
    Simulate a GitHub webhook event and process it locally to test the notification system
    """
    # Construct a sample webhook payload for the given event type
    if event_type == 'pull_request':
        payload = {
            "action": action,
            "pull_request": {
                "html_url": "https://github.com/test-org/test-repo/pull/1",
                "user": {
                    "login": "test-user"
                },
                "title": "Test pull request"
            },
            "repository": {
                "full_name": "test-org/test-repo",
                "html_url": "https://github.com/test-org/test-repo"
            }
        }
    else:
        payload = {
            "action": action,
            "repository": {
                "full_name": "test-org/test-repo",
                "html_url": "https://github.com/test-org/test-repo"
            }
        }
    
    logger.info(f"Simulating {event_type} webhook with action {action}")
    logger.info(f"Payload: {json.dumps(payload)}")
    
    # Construct PR data from payload
    try:
        # Extract data similarly to the webhook function
        if event_type == 'pull_request':
            pr_data = {
                'title': payload.get('repository', {}).get('full_name', 'Unknown repository'),
                'repository': payload.get('repository', {}).get('full_name', 'Unknown repository'),
                'author': f"<@{payload.get('pull_request', {}).get('user', {}).get('login', 'Unknown')}>",
                'url': payload.get('pull_request', {}).get('html_url', '#')
            }
        else:
            pr_data = {
                'title': f"GitHub {event_type} event in " + 
                        payload.get('repository', {}).get('full_name', 'Unknown repository'),
                'repository': payload.get('repository', {}).get('full_name', 'Unknown repository'),
                'author': 'GitHub Webhook',
                'url': payload.get('repository', {}).get('html_url', '#')
            }
        
        logger.info(f"Processed data for notification: {pr_data}")
        
        # Send notification to Slack
        response = notify_pr_review(pr_data)
        
        if response and response.get('ok'):
            logger.info("✅ Successfully sent notification to Slack")
        else:
            logger.error(f"❌ Failed to send notification: {response}")
    
    except Exception as e:
        logger.error(f"❌ Error processing webhook data: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())

if __name__ == "__main__":
    # If command-line args provided, use them as event_type and action
    event_type = 'pull_request'
    action = 'opened'
    
    if len(sys.argv) > 1:
        event_type = sys.argv[1]
    if len(sys.argv) > 2:
        action = sys.argv[2]
    
    # Run the simulator
    simulate_webhook(event_type, action)
    logger.info("Done!")
