from flask import Flask, request, make_response, session, redirect
from flask_session import Session
from flask_sqlalchemy import SQLAlchemy, inspect
from flask_cors import CORS
from dotenv import load_dotenv
from sqlalchemy.exc import IntegrityError
from email_validator import validate_email, EmailNotValidError
from flask_bcrypt import Bcrypt
from flask_mail import Mail
import os
import datetime
import uuid

load_dotenv()

# Create a new instance of a flask app
app = Flask(__name__)

# Enable cors for the frontend
CORS(app, supports_credentials=True)

# Set the database app config vars
app.config["SQLALCHEMY_DATABASE_URI"] = os.getenv("DATABASE_URL")
app.config["SECRET_KEY"] = os.getenv("SECRET_KEY")
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
Session(app)

# Configure flask mail
app.config["MAIL_SERVER"] = os.getenv("MAIL_SERVER")
app.config["MAIL_PORT"] = os.getenv("MAIL_PORT")
# app.config["MAIL_USE_SSL"] = True
app.config["MAIL_USE_TLS"] = 1
app.config["MAIL_USERNAME"] = os.getenv("MAIL_USERNAME")
app.config["MAIL_PASSWORD"] = os.getenv("MAIL_PASSWORD")
mail = Mail(app)

# Uncomment these lines below when needing to create a new session table in the db
# session = Session(app)
# session.app.session_interface.db.create_all()

from models import User, user_schema, Role
from helpers import sendVerificationEmail

@app.route("/health", methods=["GET"])
def health():
    return {
        "Success": True
    }

@app.route("/signUp", methods=["POST"])
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
        approved=False, role=body['role'],
        verified=False
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
        db.session.rollback()
        return {
            "error": "Internal Server Error"
        }, 500

    # Generate a new verification token
    verificationToken = uuid.uuid1()

    # Update the users access_token and verification_token and commit the result
    user.access_token = token
    user.verification_token = verificationToken
    db.session.commit()

    # Send a verification email
    err = sendVerificationEmail(mail, [user.email], user.first_name, user.last_name, str(verificationToken))
    if err != None:
        print(err)
        db.session.rollback()
        return {
            "error": "Internal Server Error"
        }, 500

    # Set the session access_token
    session['access_token'] = token

    result = user_schema.dump(user)

    # Delete the password from the response, we don't want to transfer this over the wire
    del result['password']
    # Delete the access token and verification token as we don't want this to be in the resopnse
    del result['access_token']
    del result['verification_token']

    # Return the user
    return {
        "user": result
    }

@app.route("/verifyUser", methods=["GET"])
def verifyUser():
    # Grab the verification token from the query parameter
    verificationToken = request.args.get('verification_token')
    email = request.args.get('email')

    if verificationToken == None:
        return {
            "error": "No verification_token present in query parameter"
        }, 400
    if email == None:
        return {
            "error": "No email present in query parameter"
        }, 400

    # Check that the verification_token belongs to the email
    user = User.query.filter_by(email=email, verification_token=verificationToken).first()
    if user == None:
        return {
            "error": "Invalid verification_token or email"
        }, 404

    # If it does, then we set the verified field to True and remove the verification_token
    user.verification_token = ''
    user.verified = True
    db.session.commit()

    # Redirect to the frontend homepage
    return redirect(os.getenv("FRONTEND_URL"), code=302)

@app.route("/auth/login", methods=["POST"])
def login():
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

    # Grab user from the database given email and password combination
    user = User.query.filter_by(email=body['email']).first()
    if user == None:
        return {
            "error": "Invalid username or password"
        }, 404

    # Check that the passwords match
    if not bcrypt.check_password_hash(user.password, body['password'].encode(encoding='utf-8')):
        return {
            "error": "Invalid username or password"
        }, 404

    token = ''

    # If the users access_token is empty, create a new one for them
    if user.access_token == '' or user.access_token == None:
        token = user.encode_auth_token({
            'id': user.id,
            'role': user.role
        })

        # Update the users access_token
        user.access_token = token
        db.session.commit()
    else:
        # If the user has an access token, check if it is expired
        payload = user.decode_auth_token(user.access_token)
        if payload == 'Expired':
            print('expired')
            token = user.encode_auth_token({
                'id': user.id,
                'role': user.role
            })

            # Update the users access_token
            user.access_token = token
            db.session.commit()
        elif payload == 'Invalid':
            # Invalid tokens are intolerable
            print('User with email ' + user.email + ' has invalid access_token')
            return {
                "error": "Internal Server Error"
            }, 500
        else:
            # If the access_token is valid and is non empty, we use this token
            token = user.access_token

    # Set the access_token in the session
    session['access_token'] = token

    # Parse the result of the user query
    result = user_schema.dump(user)

    # Delete the sensitive information
    del result['password']
    del result['access_token']
    del result['verification_token']

    return {
        "user": result
    }

