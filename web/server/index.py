import os
import sys
import logging
from flask import Flask, render_template_string, send_from_directory, abort


# Suppress Flask/Werkzeug logging
logging.getLogger("werkzeug").setLevel(logging.ERROR)
log = logging.getLogger("werkzeug")
log.setLevel(logging.ERROR)

# Set up logging for Flask
logger = logging.getLogger("index")


app = Flask(__name__)

sansegrol_path = os.environ.get("Sansegrol")

if not sansegrol_path:
    logger.error("Sansegrol environment variable not set")
    sys.exit(1)

HTML_DIR = os.path.join(sansegrol_path, "web", "html")
CSS_DIR = os.path.join(sansegrol_path, "web", "css")
JS_DIR = os.path.join(sansegrol_path, "web", "js")

@app.route("/")
def index():
    return send_from_directory(HTML_DIR, "index.html")

@app.route("/<path:filename>.html")
def html_page(filename):
    if ".." in filename or filename.startswith("/"):
        abort(404)
    return send_from_directory(HTML_DIR, filename + ".html")

@app.route("/css/<path:filename>")
def css_file(filename):
    if ".." in filename or filename.startswith("/"):
        abort(404)
    return send_from_directory(CSS_DIR, filename)

@app.route("/js/<path:filename>")
def js_file(filename):
    if ".." in filename or filename.startswith("/"):
        abort(404)
    return send_from_directory(JS_DIR, filename)
