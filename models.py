from app import db, app
from flask_marshmallow import Marshmallow

ma = Marshmallow(app)

class User(db.Model):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    first_name = db.Column(db.String, nullable=False)
    last_name = db.Column(db.String, nullable=False)
    email = db.Column(db.String, nullable=False)
    password = db.Column(db.String, nullable=False)
    approved = db.Column(db.Boolean, nullable=True)
    check_in = db.Column(db.Boolean, nullable=True)
    coach_id = db.Column(db.Integer, nullable=True)
    access_token = db.Column(db.String, nullable=True)

class UserSchema(ma.Schema):
    class Meta:
        fields = ('id', 'first_name', 'last_name', 'email', 'password', 'approved', 'check_in', 'coach_id', 'access_token')

user_schema = UserSchema()
