from flask import Blueprint, session, redirect, flash, url_for, request
import config
import logging
from utils import buildURL, httpSession
import jwt

# Logging and Blueprint setup
logger = logging.getLogger(__name__)
authBP = Blueprint('auth', __name__)

@authBP.route("/register")
def register():
    keycloakRegURL = f"{config.keycloakPublicURL}/realms/{config.keycloakRealm}/protocol/openid-connect/registrations"

    params = {
        "client_id": config.keycloakClientId,
        "redirect_uri": url_for('auth.registerCallback', _external=True),
        "response_type": "code",
        "scope": "openid profile email"
    }

    return redirect(buildURL(keycloakRegURL, params))


@authBP.route("/login")
def login():
    authURL = f"{config.keycloakPublicURL}/realms/{config.keycloakRealm}/protocol/openid-connect/auth"

    params = {
        "client_id": config.keycloakClientId,
        "redirect_uri": url_for('auth.loginCallback', _external=True),
        "response_type": "code",
        "scope": "openid profile email"
    }

    return redirect(buildURL(authURL, params))


@authBP.route('/registerCallback')
def registerCallback():
    code = request.args.get('code')

    if not code:
        return "Error: No authentication code received."

    return processOIDCCallback(code, "register")


@authBP.route('/loginCallback')
def loginCallback():
    code = request.args.get('code')

    if not code:
        return "Error: No authentication code received."

    return processOIDCCallback(code, "login")


def processOIDCCallback(code, action):
    tokenEndpoint = f"{config.keycloakInternalURL}/realms/{config.keycloakRealm}/protocol/openid-connect/token"
    payload = {
        'grant_type': 'authorization_code',
        'code': code,
        'redirect_uri': url_for(f"auth.{action}Callback", _external=True),
        'client_id': config.keycloakClientId,
        'client_secret': config.keycloakClientSecret
    }

    try:
        # TODO: Verify should not be false in the future
        response = httpSession.post(tokenEndpoint, data=payload, verify=False)
        # TODO: in the future, the issuer should be from the public URL
        tokenData = response.json()

        if 'access_token' in tokenData:
            userInfoEndpoint = f"{config.keycloakInternalURL}/realms/{config.keycloakRealm}/protocol/openid-connect/userinfo"
            userInfoResponse = httpSession.get(userInfoEndpoint, headers={'Authorization': f"Bearer {tokenData['access_token']}"}, verify=False)
            userInfo = userInfoResponse.json()
            decodedToken = jwt.decode(tokenData['access_token'], options={"verify_signature": False})

            session["userinfo"] = {
                'id_token': tokenData.get('id_token'),
                'access_token': tokenData.get('access_token'),
                'refresh_token': tokenData.get('refresh_token'),
                'preferred_username': userInfo.get('preferred_username'),
                'email': userInfo.get('email'),
                'roles': decodedToken.get('realm_access', {}).get('roles', []),
            }

            session.modified = True  # Force Flask to save session

            if action == "register":
                flash("You have successfully created your account! You can now browse the website", "success")
                return redirect(url_for('general.home'))
            else:
                flash("Logged in!", "success")
                return redirect(url_for('general.home'))

        else:
            logger.info("Error: No access_token received.")
            return "Authentication error."

    except Exception as e:
        logger.info(f"Exception during token exchange: {e}")
        return "Authentication error."


@authBP.route('/logout')
def logout():
    try:
        keycloakLogoutEndpoint = f"{config.keycloakPublicURL}/realms/{config.keycloakRealm}/protocol/openid-connect/logout"
        idToken = session.get("userinfo", {}).get("id_token", "")

        '''url_for("general.home", _external=True)'''  # TODO: disabled for localhost, otherwise it causes a bad redirect. In the future, use the correct url_for
        params = {
            "post_logout_redirect_uri": "https://localhost:8080/home"
        }

        # If the user has an ID token, include it in the logout request
        if idToken:
            params["id_token_hint"] = idToken

        session.clear()  # Clear Flask session data
        return redirect(buildURL(keycloakLogoutEndpoint, params))

        flash("You have successfully logged out!", "success")
        if config.debug:
            logger.info("Successful logout")

        return redirect(url_for('home'))

    except Exception as e:
        logger.error(f"Exception during logout: {e}")
        return "Error logging out. Please try again."