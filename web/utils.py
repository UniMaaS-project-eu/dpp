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


def toSerializableValue(value):
    if hasattr(value, "isoformat"):
        return value.isoformat()
    return value

def fillInData(form, productModel, modelKey=None, userEmail=None):
    """
    Build NGSI-LD payload from the form data and product model.
    Combines fixed fields (from model), dynamic fields (from form), and lifecycle defaults.
    """
    from product_models import (
        getLifecycleDefaults,
        getModelDynamicFields,
        getModelServiceFields,
        SERVICE_FIELD_UNIT_CODES,
    )

    partNumber = str(form.partNumber.data).strip()
    lifecycleDefaults = getLifecycleDefaults(modelKey)
    dynamicFields = getModelDynamicFields(modelKey) if modelKey else []
    serviceFields = getModelServiceFields(modelKey) if modelKey else []

    data = {
        "@context": [
            "https://uri.etsi.org/ngsi-ld/v1/ngsi-ld-core-context.jsonld"
        ],
        "id": f"urn:ngsi-ld:Product:{partNumber}",
        "type": "Product",

        # Dynamic fields from form
        "partNumber": {"type": "Property", "value": partNumber},
        "manufacturingDate": {"type": "Property", "value": toSerializableValue(form.manufacturingDate.data)},

        # Lifecycle fields (auto-initialized)
        "status": {"type": "Property", "value": toSerializableValue(lifecycleDefaults["status"])},
        "condition": {"type": "Property", "value": toSerializableValue(lifecycleDefaults["condition"])},
    }

    if "numberOfUses" in lifecycleDefaults:
        data["numberOfUses"] = {
            "type": "Property",
            "value": toSerializableValue(lifecycleDefaults["numberOfUses"]),
        }

    modelMetadataKeys = {
        "dynamicFields",
        "serviceFields",
        "lifecycleDefaults",
        "hasReturnRatio",
        "additionalFixedFields",
        "requiredFixedFields",
        "lifecycleExcludedFields",
    }

    for fieldName, fieldValue in productModel.items():
        if fieldName in modelMetadataKeys:
            continue
        if fieldValue is None:
            continue

        payload = {"type": "Property", "value": toSerializableValue(fieldValue)}
        if fieldName == "manufacturingCarbonFootprint":
            payload["unitCode"] = "KGM"

        data[fieldName] = payload

    currentLocation = None
    if "currentLocation" in dynamicFields:
        currentLocation = form.currentLocation.data
    elif lifecycleDefaults.get("currentLocation") is not None:
        currentLocation = lifecycleDefaults.get("currentLocation")

    if currentLocation not in [None, ""]:
        data["currentLocation"] = {"type": "Property", "value": toSerializableValue(currentLocation)}

    lifecycleCF = lifecycleDefaults.get("lifecycleCarbonFootprint")
    if lifecycleCF is None:
        lifecycleCF = productModel.get("manufacturingCarbonFootprint")
    if lifecycleCF is None and "manufacturingCarbonFootprint" in serviceFields:
        lifecycleCF = form.manufacturingCarbonFootprint.data
    if lifecycleCF is not None:
        data["lifecycleCarbonFootprint"] = {
            "type": "Property",
            "value": toSerializableValue(lifecycleCF),
            "unitCode": "KGM",
        }

    lastMaintenanceDate = lifecycleDefaults.get("lastMaintenanceDate")
    if lastMaintenanceDate is not None:
        formattedLastMaintenance = toSerializableValue(lastMaintenanceDate)
        data["lastMaintenanceDate"] = {"type": "Property", "value": formattedLastMaintenance}

    for fieldName, fieldValue in lifecycleDefaults.items():
        if fieldName in data:
            continue
        if fieldValue is None:
            continue
        data[fieldName] = {"type": "Property", "value": toSerializableValue(fieldValue)}

    # returnRatio only applies to models that have it (not Europallet)
    if productModel.get("hasReturnRatio") and form.returnRatio.data is not None:
        data["returnRatio"] = {"type": "Property", "value": form.returnRatio.data}

    for fieldName in serviceFields:
        field = getattr(form, fieldName, None)
        if not field:
            continue
        if field.data in [None, ""]:
            continue
        payload = {"type": "Property", "value": toSerializableValue(field.data)}
        unitCode = SERVICE_FIELD_UNIT_CODES.get(fieldName)
        if unitCode:
            payload["unitCode"] = unitCode
        data[fieldName] = payload

    # Track who registered the product
    if userEmail:
        data["registeredBy"] = {"type": "Property", "value": userEmail}

    return data

def canRegisterProduct(userinfo, rolesToCheck):
    userRoles = userinfo.get("roles", [])
    userEmail = (userinfo.get("email") or "").strip().lower()
    return any(role in userRoles for role in rolesToCheck) or userEmail == "demo@test.com"

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
    
    # Subscription 1: Product-Blockchain (opType==1)
    subscription1Data = {
        "id": "urn:ngsi-ld:Subscription:Product-Blockchain",
        "type": "Subscription",
        "description": "Notification to register product on Blockchain when opType==1",
        "entities": [{"type": "Product"}],
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
    
    # Subscription 2: Product-Update (opType==2)
    subscription2Data = {
        "id": "urn:ngsi-ld:Subscription:Product-Update",
        "type": "Subscription",
        "description": "Notification to update product on Blockchain when opType==2",
        "entities": [{"type": "Product"}],
        "watchedAttributes": [
            "status", "numberOfUses", "condition", "currentLocation",
            "lastMaintenanceDate", "lifecycleCarbonFootprint"
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