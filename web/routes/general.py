from flask import Blueprint, render_template, session
import config
import logging

# Logging and Blueprint setup
generalBP = Blueprint('general', __name__)
logger = logging.getLogger(__name__)

@generalBP.route("/")
@generalBP.route("/home")
def home():
    """Main page, shows the authenticated user."""
    userInfo = session.get("userinfo", {})
    if config.debug:
        logger.info(f"Complete session in index(): {session}")  # Complete debug

    return render_template('home.html', userinfo=userInfo)


@generalBP.route("/about")
def about():
    """About page, shows the authenticated user."""
    userInfo = session.get("userinfo", {})
    return render_template('about.html', title='About us', userinfo=userInfo)