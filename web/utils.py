import requests
import logging
import config
import time

# Get logger instance that will use the configuration from main.py
logger = logging.getLogger(__name__)

# Global session for HTTP requests
httpSession = requests.Session()

def buildURL(base, params):
    return f"{base}?{'&'.join([f'{key}={value}' for key, value in params.items()])}"

def fillInData(form):
    """
    Build NGSI-LD payload from the form data.
    """

    data = {
        "@context": [
            "https://uri.etsi.org/ngsi-ld/v1/ngsi-ld-core-context.jsonld"
        ],
        "id": f"urn:ngsi-ld:Asset:{form.productID.data}",  # El ID debe ser una URI válida
        "type": "Asset",
        "opType": {"type": "Property", "value": 1},
        "appraisedValue": {"type": "Property", "value": "1"},
        "color": {"type": "Property", "value": form.color.data},
        "manufacturer": {"type": "Property", "value": form.manufacturer.data},
        "material": {"type": "Property", "value": form.material.data},
        "model": {"type": "Property", "value": form.model.data},
        "productionDate": {"type": "Property", "value": form.productionDate.data},
        "recyclability": {"type": "Property", "value": form.recyclability.data},
        "serialNumber": {"type": "Property", "value": form.serialNumber.data},
        "size": {"type": "Property", "value": form.size.data},
        "weight": {"type": "Property", "value": form.weight.data}
    }
    return data

def canRegisterProduct(userinfo, rolesToCheck):
    userRoles = userinfo.get("roles", [])
    return any(role in userRoles for role in rolesToCheck)

def createSubscription(subscriptionData):
    """
    Create a single subscription in Orion-LD.
    """
    try:
        url = f"{config.orionURL}/ngsi-ld/v1/subscriptions/"
        headers = {'Content-Type': 'application/ld+json'}
        
        subscriptionId = subscriptionData.get('id', 'Unknown')
        response = httpSession.post(url, json=subscriptionData, headers=headers)
        
        if response.status_code == 201:
            logger.info(f"Created subscription: {subscriptionId}")
            return True
        else:
            logger.error(f"Failed to create subscription {subscriptionId}: {response.status_code}")
            return False
            
    except Exception as e:
        logger.error(f"Error creating subscription: {e}")
        return False

def setupOrionSubscriptions():
    """
    Check and create required Orion-LD subscriptions if they don't exist.
    """
    logger.info("Setting up Orion-LD subscriptions")
    
    # Test connection to Orion with retries
    maxRetries = 3
    for attempt in range(1, maxRetries + 1):
        try:
            testUrl = f"{config.orionURL}/version"
            response = httpSession.get(testUrl, timeout=5)
            
            if response.status_code == 200:
                logger.info(f"Connected to Orion-LD on attempt {attempt}")
                break
            else:
                logger.warning(f"Orion-LD connection attempt {attempt} failed: {response.status_code}")
                
        except Exception as e:
            logger.warning(f"Orion-LD connection attempt {attempt} failed: {e}")
            
        if attempt < maxRetries:
            logger.info(f"Waiting 3 seconds before retry...")
            time.sleep(3)
        else:
            logger.error("Cannot connect to Orion-LD after 3 attempts")
            return
    
    # Define our target subscriptions
    subscriptionsToCreate = []
    
    # Subscription 1: Asset-Blockchain (opType==1)
    subscription1Data = {
        "id": "urn:ngsi-ld:Subscription:Asset-Blockchain",
        "type": "Subscription",
        "description": "Notification to register asset on Blockchain when opType==1",
        "entities": [{"type": "Asset"}],
        "q": "opType==1",
        "status": "active",
        "isActive": True,
        "notification": {
            "format": "normalized",
            "endpoint": {
                "uri": f"{config.apiRestURL}/unimaas/create",
                "accept": "application/json"
            },
            "status": "ok"
        },
        "expiresAt": "2040-01-01T14:00:00.000Z",
        "throttling": 5,
        "@context": "https://uri.etsi.org/ngsi-ld/v1/ngsi-ld-core-context-v1.8.jsonld"
    }
    
    # Subscription 2: Asset-Update (opType==2)
    subscription2Data = {
        "id": "urn:ngsi-ld:Subscription:Asset-Update",
        "type": "Subscription",
        "description": "Notification to update asset on Blockchain when opType==2",
        "entities": [{"type": "Asset"}],
        "watchedAttributes": [
            "appraisedValue", "color", "manufacturer", "material", "model",
            "production_date", "recyclability", "serial_number", "size", "weight"
        ],
        "q": "opType==2",
        "status": "active",
        "isActive": True,
        "notification": {
            "format": "normalized",
            "endpoint": {
                "uri": f"{config.apiRestURL}/unimaas/update",
                "accept": "application/json"
            },
            "status": "ok"
        },
        "expiresAt": "2040-01-01T14:00:00.000Z",
        "throttling": 5,
        "@context": "https://uri.etsi.org/ngsi-ld/v1/ngsi-ld-core-context-v1.8.jsonld"
    }
    
    targetSubscriptions = [subscription1Data, subscription2Data]
    
    # Check which subscriptions need to be created
    for subscriptionData in targetSubscriptions:
        subscriptionId = subscriptionData['id']
        
        try:
            checkUrl = f"{config.orionURL}/ngsi-ld/v1/subscriptions/{subscriptionId}"
            response = httpSession.get(checkUrl)

            if response.status_code == 200:
                logger.info(f"Subscription {subscriptionId} exists")
            elif response.status_code == 404:
                subscriptionsToCreate.append(subscriptionData)
                
        except Exception as e:
            logger.error(f"Error checking {subscriptionId}: {e}")
    
    # Create missing subscriptions
    if subscriptionsToCreate:
        logger.info(f"Creating {len(subscriptionsToCreate)} missing subscriptions")
        
        for subscriptionData in subscriptionsToCreate:
            success = createSubscription(subscriptionData)
            if not success:
                logger.error("Failed to create subscription - stopping setup")
                return
                
    logger.info("Orion-LD subscription setup completed")