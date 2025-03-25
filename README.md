# PR Review Bot for Slack

A Slack bot that automates PR review assignments for a team.

## Features

- Automatically assigns PR reviews to a primary reviewer (Nigel) and two additional team members
- Monitors emoji reactions to track when a review has been claimed
- Notifies all relevant parties about PR status changes
- Ensures fair rotation among team members for review assignments

## Setup Instructions

1. **Environment Variables**:
   - Copy `.env.example` to `.env` and fill in your Slack credentials:
   ```
   cp .env.example .env
   ```

2. **Install Dependencies**:
   ```
   pip install -r requirements.txt
   ```

3. **Slack App Configuration**:
   - Create a Slack app at https://api.slack.com/apps
   - Add the following Bot Token Scopes:
     - `chat:write`
     - `chat:write.public`
     - `reactions:read`
     - `users:read`
     - `channels:history`
     - `im:write`
   - Install the app to your workspace
   - Copy the Bot User OAuth Token to your `.env` file
   - Configure Event Subscriptions for:
     - `reaction_added`
   - Set the Request URL to your server's `/slack/events` endpoint

4. **Update Team Configuration**:
   - Edit the `TEAM_MEMBERS` dictionary in `pr_review_bot.py` with the actual Slack User IDs for your team

5. **Running the Bot**:
   ```
   python pr_review_bot.py
   ```

## Usage

### Webhook Integration

Set up your Git platform (GitHub, GitLab, etc.) to send webhook events to:
```
https://your-server-url/webhook/pr
```

### Manual PR Notification

For testing or manual notification:
```python
from pr_review_bot import notify_pr_review

pr_data = {
    'title': 'Example PR',
    'repository': 'owner/repo',
    'author': 'username',
    'url': 'https://github.com/owner/repo/pull/123'
}

notify_pr_review(pr_data)
```

### Claiming a Review

- When a PR review notification appears in the channel, team members can claim the review by reacting with the ✅ emoji
- The bot will update the message to indicate who claimed the review
- Nigel will be notified via DM when a review has been claimed

## Project Structure

- `pr_review_bot.py`: Main application logic and PR notification functionality
- `reaction_handler.py`: Processes Slack reaction events for review claiming
- `.env`: Environment variables (not checked into version control)
- `requirements.txt`: Python dependencies

## Customization

- Change the `CLAIM_EMOJI` variable to use a different emoji for claiming reviews
- Adjust the message format in `notify_pr_review()` function
- Modify the reviewer selection logic in `select_reviewers()` function
