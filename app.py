from flask import Flask, request, make_response
from flask_sqlalchemy import SQLAlchemy, inspect
from flask_cors import CORS
from dotenv import load_dotenv
from sqlalchemy.exc import IntegrityError
from email_validator import validate_email, EmailNotValidError
from flask_bcrypt import Bcrypt
import os

load_dotenv()

# Create a new instance of a flask app
app = Flask(__name__)
# Enable cors for the frontend
CORS(app, supports_credentials=True)

# Set the database uri to the config var and create a connection to the db. In a real production app
# this connection string would be set as an environment variable
app.config["SQLALCHEMY_DATABASE_URI"] = os.getenv("DATABASE_URL")
app.config["SECRET_KEY"] = 'S3CRET!K3Y11!'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)
bcrypt = Bcrypt(app)

from models import User, user_schema

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
    encodedPassword = bcrypt.generate_password_hash(body['password'])

    # Create the user with the encoded password
    user = User()
    user = User(first_name=body['first_name'], last_name=body['last_name'], email=body['email'], password=encodedPassword)

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

    # Grab the user from the database and dumpp the result into a user schema
    user = User.query.get(user.id)
    result = user_schema.dump(user)

    # Delete the password from the response, we don't want to transfer this over the wire
    del result['password']

    # Return the user
    return {
        "user": result
    }
