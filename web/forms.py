from flask_wtf import FlaskForm
from wtforms import StringField, IntegerField, FloatField, SelectField, SubmitField, DateField, BooleanField
from wtforms.validators import DataRequired, NumberRange, Optional, Length, Regexp
from product_models import getModelChoices


class SelectModelForm(FlaskForm):
    """First step: select a Product Model."""
    modelKey = SelectField(
        "Select Product Model",
        choices=[],
        validators=[DataRequired(message="You must select a product model")]
    )
    submit = SubmitField('Continue')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.modelKey.choices = [("", "-- Select a model --")] + getModelChoices()


class RegisterProductForm(FlaskForm):
    """Second step: fill in the dynamic fields for a specific product instance."""

    # Dynamic fields (user input)
    partNumber = StringField(
        "Part Number",
        validators=[
            DataRequired(message="This field is required"),
            Length(max=64, message="Must be 64 characters or fewer"),
            Regexp(r"^[A-Za-z0-9_-]+$", message="Use letters, numbers, hyphens or underscores")
        ]
    )
    manufacturingDate = DateField(
        "Manufacturing Date",
        format='%Y-%m-%d',
        validators=[DataRequired(message="This field is required (YYYY-MM-DD)")]
    )
    returnRatio = IntegerField(
        "Return Ratio",
        validators=[
            Optional(),
            NumberRange(min=1, max=10, message="Must be between 1 and 10")
        ]
    )
    currentLocation = StringField(
        "Current Location",
        validators=[Optional(), Length(max=120, message="Must be 120 characters or fewer")]
    )

    # CATONE Product 1 - Manual Warehouse Operations
    inboundLeadTime = FloatField(
        "Inbound Lead Time (minutes)",
        validators=[Optional(), NumberRange(min=0, message="Must be 0 or greater")]
    )
    inventoryAccuracy = FloatField(
        "Inventory Accuracy (%)",
        validators=[Optional(), NumberRange(min=0, max=100, message="Must be between 0 and 100")]
    )
    pickingProductivity = FloatField(
        "Picking Productivity (lines/hour)",
        validators=[Optional(), NumberRange(min=0, message="Must be 0 or greater")]
    )

    # CATONE Product 2 - ASRS Automated Storage System
    craneCyclePerformance = FloatField(
        "Crane Cycle Performance (cycles/h)",
        validators=[Optional(), NumberRange(min=0, message="Must be 0 or greater")]
    )
    asrsUtilization = FloatField(
        "ASRS Utilization (%)",
        validators=[Optional(), NumberRange(min=0, max=100, message="Must be between 0 and 100")]
    )
    mtbf = FloatField(
        "MTBF (hours)",
        validators=[Optional(), NumberRange(min=0, message="Must be 0 or greater")]
    )

    # CATONE Product 3 - Transportation & Yard Management
    truckDwellTime = FloatField(
        "Truck Dwell Time (minutes)",
        validators=[Optional(), NumberRange(min=0, message="Must be 0 or greater")]
    )
    slotPunctuality = FloatField(
        "Slot Punctuality (%)",
        validators=[Optional(), NumberRange(min=0, max=100, message="Must be between 0 and 100")]
    )
    yardCongestionIndex = FloatField(
        "Yard Congestion Index (%)",
        validators=[Optional(), NumberRange(min=0, max=100, message="Must be between 0 and 100")]
    )

    # AEGEAN Product 1 - Commercial Passenger Aircraft (Single Aisle)
    maintenanceProgramReference = StringField(
        "Maintenance Program Reference",
        validators=[Optional(), Length(max=120, message="Must be 120 characters or fewer")]
    )
    averageCheckInterval = FloatField(
        "Average Check Interval",
        validators=[Optional(), NumberRange(min=0, message="Must be 0 or greater")]
    )
    documentIssueDate = DateField(
        "Document Issue Date",
        format='%Y-%m-%d',
        validators=[Optional()]
    )
    revisionNumber = IntegerField(
        "Revision Number",
        validators=[Optional(), NumberRange(min=1, message="Must be 1 or greater")]
    )
    paperSafetyInfo = BooleanField(
        "Paper Safety Information",
        default=True
    )

    # ANV Product 1 - Precast Technical Stairs
    dimensions = StringField(
        "Dimensions",
        validators=[Optional(), Length(max=120, message="Must be 120 characters or fewer")]
    )
    totalCost = FloatField(
        "Total Cost",
        validators=[Optional(), NumberRange(min=0, message="Must be 0 or greater")]
    )
    manufacturingCarbonFootprint = FloatField(
        "Manufacturing Carbon Footprint",
        validators=[Optional(), NumberRange(min=0, message="Must be 0 or greater")]
    )

    # ANV Product 2/3 - Foundation and Precast Parkour Elements
    technicalDocumentationReference = StringField(
        "Technical Documentation Reference",
        validators=[Optional(), Length(max=300, message="Must be 300 characters or fewer")]
    )

    submit = SubmitField('Register Product')


class EditProductForm(FlaskForm):
    """Form to edit lifecycle fields of a registered product."""

    status = SelectField(
        "Status",
        choices=[
            ("manufactured", "Manufactured"),
            ("designed", "Designed"),
            ("installed", "Installed"),
            ("in-use", "In Use"),
            ("in_use", "In Use"),
            ("maintenance", "Maintenance"),
            ("repaired", "Repaired"),
            ("in_repair", "In Repair"),
            ("in_storage", "In Storage"),
            ("retired", "Retired"),
            ("recycled", "Recycled"),
            ("lost", "Lost"),
        ],
        validators=[DataRequired(message="This field is required")]
    )
    numberOfUses = IntegerField(
        "Number of Uses",
        validators=[
            Optional(),
            NumberRange(min=0, message="Must be 0 or greater")
        ]
    )
    condition = SelectField(
        "Condition",
        choices=[
            ("new", "New"),
            ("good", "Good"),
            ("worn", "Worn"),
            ("fair", "Fair"),
            ("poor", "Poor"),
            ("damaged", "Damaged"),
            ("repaired", "Repaired"),
        ],
        validators=[DataRequired(message="This field is required")]
    )
    currentLocation = StringField(
        "Current Location",
        validators=[DataRequired(message="This field is required")]
    )
    lastMaintenanceDate = DateField(
        "Last Maintenance Date",
        format='%Y-%m-%d',
        validators=[Optional()]
    )
    lifecycleCarbonFootprint = FloatField(
        "Lifecycle Carbon Footprint (kgCO₂)",
        validators=[
            Optional(),
            NumberRange(min=0, message="Must be 0 or greater")
        ]
    )
    submit = SubmitField('Save Changes')