"""
WSGI configuration file for PythonAnywhere
This is a sample configuration - you'll need to copy parts of this
to the WSGI file provided by PythonAnywhere.
"""

import sys
import os

# Add your project directory to the Python path
project_home = '/home/yourusername/slack-pr-bot'  # Replace with your actual PythonAnywhere path
if project_home not in sys.path:
    sys.path.insert(0, project_home)

# Set environment variables
os.environ['SLACK_BOT_TOKEN'] = 'your-slack-bot-token'  # Replace with your actual token
os.environ['PR_REVIEW_CHANNEL'] = 'pr-reviews'  # Replace with your actual channel name

# Import your Flask application
from app import app as application  # This imports the 'app' object from your app.py
