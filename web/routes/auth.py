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
        if response.status_code != 200:
            logger.info(f"Token endpoint error ({response.status_code}): {response.text}")
            return "Authentication error."

        # TODO: in the future, the issuer should be from the public URL
        try:
            tokenData = response.json()
        except ValueError:
            logger.info(f"Invalid JSON from token endpoint ({response.status_code}): {response.text}")
            return "Authentication error."

        if 'access_token' in tokenData:
            userInfoEndpoint = f"{config.keycloakInternalURL}/realms/{config.keycloakRealm}/protocol/openid-connect/userinfo"
            userInfoResponse = httpSession.get(userInfoEndpoint, headers={'Authorization': f"Bearer {tokenData['access_token']}"}, verify=False)

            if userInfoResponse.status_code != 200:
                logger.info(f"Userinfo endpoint error ({userInfoResponse.status_code}): {userInfoResponse.text}")
                return "Authentication error."

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
            logger.info(f"Error: No access_token received. Response: {tokenData}")
            return "Authentication error."

    except Exception as e:
        logger.info(f"Exception during token exchange: {e}")
        return "Authentication error."


@authBP.route('/logout')
def logout():
    try:
        keycloakLogoutEndpoint = f"{config.keycloakPublicURL}/realms/{config.keycloakRealm}/protocol/openid-connect/logout"
        idToken = session.get("userinfo", {}).get("id_token", "")
        postLogoutRedirectURI = f"{request.url_root.rstrip('/')}{url_for('general.home')}"

        params = {
            "post_logout_redirect_uri": postLogoutRedirectURI
        }

        # If the user has an ID token, include it in the logout request
        if idToken:
            params["id_token_hint"] = idToken

        session.clear()  # Clear Flask session data
        return redirect(buildURL(keycloakLogoutEndpoint, params))

    except Exception as e:
        logger.error(f"Exception during logout: {e}")
        return "Error logging out. Please try again."