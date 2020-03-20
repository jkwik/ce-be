from flask import Flask, request, make_response
from flask_sqlalchemy import SQLAlchemy, inspect
from flask_cors import CORS
from dotenv import load_dotenv
import os

load_dotenv()

# Create a new instance of a flask app
app = Flask(__name__)
# Enable cors for the frontend
CORS(app, supports_credentials=True)

# Set the database uri to the config var and create a connection to the db. In a real production app
# this connection string would be set as an environment variable
app.config["SQLALCHEMY_DATABASE_URI"] = os.getenv
# app.config["SECRET_KEY"] = 'S3CRET!K3Y11!'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

from models import User, user_schema

@app.route("/health", methods=["GET"])
def health():
    return {
        "Success": True
    }

@app.route("/signUp", methods=["POST"])
def signUp():
    body = request.get_json(force=True)
    user = User()

    user = User(first_name=body['first_name'], last_name=body['last_name'], email=body['email'], password=body['password'])

    try:
        db.session.add(user)
        db.session.commit()
    except:
        return {
            "error": "403"
        }

    # Refresh the user to grab the id
    db.session.refresh(user)

    # Grab the user from the database and dumpp the result into a user schema
    user = User.query.get(user.id)
    result = user_schema.dump(user)

    # Return the user
    return {
        "user": result
    }
