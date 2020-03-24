from flask import Flask, request, make_response, session
from flask_session import Session
from flask_sqlalchemy import SQLAlchemy, inspect
from flask_cors import CORS
from dotenv import load_dotenv
from sqlalchemy.exc import IntegrityError
from email_validator import validate_email, EmailNotValidError
from flask_bcrypt import Bcrypt
import os
import datetime

load_dotenv()

# Create a new instance of a flask app
app = Flask(__name__)
# Enable cors for the frontend
CORS(app, supports_credentials=True)
# Set the database app config vars
app.config["SQLALCHEMY_DATABASE_URI"] = os.getenv("DATABASE_URL")
app.config["SECRET_KEY"] = 'S3CRET!K3Y11!'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)
# Encryption package for passwords
bcrypt = Bcrypt(app)
# Session configuration, this creates the session table if it doesn't exist
app.config["SESSION_TYPE"] = 'sqlalchemy'
app.config["SESSION_COOKIE_NAME"] = 'access_token'
app.config["SESSION_COOKIE_HTTPONLY"] = True
app.config["SESSION_ALCHEMY"] = db
app.config["PERMANENT_SESSION_LIFETIME"] = datetime.timedelta(days=0, hours=24000)
app.config.from_object(__name__)
Session(app)
# Uncomment these lines below when needing to create a new session table in the db
# session = Session(app)
# session.app.session_interface.db.create_all()

from models import User, user_schema, Role

@app.route("/health", methods=['GET'])
def health():
    return {
        "Success": True
    }

@app.route("/signUp", methods=['POST'])
def signUp():
    body = request.get_json(force=True)

    # Validate that the email is the correct format
    try:
        v = validate_email(body['email']) # validate and get info
        body['email'] = v["email"] # replace with normalized form
    except EmailNotValidError as e:
        # email is not valid, return error code
        return {
            "error": "Invalid Email Format"
        }, 406

    # Encrypt the password
    encodedPassword = bcrypt.generate_password_hash(body['password']).decode(encoding="utf-8")

    # Check that they've passed a valid role
    try:
        role = body['role']

        if role != Role.CLIENT.name and role != Role.COACH.name:
            return {
                "error": "Expected role of COACH or CLIENT"
            }, 400
    except:
        return {
            "error": "Expected role of COACH or CLIENT"
        }, 400

    # Create the user with the encoded password
    user = User(
        first_name=body['first_name'], last_name=body['last_name'],
        email=body['email'], password=encodedPassword,
        approved=False, role=body['role']
    )

    try:
        db.session.add(user)
        db.session.commit()
    except IntegrityError:
        return {
            "error": "Duplicate Email"
        }, 409
    except Exception as e:
        return {
            "error": "Internal Server Error"
        }, 500
        raise

    # Refresh the user to grab the id
    db.session.refresh(user)

    # Grab the user from the database and dump the result into a user schema
    user = User.query.get(user.id)

    # Generate a new access token
    token = user.encode_auth_token({
        'id': user.id,
        'role': user.role
    })
    if isinstance(token, Exception):
        print(token) # This is printed as an error
        return {
            "error": "Internal Server Error"
        }, 500

    # Update the users access_token and commit the result
    user.access_token = token
    db.session.commit()

    # Set the session access_token
    session['access_token'] = token

    result = user_schema.dump(user)

    # Delete the password from the response, we don't want to transfer this over the wire
    del result['password']
    # Delete the access token as we don't want this to be in the resopnse
    del result['access_token']

    # Return the user
    return {
        "user": session['access_token']
    }

@app.route('/approveClient', methods=['PUT'])
def approveClient():
    body = request.get_json(force=True)
    cookie_access_token = session.get('access_token', 'not set')

    # Check that the role of the requestee is COACH
    try:
        role = body['role']

        if role != Role.COACH.name:
            return {
                "error": "Expected role of COACH"
            }, 400
    except:
        return {
            "error": "Expected role of COACH or CLIENT"
        }, 400

    # retrieve user with id passed in
    user = User()
    user = User.query.get(body['id'])
    decode = user.decode_auth_token(session.get('access_token', 'not set'))
    # TODO: change the access token check to 
    if cookie_access_token == decode:
    # if body['access_token'] == user.access_token:
        try:
            # update the approved field for this user
            user.approved = True
            db.session.commit()
        except Exception as e:
            return {
                "error": "Internal Server Error"
            }, 500
            raise
    else:
        return {
                "error": cookie_access_token
        }
    
    # Refresh the user to grab the id
    db.session.refresh(user)
    # Grab the user from the database and dump the result into a user schema
    user = User.query.get(user.id)
    result = user_schema.dump(user)
    # remove the sensitive data fields
    del result['password']
    del result['access_token']
    del result['verification_token']
    # Return the user
    return {
        "user": result
    }

@app.route('/clientList', methods=['GET'])
def clientList():
    body = request.get_json(force=True)

    # Check that the role of the requestee is COACH
    # try:
    #     role = body['role']

    #     if role != Role.COACH.name:
    #         return {
    #             "error": "Expected role of COACH"
    #         }, 400
    # except:
    #     return {
    #         "error": "Expected role of COACH or CLIENT"
    #     }, 400

    # retrieve user with id passed in
    user = User()
    
    # TODO: change the access token check to 
    # if body['access_token'] == user.access_token:
    try:
         # update the approved field for this user
        user = User.query.filter_by(coach_id=body['coach_id']).first()
        result = user_schema.dump(user)
        # remove the sensitive data fields
        del result['password']
        del result['access_token']
        del result['verification_token']
        # Return the user
        return {
            "user": result
        }
    except Exception as e:
        return {
            "error": "Internal Server Error"
        }, 500
        raise
  






