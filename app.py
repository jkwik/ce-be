from flask import Flask, request, make_response
from flask_sqlalchemy import SQLAlchemy, inspect
from flask_cors import CORS

# Create a new instance of a flask app
app = Flask(__name__)
# Enable cors for the frontend
CORS(app, supports_credentials=True)

# Set the database uri to the config var and create a connection to the db. In a real production app
# this connection string would be set as an environment variable
# TODO: Change this url
# app.config["SQLALCHEMY_DATABASE_URI"] = "postgres://spike:CS506SP1KE@spike.c5vhczbpkz10.us-east-2.rds.amazonaws.com:5432/spike"
app.config["SECRET_KEY"] = 'S3CRET!K3Y11!'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

@app.route("/health", methods=["GET"])
def health():
    return {
        "Success": True
    }
