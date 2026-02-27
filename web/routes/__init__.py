from .auth import authBP
from .general import generalBP
from .product import productBP
import config
import logging

logger = logging.getLogger(__name__)

def registerBPs(app):
    """Register all blueprints for the application."""
    app.register_blueprint(authBP)
    app.register_blueprint(generalBP)
    app.register_blueprint(productBP)

    if config.debug:
        logger.info("Blueprints registered successfully.")