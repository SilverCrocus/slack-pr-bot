# PythonAnywhere Setup Guide for Slack PR Bot

## 1. Sign Up for PythonAnywhere

If you don't already have an account, sign up at [PythonAnywhere](https://www.pythonanywhere.com/).

## 2. Upload Your Code

### Option 1: Using Git
1. Go to the "Consoles" tab and open a Bash console
2. Clone your repository:
   ```
   git clone https://github.com/yourusername/your-repo.git slack-pr-bot
   ```

### Option 2: Manually Upload Files
1. Go to the "Files" tab
2. Create a new directory called `slack-pr-bot`
3. Upload all your Python files to this directory

## 3. Set Up a Virtual Environment

1. Go to the "Consoles" tab and open a Bash console
2. Navigate to your project directory:
   ```
   cd slack-pr-bot
   ```
3. Create a virtual environment:
   ```
   python -m venv venv
   ```
4. Activate the virtual environment:
   ```
   source venv/bin/activate
   ```
5. Install dependencies:
   ```
   pip install -r requirements.txt
   ```

## 4. Configure Environment Variables

1. Go to the "Web" tab in the PythonAnywhere dashboard
   - Click on the "Web" menu item in the top navigation bar

2. Scroll down to find your web app configuration section
   - You should see your web app listed with its URL (e.g., yourusername.pythonanywhere.com)

3. Continue scrolling down to the "Environment variables" section
   - It's usually located after the "Static files" section
   - Look for a section with a heading "Environment variables"
   - If you can't find it, continue scrolling to the bottom of the page

4. Add your environment variables:
   - You'll see a form with two columns: "Name" and "Value"
   - For each variable, click "Add a new variable"
   - Add these variables:
     
     | Name | Value |
     |------|-------|
     | SLACK_BOT_TOKEN | xoxb-your-token-here |
     | PR_REVIEW_CHANNEL | pr-reviews |

5. After adding all variables, scroll to the bottom of the page and click the "Save" button
   - Your changes won't apply until you save and reload the web app

6. If you cannot find the Environment Variables section:
   - Some PythonAnywhere accounts (especially free tier) may not show this UI section
   - In that case, you'll need to add the variables directly to your WSGI file:

   ```python
   # In your WSGI file (accessible from the Web tab)
   import os
   
   # Set environment variables here
   os.environ['SLACK_BOT_TOKEN'] = 'xoxb-your-token-here'
   os.environ['PR_REVIEW_CHANNEL'] = 'pr-reviews'
   
   # Then import your application
   from app import app as application
   ```

## 5. Configure the Web App

1. Go to the "Web" tab
2. Click "Add a new web app"
3. Choose "Manual configuration"
4. Select your Python version (3.8 or higher recommended)
5. Set the path to your project directory (e.g., `/home/yourusername/slack-pr-bot`)

## 6. Configure the WSGI File

1. Scroll down to the "Code" section and click on the WSGI configuration file link
2. Delete all the existing content
3. Copy the content from your `pythonanywhere_wsgi.py` file (with your actual paths)
4. Save the file

## 7. Reload the Web App

1. Go back to the "Web" tab
2. Click the "Reload" button to restart your application

## 8. Set Up Slack to Use Your PythonAnywhere URL

Your application will now be available at `https://yourusername.pythonanywhere.com`

Configure your Slack app to use these URLs:
- Slash Commands URL: `https://yourusername.pythonanywhere.com/slack/commands`
- Events URL: `https://yourusername.pythonanywhere.com/slack/events`
- Webhook URL: `https://yourusername.pythonanywhere.com/webhook/pr`

## 9. Testing Your Setup

1. Try sending a slash command from Slack
2. Check the "Web" tab logs for any errors

## 10. Troubleshooting

- If you encounter any issues, check the error logs in the "Web" tab
- Make sure your environment variables are set correctly
- Ensure your Slack app is properly configured with the correct URLs
