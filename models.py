from app import db, app
from flask_marshmallow import Marshmallow
from enum import Enum
import jwt
import datetime

ma = Marshmallow(app)

class User(db.Model):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    first_name = db.Column(db.String, nullable=False)
    last_name = db.Column(db.String, nullable=False)
    email = db.Column(db.String, nullable=False, unique=True)
    password = db.Column(db.String, nullable=False)
    approved = db.Column(db.Boolean, nullable=True)
    check_in = db.Column(db.Boolean, nullable=True)
    coach_id = db.Column(db.Integer, nullable=True)
    access_token = db.Column(db.String, nullable=True)
    role = db.Column(db.String, nullable=False)
    verification_token = db.Column(db.String, nullable=True)
    verified = db.Column(db.Boolean, nullable=False)

    def encode_auth_token(self, sub):
        """
        Generates the Auth Token
        :sub: a dictionary containing any valid values
        :return: string
        """
        try:
            payload = {
                'exp': datetime.datetime.utcnow() + datetime.timedelta(days=0, hours=2),
                'iat': datetime.datetime.utcnow(),
                'sub': sub
            }
            return jwt.encode(
                payload,
                app.config.get('SECRET_KEY'),
                algorithm='HS256'
            ).decode(encoding="utf-8")
        except Exception as e:
            return e

    @staticmethod
    def decode_auth_token(auth_token):
        """
        Decodes the auth token
        :param auth_token:
        :return: integer|string
        """
        try:
            payload = jwt.decode(auth_token, app.config.get('SECRET_KEY'))
            return payload['sub']
        except jwt.ExpiredSignatureError:
            return 'Expired'
        except jwt.InvalidTokenError:
            return 'Invalid'

class UserSchema(ma.Schema):
    class Meta:
        fields = ('id', 'first_name', 'last_name', 'email', 'password', 'approved', 'check_in', 'coach_id', 'access_token', 'role', 'verification_token', 'verified')

# class UserSchemas(ma.Schema):
#     class Meta:
#         fields = ('id', 'first_name', 'last_name', 'email', 'password', 'approved', 'check_in', 'coach_id', 'access_token', 'role', 'verification_token')

user_schema = UserSchema()

class Role(Enum):
    COACH = 'COACH'
    CLIENT = 'CLIENT'

