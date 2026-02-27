import os

# Web variables
listenPort = int(os.environ.get('WEB_INTERNAL_PORT', '8080'))
secretKey = os.environ.get('WEB_SECRET_KEY', '')
debug = int(os.environ.get('WEB_DEBUG', '0')) == 1

# Keycloak variables
keycloakRealm = os.environ.get('KEYCLOAK_REALM', '')
keycloakClientId = os.environ.get('KEYCLOAK_CLIENT_ID', '')
keycloakClientSecret = os.environ.get('KEYCLOAK_CLIENT_SECRET', '')
keycloakInternalURL = os.environ.get('KEYCLOAK_INTERNAL_URL', '')
keycloakPublicURL = os.environ.get('KEYCLOAK_PUBLIC_URL', '')

# Orion variables
orionURL = os.environ.get('ORION_URL', '')

# API REST variables
apiRestURL = os.environ.get('API_REST_URL', '')