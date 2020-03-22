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

                        # app.config["SQLALCHEMY_DATABASE_URI"] = os.getenv
app.config["SQLALCHEMY_DATABASE_URI"] = "postgres://nvjgfrayuptlkt:e7d1e4aeddb1b44888b9817872f22fc522d332bb0d453b1633bbf8688f57d266@ec2-18-235-20-228.compute-1.amazonaws.com:5432/d784oou6iuu63p"
# app.config["SECRET_KEY"] = 'S3CRET!K3Y11!'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

from models import User, user_schema

@app.route("/health", methods=['GET'])
def health():
    return {
        "Success": True
    }

@app.route("/signUp", methods=['POST'])
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

@app.route('/approveClient', methods=['PUT'])
def approveClient():
    body = request.get_json(force=True)
    user = User()
    # retrieve user with id passed in
    user = User.query.get(body['id'])

    if body['access_token'] == user.access_token:
        try:
            # update the approved field for this user
            user.approved = True
            db.session.commit()
        except:
            return {
                "error": "could not approve client for this user"
            }
    else:
        return {
                "error": "incorrect access token"
        }
    
    # Refresh the user to grab the id
    db.session.refresh(user)

    # Grab the user from the database and dump the result into a user schema
    user = User.query.get(user.id)
    result = user_schema.dump(user)
    # Return the user
    return {
        "user": result
    }

@app.route('/clientList', methods=['GET'])
def clientList():
    body = request.get_json(force=True)
    user = User()
    # retrieve user with id passed in
    user = User.query.get(body['id'])
    
    # check that the user is the coach
    if user.id == 1:
        try:
            # retrieve and return list of clients
            clients = User.query.filter(User.coach_id == 1).all()
            results = [
                {
                    "user_id": client.id,
                    "first_name": client.first_name
                }for client in clients
            ]
            return {
                "clients": results
            } 
        except:
            return {
                "error": "could not list clients"
            }
    else:
        return {
                "permission error": "only the coach can view a client list"
        }
    
    # Refresh the user to grab the id
    db.session.refresh(user)



