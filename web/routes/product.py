from flask import Blueprint, render_template, session, flash, redirect, url_for, request
from utils import fillInData, httpSession, canRegisterProduct
from product_models import (
    getProductModel,
    FIXED_FIELD_LABELS,
    PRODUCT_MODELS,
    getModelChoices,
    getModelDynamicFields,
    getModelServiceFields,
    SERVICE_FIELD_LABELS,
    SERVICE_FIELD_UNITS,
    SERVICE_FIELD_DESCRIPTIONS,
    SERVICE_FIELD_TYPES,
    LIFECYCLE_FIELD_LABELS,
    getLifecycleDefaults,
)
import config
import forms
import logging
import requests
from datetime import date
from urllib.parse import quote

# Logging and Blueprint setup
logger = logging.getLogger(__name__)
productBP = Blueprint('product', __name__)


def isMissingValue(value):
    if value is None:
        return True
    if isinstance(value, str):
        return value.strip() == ""
    return False


def validateRequiredRegistrationFields(form, fieldNames):
    isValid = True
    for fieldName in fieldNames:
        field = getattr(form, fieldName, None)
        if not field:
            continue
        if isMissingValue(field.data):
            if "This field is required" not in field.errors:
                field.errors.append("This field is required")
            isValid = False
    return isValid


def getProductModelByName(modelName):
    for modelKey, modelConfig in PRODUCT_MODELS.items():
        if modelConfig.get("modelName") == modelName:
            return modelKey, modelConfig
    return None, None


def buildServiceFieldMetadata(serviceFieldKeys):
    metadata = []
    for fieldName in serviceFieldKeys:
        metadata.append({
            "key": fieldName,
            "label": SERVICE_FIELD_LABELS.get(fieldName, fieldName),
            "unit": SERVICE_FIELD_UNITS.get(fieldName, ""),
            "description": SERVICE_FIELD_DESCRIPTIONS.get(fieldName, ""),
            "inputType": SERVICE_FIELD_TYPES.get(fieldName, "text"),
        })
    return metadata


def buildAdditionalLifecycleFieldMetadata(lifecycleDefaults):
    excludedFields = {
        "status",
        "numberOfUses",
        "condition",
        "currentLocation",
        "lastMaintenanceDate",
        "lifecycleCarbonFootprint",
    }

    metadata = []
    for fieldName in lifecycleDefaults.keys():
        if fieldName in excludedFields:
            continue
        metadata.append({
            "key": fieldName,
            "label": LIFECYCLE_FIELD_LABELS.get(fieldName, fieldName),
        })

    return metadata


@productBP.route("/registerProduct", methods=['GET', 'POST'])
def registerProduct():
    """Step 1: Select a Product Model."""
    userinfo = session.get("userinfo", {})

    if not canRegisterProduct(userinfo, ['testRole1', 'admin']):
        flash('You must have permissions to access this function.', 'warning')
        return redirect(url_for('general.home'))

    form = forms.SelectModelForm()

    if form.validate_on_submit():
        modelKey = form.modelKey.data
        return redirect(url_for('product.registerProductInstance', modelKey=modelKey))

    return render_template(
        'select_model.html',
        title='Register product',
        form=form,
        userinfo=userinfo,
        productModels=PRODUCT_MODELS,
    )


@productBP.route("/registerProduct/<modelKey>", methods=['GET', 'POST'])
def registerProductInstance(modelKey):
    """Step 2: Fill in dynamic fields for the selected Product Model."""
    userinfo = session.get("userinfo", {})

    if not canRegisterProduct(userinfo, ['testRole1', 'admin']):
        flash('You must have permissions to access this function.', 'warning')
        return redirect(url_for('general.home'))

    productModel = getProductModel(modelKey)
    if not productModel:
        flash('Invalid product model selected.', 'danger')
        return redirect(url_for('product.registerProduct'))

    form = forms.RegisterProductForm()

    dynamicFieldKeys = getModelDynamicFields(modelKey)
    serviceFieldKeys = getModelServiceFields(modelKey)
    serviceFieldMetadata = buildServiceFieldMetadata(serviceFieldKeys)
    lifecycleDefaults = getLifecycleDefaults(modelKey)
    additionalLifecycleFields = buildAdditionalLifecycleFieldMetadata(lifecycleDefaults)

    hasReturnRatio = "returnRatio" in dynamicFieldKeys or productModel.get("hasReturnRatio", False)
    showCurrentLocation = "currentLocation" in dynamicFieldKeys
    showNumberOfUses = "numberOfUses" in lifecycleDefaults
    showLastMaintenanceDate = "lastMaintenanceDate" in lifecycleDefaults
    showLifecycleCarbonFootprint = (
        "lifecycleCarbonFootprint" in lifecycleDefaults
        or productModel.get("manufacturingCarbonFootprint") is not None
        or "manufacturingCarbonFootprint" in serviceFieldKeys
    )

    requiredDynamicFields = []
    if showCurrentLocation:
        requiredDynamicFields.append("currentLocation")
    if hasReturnRatio:
        requiredDynamicFields.append("returnRatio")
    requiredDynamicFields.extend(serviceFieldKeys)

    if form.validate_on_submit():
        if not validateRequiredRegistrationFields(form, requiredDynamicFields):
            flash('Please complete the required fields for this model.', 'warning')
        else:
            userEmail = (userinfo.get("email") or "").strip().lower()
            data = fillInData(form, productModel, modelKey=modelKey, userEmail=userEmail)
            orionURL = f"{config.orionURL}/ngsi-ld/v1/entities"
            headers = {
                "Content-Type": "application/ld+json"
            }

            try:
                response = httpSession.post(orionURL, json=data, headers=headers)
                if response.status_code in [201, 204]:
                    flash('Product successfully registered in the system.', 'success')
                    return redirect(url_for('general.home'))
                else:
                    flash(f'Error registering product in Orion-LD: {response.status_code} - {response.text}', 'danger')
            except requests.exceptions.RequestException as e:
                logger.error(f"Connection error to Orion-LD: {e}")
                flash(f'Connection error with Orion-LD: {str(e)}', 'danger')

    return render_template(
        'register_product.html',
        title=f'Register {productModel["modelName"]}',
        form=form,
        userinfo=userinfo,
        productModel=productModel,
        modelKey=modelKey,
        fixedFieldLabels=FIXED_FIELD_LABELS,
        hasReturnRatio=hasReturnRatio,
        showCurrentLocation=showCurrentLocation,
        showNumberOfUses=showNumberOfUses,
        showLastMaintenanceDate=showLastMaintenanceDate,
        serviceFieldMetadata=serviceFieldMetadata,
        lifecycleDefaults=lifecycleDefaults,
        additionalLifecycleFields=additionalLifecycleFields,
        showLifecycleCarbonFootprint=showLifecycleCarbonFootprint,
    )


@productBP.route("/search", methods=['GET', 'POST'])
def search():
    itemsSearch = None
    searchQuery = ""
    selectedModelKey = ""
    warningMsg = ""
    cleanupSummary = None

    userinfo = session.get("userinfo", {})
    modelChoices = getModelChoices()

    if request.method == 'POST':
        action = (request.form.get('action') or 'search').strip().lower()
        searchQuery = (request.form.get('search') or '').strip()
        selectedModelKey = (request.form.get('modelKey') or '').strip()

        if action == 'cleanup':
            cleanupSummary = cleanupLegacyEntities()
            if cleanupSummary["errors"] == 0:
                flash(
                    (
                        f"Legacy cleanup completed. "
                        f"Deleted {cleanupSummary['deleted_assets']} Asset entities and "
                        f"{cleanupSummary['deleted_invalid_products']} invalid Product entities."
                    ),
                    'success'
                )
            else:
                flash(
                    (
                        f"Cleanup completed with {cleanupSummary['errors']} errors. "
                        f"Deleted {cleanupSummary['deleted_assets']} Asset entities and "
                        f"{cleanupSummary['deleted_invalid_products']} invalid Product entities."
                    ),
                    'warning'
                )

        if selectedModelKey and not getProductModel(selectedModelKey):
            warningMsg = "You must select a valid Product Model"
            itemsSearch = []
        else:
            itemsSearch = searchProducts(selectedModelKey, searchQuery)
            if config.debug:
                logger.info(f"Products search: {itemsSearch}")
    else:
        itemsSearch = searchProducts(selectedModelKey, searchQuery)

    return render_template(
        'search.html',
        title='Search products',
        items_search=itemsSearch,
        search_query=searchQuery,
        selected_model_key=selectedModelKey,
        model_choices=modelChoices,
        warning_message=warningMsg,
        cleanup_summary=cleanupSummary,
        userinfo=userinfo
    )


@productBP.route("/product/<partNumber>")
def productDetail(partNumber):
    """View full product details."""
    userinfo = session.get("userinfo", {})
    product = fetchProductByPartNumber(partNumber)

    if not product:
        flash('Product not found.', 'warning')
        return redirect(url_for('product.search'))

    canEdit = False
    userEmail = (userinfo.get("email") or "").strip().lower()
    productOwner = (product.get("registeredBy") or "").strip().lower()
    if userEmail and productOwner and userEmail == productOwner:
        canEdit = True

    modelKey, modelConfig = getProductModelByName(product.get("modelName"))
    serviceFieldMetadata = buildServiceFieldMetadata(modelConfig.get("serviceFields", []) if modelConfig else [])
    lifecycleDefaults = getLifecycleDefaults(modelKey) if modelConfig else {}
    additionalLifecycleFields = buildAdditionalLifecycleFieldMetadata(lifecycleDefaults)
    additionalLifecycleFieldKeys = [field["key"] for field in additionalLifecycleFields]
    showLifecycleCarbonFootprint = not isMissingValue(product.get("lifecycleCarbonFootprint"))

    return render_template(
        'product_detail.html',
        title=f'Product #{partNumber}',
        product=product,
        userinfo=userinfo,
        canEdit=canEdit,
        fixedFieldLabels=FIXED_FIELD_LABELS,
        serviceFieldMetadata=serviceFieldMetadata,
        additionalLifecycleFields=additionalLifecycleFields,
        additionalLifecycleFieldKeys=additionalLifecycleFieldKeys,
        showLifecycleCarbonFootprint=showLifecycleCarbonFootprint,
    )


@productBP.route("/product/<partNumber>/edit", methods=['GET', 'POST'])
def editProduct(partNumber):
    """Edit lifecycle fields of a product (only by owner)."""
    userinfo = session.get("userinfo", {})

    if not userinfo:
        flash('You must be logged in to edit a product.', 'warning')
        return redirect(url_for('auth.login'))

    product = fetchProductByPartNumber(partNumber)
    if not product:
        flash('Product not found.', 'warning')
        return redirect(url_for('product.search'))

    userEmail = (userinfo.get("email") or "").strip().lower()
    productOwner = (product.get("registeredBy") or "").strip().lower()
    if not userEmail or not productOwner or userEmail != productOwner:
        flash('You can only edit products you registered.', 'danger')
        return redirect(url_for('product.productDetail', partNumber=partNumber))

    modelKey, modelConfig = getProductModelByName(product.get("modelName"))
    lifecycleDefaults = getLifecycleDefaults(modelKey) if modelConfig else {}
    showNumberOfUses = "numberOfUses" in lifecycleDefaults
    showLastMaintenanceDate = "lastMaintenanceDate" in lifecycleDefaults
    showLifecycleCarbonFootprint = (
        not isMissingValue(product.get("lifecycleCarbonFootprint"))
        or (modelConfig and modelConfig.get("manufacturingCarbonFootprint") is not None)
        or (modelConfig and "manufacturingCarbonFootprint" in modelConfig.get("serviceFields", []))
    )

    form = forms.EditProductForm()

    if form.validate_on_submit():
        if showNumberOfUses and isMissingValue(form.numberOfUses.data):
            if "This field is required" not in form.numberOfUses.errors:
                form.numberOfUses.errors.append("This field is required")
            flash('Please complete the required lifecycle fields for this model.', 'warning')
        else:
            updatePayload = buildEditPayload(
                form,
                includeNumberOfUses=showNumberOfUses,
                includeLastMaintenanceDate=showLastMaintenanceDate,
                includeLifecycleCarbonFootprint=showLifecycleCarbonFootprint,
            )
            entityId = product["id"]

            orionURL = f"{config.orionURL}/ngsi-ld/v1/entities/{quote(entityId, safe='')}/attrs"
            headers = {"Content-Type": "application/json"}

            try:
                response = httpSession.patch(orionURL, json=updatePayload, headers=headers, timeout=10)
                if response.status_code in [204, 207]:
                    flash('Product updated successfully.', 'success')
                    return redirect(url_for('product.productDetail', partNumber=partNumber))
                else:
                    flash(f'Error updating product: {response.status_code} - {response.text}', 'danger')
            except requests.exceptions.RequestException as e:
                logger.error(f"Connection error to Orion-LD: {e}")
                flash(f'Connection error with Orion-LD: {str(e)}', 'danger')

    elif request.method == 'GET':
        form.status.data = product.get("status", "manufactured")
        if showNumberOfUses:
            form.numberOfUses.data = product.get("numberOfUses", 0)
        form.condition.data = product.get("condition", "new")
        form.currentLocation.data = product.get("currentLocation", "")
        if showLastMaintenanceDate:
            lastMaintenance = product.get("lastMaintenanceDate")
            if lastMaintenance:
                try:
                    form.lastMaintenanceDate.data = date.fromisoformat(str(lastMaintenance))
                except (ValueError, TypeError):
                    pass
        if showLifecycleCarbonFootprint:
            form.lifecycleCarbonFootprint.data = product.get("lifecycleCarbonFootprint")

    return render_template(
        'edit_product.html',
        title=f'Edit Product #{partNumber}',
        form=form,
        product=product,
        userinfo=userinfo,
        fixedFieldLabels=FIXED_FIELD_LABELS,
        showNumberOfUses=showNumberOfUses,
        showLastMaintenanceDate=showLastMaintenanceDate,
        showLifecycleCarbonFootprint=showLifecycleCarbonFootprint,
    )


def fetchProductByPartNumber(partNumber):
    """Fetch a single product entity by part number from Orion-LD."""
    normalizedPartNumber = str(partNumber).strip()
    if not normalizedPartNumber:
        return None

    entityId = f"urn:ngsi-ld:Product:{normalizedPartNumber}"
    try:
        url = f"{config.orionURL}/ngsi-ld/v1/entities/{quote(entityId, safe='')}"
        response = httpSession.get(url, headers={"Accept": "application/ld+json"}, timeout=10)
        if response.status_code == 200:
            entity = response.json()
            if isValidProductEntity(entity):
                return normalizeOrionProduct(entity)
        return None
    except Exception as e:
        logger.error(f"Error fetching product {normalizedPartNumber}: {e}")
        return None


def buildEditPayload(
    form,
    includeNumberOfUses=True,
    includeLastMaintenanceDate=True,
    includeLifecycleCarbonFootprint=True,
):
    """Build NGSI-LD PATCH payload from edit form data."""
    payload = {
        "status": {"type": "Property", "value": form.status.data},
        "condition": {"type": "Property", "value": form.condition.data},
        "currentLocation": {"type": "Property", "value": form.currentLocation.data},
    }

    if includeNumberOfUses and not isMissingValue(form.numberOfUses.data):
        payload["numberOfUses"] = {"type": "Property", "value": form.numberOfUses.data}

    if includeLifecycleCarbonFootprint and not isMissingValue(form.lifecycleCarbonFootprint.data):
        payload["lifecycleCarbonFootprint"] = {
            "type": "Property",
            "value": form.lifecycleCarbonFootprint.data,
            "unitCode": "KGM",
        }

    if includeLastMaintenanceDate and form.lastMaintenanceDate.data:
        payload["lastMaintenanceDate"] = {"type": "Property", "value": form.lastMaintenanceDate.data.isoformat()}

    return payload


def extractPropertyValue(entity, propertyName):
    propertyData = entity.get(propertyName, "")
    if isinstance(propertyData, dict):
        return propertyData.get("value", "")
    return propertyData


def normalizeOrionProduct(entity):
    normalized = {
        "id": entity.get("id", ""),
        # Dynamic fields
        "partNumber": extractPropertyValue(entity, "partNumber"),
        "manufacturingDate": extractPropertyValue(entity, "manufacturingDate"),
        "returnRatio": extractPropertyValue(entity, "returnRatio"),
        # Lifecycle fields
        "status": extractPropertyValue(entity, "status"),
        "numberOfUses": extractPropertyValue(entity, "numberOfUses"),
        "condition": extractPropertyValue(entity, "condition"),
        "currentLocation": extractPropertyValue(entity, "currentLocation"),
        "lastMaintenanceDate": extractPropertyValue(entity, "lastMaintenanceDate"),
        "lifecycleCarbonFootprint": extractPropertyValue(entity, "lifecycleCarbonFootprint"),
        # Owner
        "registeredBy": extractPropertyValue(entity, "registeredBy"),
    }

    for lifecycleFieldName in LIFECYCLE_FIELD_LABELS.keys():
        normalized[lifecycleFieldName] = extractPropertyValue(entity, lifecycleFieldName)

    for fixedFieldName in FIXED_FIELD_LABELS.keys():
        normalized[fixedFieldName] = extractPropertyValue(entity, fixedFieldName)

    for serviceFieldName in SERVICE_FIELD_LABELS.keys():
        normalized[serviceFieldName] = extractPropertyValue(entity, serviceFieldName)

    return normalized


def fetchEntitiesByType(entityType):
    orionEntitiesURL = f"{config.orionURL}/ngsi-ld/v1/entities?type={quote(entityType)}&limit=1000"
    response = httpSession.get(orionEntitiesURL, headers={"Accept": "application/ld+json"}, timeout=10)
    response.raise_for_status()

    entities = response.json()
    if isinstance(entities, list):
        return entities
    return []


def isValidProductEntity(entity):
    if entity.get("type") != "Product":
        return False

    modelName = extractPropertyValue(entity, "modelName")
    modelKey, modelConfig = getProductModelByName(modelName)
    if not modelConfig:
        return False

    requiredFields = [
        "partNumber",
        "manufacturingDate",
    ]

    defaultRequiredFixedFields = [
        "modelName",
        "description",
        "usePurpose",
        "manufacturerName",
        "manufacturerAddress",
        "taricCode",
        "durabilityMinYears",
        "durabilityMaxYears",
        "repairability",
    ]

    requiredFields.extend(modelConfig.get("requiredFixedFields", defaultRequiredFixedFields))

    lifecycleRequiredDefaults = ["status", "condition", "currentLocation"]
    requiredFields.extend(lifecycleRequiredDefaults)

    lifecycleDefaults = getLifecycleDefaults(modelKey)
    if "numberOfUses" in lifecycleDefaults:
        requiredFields.append("numberOfUses")

    if modelConfig.get("manufacturingCarbonFootprint") is not None:
        requiredFields.append("manufacturingCarbonFootprint")

    requiredFields.extend(modelConfig.get("additionalFixedFields", []))

    if modelConfig.get("manufacturingCarbonFootprint") is not None or "lifecycleCarbonFootprint" in lifecycleDefaults:
        requiredFields.append("lifecycleCarbonFootprint")
    if "manufacturingCarbonFootprint" in modelConfig.get("serviceFields", []):
        requiredFields.append("lifecycleCarbonFootprint")

    for fieldName, fieldValue in lifecycleDefaults.items():
        if fieldValue is None:
            continue
        if fieldName not in requiredFields:
            requiredFields.append(fieldName)

    requiredFields.extend(modelConfig.get("serviceFields", []))

    if modelConfig.get("hasReturnRatio"):
        requiredFields.append("returnRatio")

    for fieldName in requiredFields:
        value = extractPropertyValue(entity, fieldName)
        if isMissingValue(value):
            return False

    return True


def searchProducts(modelKey, searchQuery):
    try:
        entities = fetchEntitiesByType("Product")
    except requests.exceptions.RequestException as e:
        logger.error(f"Error querying Orion-LD Products: {e}")
        return []
    except ValueError:
        logger.error("The Orion-LD Product response is not valid JSON.")
        return []

    selectedModelName = ""
    if modelKey:
        productModel = getProductModel(modelKey)
        selectedModelName = productModel["modelName"] if productModel else ""

    searchTerm = (searchQuery or "").strip().lower()
    products = []

    for entity in entities:
        if not isValidProductEntity(entity):
            continue

        item = normalizeOrionProduct(entity)

        if selectedModelName and item.get("modelName") != selectedModelName:
            continue

        if searchTerm:
            searchableFields = [
                str(item.get("partNumber", "")),
                str(item.get("currentLocation", "")),
                str(item.get("status", "")),
                str(item.get("condition", "")),
                str(item.get("manufacturerName", "")),
                str(item.get("description", "")),
            ]
            for serviceFieldName in SERVICE_FIELD_LABELS.keys():
                searchableFields.append(str(item.get(serviceFieldName, "")))

            haystack = " ".join(searchableFields).lower()
            if searchTerm not in haystack:
                continue

        products.append(item)

    def partNumberSortKey(item):
        value = str(item.get("partNumber", ""))
        if value.isdigit():
            return (0, int(value))
        return (1, value.lower())

    products.sort(key=partNumberSortKey)
    return products


def cleanupLegacyEntities():
    summary = {
        "deleted_assets": 0,
        "deleted_invalid_products": 0,
        "errors": 0,
    }

    try:
        legacyAssets = fetchEntitiesByType("Asset")
        for entity in legacyAssets:
            entityId = entity.get("id")
            if not entityId:
                continue

            deleteURL = f"{config.orionURL}/ngsi-ld/v1/entities/{quote(entityId, safe='')}"
            response = httpSession.delete(deleteURL, timeout=10)

            if response.status_code in [204, 404]:
                summary["deleted_assets"] += 1
            else:
                summary["errors"] += 1
                logger.warning(f"Failed deleting legacy Asset {entityId}: {response.status_code} - {response.text}")
    except requests.exceptions.RequestException as e:
        summary["errors"] += 1
        logger.error(f"Error cleaning legacy Asset entities: {e}")

    try:
        products = fetchEntitiesByType("Product")
        for entity in products:
            if isValidProductEntity(entity):
                continue

            entityId = entity.get("id")
            if not entityId:
                continue

            deleteURL = f"{config.orionURL}/ngsi-ld/v1/entities/{quote(entityId, safe='')}"
            response = httpSession.delete(deleteURL, timeout=10)

            if response.status_code in [204, 404]:
                summary["deleted_invalid_products"] += 1
            else:
                summary["errors"] += 1
                logger.warning(f"Failed deleting invalid Product {entityId}: {response.status_code} - {response.text}")
    except requests.exceptions.RequestException as e:
        summary["errors"] += 1
        logger.error(f"Error cleaning invalid Product entities: {e}")

    return summary