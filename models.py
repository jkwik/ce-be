from app import db, app
from flask_marshmallow import Marshmallow
from enum import Enum

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
    role = db.Column(db.String, nullable=True)
    verification_token = db.Column(db.String, nullable=True)


class UserSchema(ma.Schema):
    class Meta:
        fields = ('id', 'first_name', 'last_name', 'email', 'password', 'approved', 'check_in', 'coach_id', 'access_token', 'role', 'verification_token')

class UsersSchema(ma.Schema):
    class Meta:
        fields = ('id', 'first_name', 'last_name', 'email', 'password', 'approved', 'check_in', 'coach_id', 'access_token', 'role', 'verification_token')

user_schema = UserSchema()
users_schema = UsersSchema(many=True)

class Role(Enum):
    COACH = 'COACH'
    CLIENT = 'CLIENT'