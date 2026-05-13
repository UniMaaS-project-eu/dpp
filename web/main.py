import os
from flask import Flask
import config
import logging
import utils
from routes import registerBPs
from werkzeug.middleware.proxy_fix import ProxyFix

# Logging configuration
logging.basicConfig(format="%(filename)s:%(lineno)d - %(levelname)s - %(message)s")
logging.getLogger().setLevel(logging.INFO)

# Check for required configurations
if not config.listenPort:
    raise ValueError("The listen port of the application isn't configured in config.py")

if not config.secretKey:
    raise ValueError("The secret key isn't configured in config.py")

if not config.keycloakRealm:
    raise ValueError("The Keycloak realm isn't configured in config.py")

if not config.keycloakClientId:
    raise ValueError("The Keycloak client ID isn't configured in config.py")

if not config.keycloakClientSecret:
    raise ValueError("The Keycloak client secret isn't configured in config.py")

if not config.keycloakInternalURL:
    raise ValueError("The Keycloak internal URL isn't configured in config.py")

if not config.keycloakPublicURL:
    raise ValueError("The Keycloak public URL isn't configured in config.py")

if not config.orionURL:
    raise ValueError("The Orion URL isn't configured in config.py")

if not config.apiRestURL:
    raise ValueError("The REST API URL isn't configured in config.py")

# Flask configuration
app = Flask(__name__)
app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1, x_prefix=1)
app.config['SECRET_KEY'] = config.secretKey
app.config["SESSION_TYPE"] = "filesystem"  # Save sessions in the filesystem
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_USE_SIGNER"] = True
app.config["SESSION_FILE_DIR"] = "./flask_session"  # Directory to store session files
app.config["PREFERRED_URL_SCHEME"] = "https" if config.useSSL else "http"
app.jinja_env.globals.update(canRegisterProduct=utils.canRegisterProduct)

basedir = os.path.abspath(os.path.dirname(__file__))
sslContext = (
    os.path.join(basedir, "certs", "odins.crt"),
    os.path.join(basedir, "certs", "odins.key")
)

if __name__ == "__main__":
    registerBPs(app)
    
    # Setup Orion-LD subscriptions on startup
    logging.info("Starting Orion-LD subscription setup")
    utils.setupOrionSubscriptions()
    logging.info("Orion-LD subscription setup finished, starting Flask app")
    
    runArgs = {
        "host": "0.0.0.0",
        "port": config.listenPort,
        "debug": config.debug
    }

    if config.useSSL:
        runArgs["ssl_context"] = sslContext

    app.run(**runArgs)