# Product Model definitions
# Each model defines fixed fields and optional metadata for registration forms.

PRODUCT_MODELS = {
    "magnum_optimum": {
        "modelName": "Magnum optimum",
        "description": "Plastic returnable and foldable container",
        "usePurpose": "Transport raw materials and finished goods between manufacturing plants",
        "manufacturerName": "Schoeller Allibert GmbH",
        "manufacturerAddress": "Sacktannen 30, 19057 Schwerin, Germany",
        "taricCode": "39231090",
        "durabilityMinYears": 5,
        "durabilityMaxYears": 15,
        "repairability": "repairable_with_spare_parts",
        "manufacturingCarbonFootprint": 176.58,
        "hasReturnRatio": True,
    },
    "europallet": {
        "modelName": "Europallet",
        "description": "Wooden pallet with 1.2x1.08 meters",
        "usePurpose": "Transport raw materials and finished goods between manufacturing plants",
        "manufacturerName": "DS Smith Poland",
        "manufacturerAddress": "ul. Malików 150, 25-639 Kielce, Poland",
        "taricCode": "4415202000",
        "durabilityMinYears": "indefinitely",
        "durabilityMaxYears": "indefinitely",
        "repairability": "repairable",
        "manufacturingCarbonFootprint": 7.75,
        "hasReturnRatio": True,
    },
    "b_container": {
        "modelName": "B-container",
        "description": "Metal returnable and foldable container",
        "usePurpose": "Transport raw materials and finished goods between manufacturing plants",
        "manufacturerName": "STRUMET sp. z o.o.",
        "manufacturerAddress": "ul. Ks. Londzina 61, 43-246 Strumień, Poland",
        "taricCode": "7326901000",
        "durabilityMinYears": 5,
        "durabilityMaxYears": 15,
        "repairability": "repairable_with_spare_parts",
        "manufacturingCarbonFootprint": 427.9,
        "hasReturnRatio": True,
    },
    "catone_manual_warehouse_operations": {
        "modelName": "Manual Warehouse Operations",
        "description": "Inbound, storage, picking, shipping",
        "usePurpose": "Optimize warehouse manual activities",
        "manufacturerName": "Catone Logistica Srl",
        "manufacturerAddress": "Caserta (ITALIA)",
        "taricCode": "H52.10",
        "durabilityMinYears": 10,
        "durabilityMaxYears": 10,
        "repairability": "Service Reliability Index - 8/10",
        "dynamicFields": ["partNumber", "manufacturingDate"],
        "serviceFields": ["inboundLeadTime", "inventoryAccuracy", "pickingProductivity"],
        "lifecycleDefaults": {
            "status": "in-use",
            "numberOfUses": 0,
            "condition": "good",
            "currentLocation": "WH01",
            "lastMaintenanceDate": None,
        },
    },
    "catone_asrs_automated_storage_system": {
        "modelName": "ASRS Automated Storage System",
        "description": "High-density automated storage with shuttles",
        "usePurpose": "Increase efficiency and traceability",
        "manufacturerName": "Catone Logistica Srl",
        "manufacturerAddress": "Caserta (ITALIA)",
        "taricCode": "H52.10",
        "durabilityMinYears": 15,
        "durabilityMaxYears": 15,
        "repairability": "Automation Reliability Index - 9/10",
        "dynamicFields": ["partNumber", "manufacturingDate"],
        "serviceFields": ["craneCyclePerformance", "asrsUtilization", "mtbf"],
        "lifecycleDefaults": {
            "status": "in-use",
            "numberOfUses": 0,
            "condition": "good",
            "currentLocation": "ASRS01",
            "lastMaintenanceDate": "2026-01-15",
        },
    },
    "catone_transportation_yard_management": {
        "modelName": "Transportation & Yard Management",
        "description": "Truck access and yard optimization",
        "usePurpose": "Reduce waiting times and coordinate logistics",
        "manufacturerName": "Catone Logistica Srl",
        "manufacturerAddress": "Caserta (ITALIA)",
        "taricCode": "H49-H52",
        "durabilityMinYears": 10,
        "durabilityMaxYears": 10,
        "repairability": "Transport Operations Index - 8/10",
        "dynamicFields": ["partNumber", "manufacturingDate"],
        "serviceFields": ["truckDwellTime", "slotPunctuality", "yardCongestionIndex"],
        "lifecycleDefaults": {
            "status": "in-use",
            "numberOfUses": 0,
            "condition": "good",
            "currentLocation": "YARD01",
            "lastMaintenanceDate": None,
        },
    },
    "aegean_commercial_passenger_aircraft_single_aisle": {
        "modelName": "Commercial Passenger Aircraft - single aisle",
        "description": "Commercial aircraft for short/medium haul",
        "usePurpose": "Passenger air transport",
        "manufacturerName": "Restricted",
        "manufacturerAddress": "Restricted",
        "taricCode": "N/A",
        "durabilityMinYears": 25,
        "durabilityMaxYears": 30,
        "repairability": "Internal maintenance score",
        "maintenanceInstructionsURL": "Restricted internal portal",
        "endOfLifeInstructionsURL": "Restricted",
        "technicalDocumentationURL": "Restricted",
        "certificatesURL": "Restricted",
        "userManualURL": "Restricted",
        "documentOwner": "Aircraft OEM / Airline Operator",
        "confidentialityLevel": "restricted",
        "manufacturerId": "Restricted",
        "operatorName": "AEGEAN Airlines",
        "facilityIds": "Internal IDs",
        "facilityType": "service / maintenance",
        "dynamicFields": ["partNumber", "manufacturingDate"],
        "serviceFields": [
            "maintenanceProgramReference",
            "averageCheckInterval",
            "documentIssueDate",
            "revisionNumber",
            "paperSafetyInfo",
        ],
        "additionalFixedFields": [
            "maintenanceInstructionsURL",
            "endOfLifeInstructionsURL",
            "technicalDocumentationURL",
            "certificatesURL",
            "userManualURL",
            "documentOwner",
            "confidentialityLevel",
            "manufacturerId",
            "operatorName",
            "facilityIds",
            "facilityType",
        ],
        "lifecycleDefaults": {
            "status": "in-use",
            "numberOfUses": 0,
            "condition": "good",
            "currentLocation": "ATH Airport",
            "lastMaintenanceDate": None,
        },
    },
    "anv_precast_technical_stairs": {
        "modelName": "Precast Technical Stairs",
        "description": "Precast vertical communication element",
        "usePurpose": "Reduce construction time",
        "manufacturerName": "ANV / PIAP",
        "material": "3D printing concrete",
        "durabilityMinYears": 50,
        "durabilityMaxYears": 75,
        "repairability": 3,
        "dynamicFields": ["partNumber", "manufacturingDate"],
        "serviceFields": ["dimensions", "totalCost", "manufacturingCarbonFootprint"],
        "additionalFixedFields": ["material"],
        "requiredFixedFields": [
            "modelName",
            "description",
            "usePurpose",
            "manufacturerName",
            "durabilityMinYears",
            "durabilityMaxYears",
            "repairability",
            "material",
        ],
        "lifecycleExcludedFields": ["numberOfUses", "lastMaintenanceDate"],
        "lifecycleDefaults": {
            "status": "manufactured",
            "condition": "new",
            "currentLocation": "construction_site",
        },
    },
    "anv_foundation_footing": {
        "modelName": "Foundation (footing)",
        "description": "Wide-base reinforced concrete foundation component",
        "usePurpose": "Transfers and distributes structural loads to soil",
        "manufacturerName": "ANV / PIAP",
        "material": "Reinforced concrete",
        "durabilityMinYears": 50,
        "durabilityMaxYears": 75,
        "repairability": 3,
        "conformityStandards": "EN 196-1, EN 13412, ASTM C109, ASTM C469, ASTM C348",
        "dynamicFields": ["partNumber", "manufacturingDate"],
        "serviceFields": ["technicalDocumentationReference"],
        "additionalFixedFields": ["material", "conformityStandards"],
        "requiredFixedFields": [
            "modelName",
            "description",
            "usePurpose",
            "manufacturerName",
            "durabilityMinYears",
            "durabilityMaxYears",
            "repairability",
            "material",
            "conformityStandards",
        ],
        "lifecycleExcludedFields": ["numberOfUses"],
        "lifecycleDefaults": {
            "status": "manufactured",
            "condition": "new",
            "currentLocation": "construction_site",
            "installationDate": None,
            "lastMaintenanceDate": None,
            "endOfLifeStatus": None,
            "confidentialityLevel": "restricted",
        },
    },
    "anv_precast_parkour_elements": {
        "modelName": "Precast Parkour Elements",
        "description": "Durable outdoor training facility for free running, vaulting, climbing and balancing",
        "usePurpose": "Creates customizable playgrounds and training areas",
        "manufacturerName": "ANV / PIAP",
        "material": "3D printed concrete",
        "durabilityMinYears": 50,
        "durabilityMaxYears": 75,
        "repairability": 3,
        "customizationLevel": "High",
        "conformityStandards": "EN 196-1, EN 13412, ASTM C109, ASTM C469, ASTM C348",
        "dynamicFields": ["partNumber", "manufacturingDate"],
        "serviceFields": ["technicalDocumentationReference"],
        "additionalFixedFields": ["material", "customizationLevel", "conformityStandards"],
        "requiredFixedFields": [
            "modelName",
            "description",
            "usePurpose",
            "manufacturerName",
            "durabilityMinYears",
            "durabilityMaxYears",
            "repairability",
            "material",
            "customizationLevel",
            "conformityStandards",
        ],
        "lifecycleExcludedFields": ["numberOfUses"],
        "lifecycleDefaults": {
            "status": "manufactured",
            "condition": "new",
            "currentLocation": "construction_site",
            "installationDate": None,
            "lastMaintenanceDate": None,
            "endOfLifeStatus": None,
            "confidentialityLevel": "restricted",
        },
    },
}

# Dynamic fields used in registration.
DEFAULT_DYNAMIC_FIELDS = ["partNumber", "manufacturingDate", "currentLocation"]

# Service-specific field metadata.
SERVICE_FIELD_LABELS = {
    "inboundLeadTime": "Inbound Lead Time",
    "inventoryAccuracy": "Inventory Accuracy",
    "pickingProductivity": "Picking Productivity",
    "craneCyclePerformance": "Crane Cycle Performance",
    "asrsUtilization": "ASRS Utilization",
    "mtbf": "MTBF",
    "truckDwellTime": "Truck Dwell Time",
    "slotPunctuality": "Slot Punctuality",
    "yardCongestionIndex": "Yard Congestion Index",
    "maintenanceProgramReference": "Maintenance Program Reference",
    "averageCheckInterval": "Average Check Interval",
    "documentIssueDate": "Document Issue Date",
    "revisionNumber": "Revision Number",
    "paperSafetyInfo": "Paper Safety Information",
    "dimensions": "Dimensions",
    "totalCost": "Total Cost",
    "technicalDocumentationReference": "Technical Documentation Reference",
    "manufacturingCarbonFootprint": "Manufacturing Carbon Footprint",
}

SERVICE_FIELD_UNITS = {
    "inboundLeadTime": "minutes",
    "inventoryAccuracy": "%",
    "pickingProductivity": "lines/hour",
    "craneCyclePerformance": "cycles/h",
    "asrsUtilization": "%",
    "mtbf": "hours",
    "truckDwellTime": "minutes",
    "slotPunctuality": "%",
    "yardCongestionIndex": "%",
    "averageCheckInterval": "flight hours / cycles / days",
    "totalCost": "EUR",
    "manufacturingCarbonFootprint": "kgCO2",
}

SERVICE_FIELD_DESCRIPTIONS = {
    "inboundLeadTime": "Time from arrival to storage",
    "inventoryAccuracy": "Stock accuracy",
    "pickingProductivity": "Picking efficiency",
    "craneCyclePerformance": "Cycles per hour",
    "asrsUtilization": "Occupancy rate",
    "mtbf": "Mean time between failures",
    "truckDwellTime": "Truck time onsite",
    "slotPunctuality": "On-time slots",
    "yardCongestionIndex": "Yard occupancy ratio",
    "maintenanceProgramReference": "Maintenance program identifier",
    "averageCheckInterval": "Planned maintenance interval",
    "documentIssueDate": "Issue date of compliance and safety documentation",
    "revisionNumber": "Documentation revision number",
    "paperSafetyInfo": "Whether paper safety documentation is available",
    "dimensions": "Product dimensions (LxWxH in meters)",
    "totalCost": "Total production cost",
    "technicalDocumentationReference": "Individual technical documentation (text or URL)",
    "manufacturingCarbonFootprint": "Carbon footprint during manufacturing",
}

SERVICE_FIELD_TYPES = {
    "inboundLeadTime": "number",
    "inventoryAccuracy": "number",
    "pickingProductivity": "number",
    "craneCyclePerformance": "number",
    "asrsUtilization": "number",
    "mtbf": "number",
    "truckDwellTime": "number",
    "slotPunctuality": "number",
    "yardCongestionIndex": "number",
    "maintenanceProgramReference": "text",
    "averageCheckInterval": "number",
    "documentIssueDate": "date",
    "revisionNumber": "number",
    "paperSafetyInfo": "boolean",
    "dimensions": "text",
    "totalCost": "number",
    "technicalDocumentationReference": "text",
    "manufacturingCarbonFootprint": "number",
}

SERVICE_FIELD_UNIT_CODES = {
    "totalCost": "EUR",
    "manufacturingCarbonFootprint": "KGM",
}

# Fixed fields that are displayed to the user (read-only)
FIXED_FIELD_LABELS = {
    "modelName": "Product Model",
    "description": "Description",
    "usePurpose": "Use Purpose",
    "manufacturerName": "Manufacturer",
    "manufacturerAddress": "Manufacturer Address",
    "taricCode": "TARIC Code",
    "durabilityMinYears": "Min. Durability (years)",
    "durabilityMaxYears": "Max. Durability (years)",
    "repairability": "Repairability",
    "manufacturingCarbonFootprint": "Manufacturing Carbon Footprint (kgCO₂)",
    "maintenanceInstructionsURL": "Maintenance Instructions",
    "endOfLifeInstructionsURL": "End-of-life Instructions",
    "technicalDocumentationURL": "Technical Documentation",
    "certificatesURL": "Certificates",
    "userManualURL": "User Manual",
    "documentOwner": "Document Owner",
    "confidentialityLevel": "Confidentiality Level",
    "manufacturerId": "Manufacturer ID",
    "operatorName": "Operator Name",
    "facilityIds": "Facility IDs",
    "facilityType": "Facility Type",
    "material": "Material",
    "conformityStandards": "Conformity Standards",
    "customizationLevel": "Customization Level",
}

# Lifecycle field defaults (auto-initialized on registration)
LIFECYCLE_DEFAULTS = {
    "status": "manufactured",
    "numberOfUses": 0,
    "condition": "new",
    "lastMaintenanceDate": None,
}

LIFECYCLE_FIELD_LABELS = {
    "installationDate": "Installation Date",
    "endOfLifeStatus": "End-of-life Status",
    "confidentialityLevel": "Confidentiality Level",
}


def getProductModel(modelKey):
    """Return the product model dict for a given key, or None."""
    return PRODUCT_MODELS.get(modelKey)


def getModelChoices():
    """Return a list of (key, label) tuples for the model selector."""
    return [(key, model["modelName"]) for key, model in PRODUCT_MODELS.items()]


def getModelDynamicFields(modelKey):
    """Return dynamic registration field names for a model key."""
    model = getProductModel(modelKey) or {}

    if "dynamicFields" in model:
        return list(model["dynamicFields"])

    fields = list(DEFAULT_DYNAMIC_FIELDS)
    if model.get("hasReturnRatio"):
        fields.insert(2, "returnRatio")
    return fields


def getModelServiceFields(modelKey):
    """Return service-specific field names for a model key."""
    model = getProductModel(modelKey) or {}
    return list(model.get("serviceFields", []))


def getLifecycleDefaults(modelKey):
    """Return lifecycle defaults for a model by merging global and model-level defaults."""
    defaults = dict(LIFECYCLE_DEFAULTS)
    model = getProductModel(modelKey) or {}
    defaults.update(model.get("lifecycleDefaults", {}))

    for fieldName in model.get("lifecycleExcludedFields", []):
        defaults.pop(fieldName, None)

    manufacturingCF = model.get("manufacturingCarbonFootprint")
    if manufacturingCF is not None and "lifecycleCarbonFootprint" not in defaults:
        defaults["lifecycleCarbonFootprint"] = manufacturingCF

    return defaults
