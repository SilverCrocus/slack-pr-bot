import os
from flask import Flask
from werkzeug.middleware.dispatcher import DispatcherMiddleware
from pr_review_bot import app as pr_app
from reaction_handler import app as reaction_app
from slash_commands import app as slash_app

# Create a dispatcher that routes to each app based on path
application = DispatcherMiddleware(Flask(__name__), {
    '/webhook': pr_app,
    '/slack/events': reaction_app,
    '/slack/commands': slash_app
})

# This app object is used by the PythonAnywhere WSGI server
app = Flask(__name__)
app.wsgi_app = application

# For local development only
if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port, debug=True)
