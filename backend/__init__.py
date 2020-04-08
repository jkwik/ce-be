from flask import Flask, session
from flask_session import Session
from flask_sqlalchemy import SQLAlchemy
from flask_cors import CORS
from dotenv import load_dotenv
from flask_bcrypt import Bcrypt
from flask_mail import Mail
import os
import datetime

# This initialization file serves to initialize all variables that will be used throughout the application

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

# Here, we import all the different modules
import backend.health
import backend.auth
import backend.user
