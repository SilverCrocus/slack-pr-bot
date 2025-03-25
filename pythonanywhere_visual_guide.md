# Visual Guide to PythonAnywhere Environment Variables Setup

## Step 1: Access Web Tab
From your PythonAnywhere dashboard, click on the "Web" tab in the top navigation menu.

```
[Dashboard] [Consoles] [Files] [Web] [Tasks] [Databases]
                                 ^^^^
                              Click here
```

## Step 2: Locate Your Web App
Scroll down to find your web application. It should look something like this:

```
+---------------------------------------------------------+
| Web app: yourusername.pythonanywhere.com                |
|                                                         |
| • Configuration for yourusername.pythonanywhere.com     |
| • Reload yourusername.pythonanywhere.com                |
+---------------------------------------------------------+
```

## Step 3: Find Environment Variables Section
Continue scrolling down the configuration page. The Environment Variables section is usually past these sections:

1. Code section
2. Virtualenv section
3. Static files section

You're looking for a section that looks like this:

```
+---------------------------------------------------------+
| Environment variables                                   |
|                                                         |
| These will be available to your WSGI application.       |
|                                                         |
| Name [_________________] Value [_________________] [Add]|
+---------------------------------------------------------+
```

## Step 4: Add Your Variables
Click "Add" and fill in each variable:

```
+---------------------------------------------------------+
| Environment variables                                   |
|                                                         |
| Name [SLACK_BOT_TOKEN____] Value [xoxb-your-token] [Add]|
|                                                         |
| Name [PR_REVIEW_CHANNEL__] Value [pr-reviews_____] [Add]|
+---------------------------------------------------------+
```

## Step 5: Save Changes
After adding all variables, scroll to the bottom of the page and click "Save":

```
+---------------------------------------------------------+
|                       [Save]                            |
+---------------------------------------------------------+
```

## Step 6: Alternative Method (Using WSGI File)
If you can't find the Environment Variables section, click on the WSGI configuration file link in the Code section. 

Add these lines to your WSGI file, before importing your application:

```python
# Set environment variables
import os
os.environ['SLACK_BOT_TOKEN'] = 'xoxb-your-token-here'
os.environ['PR_REVIEW_CHANNEL'] = 'pr-reviews'

# Import your application
from app import app as application
```

Save the WSGI file, then go back to the Web tab and click "Reload" to apply your changes.
