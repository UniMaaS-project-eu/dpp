from flask_wtf import FlaskForm
from wtforms import StringField, SubmitField
from wtforms.validators import DataRequired

class RegisterProductForm(FlaskForm):
    productID = StringField("Product ID", validators=[DataRequired(message="This field is required")])
    manufacturer = StringField("Manufacturer", validators=[DataRequired(message="This field is required")])
    model = StringField("Product model", validators=[DataRequired(message="This field is required")])
    productionDate = StringField("Manufacturing date", validators=[DataRequired(message="This field is required")])
    material = StringField("Product material", validators=[DataRequired(message="This field is required")])
    color = StringField("Color", validators=[DataRequired(message="This field is required")])
    serialNumber = StringField("Serial number", validators=[DataRequired(message="This field is required")])
    recyclability = StringField("Recyclability level", validators=[DataRequired(message="This field is required")])
    weight = StringField("Product weight", validators=[DataRequired(message="This field is required")])
    size = StringField("Product size (in cm)", validators=[DataRequired(message="This field is required")])
                                                                
    submit = SubmitField('Add product')