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

from models import User, user_schema, Role, user_schemas, CoachSession, coach_session_schema, coach_session_schemas, CoachTemplate, coach_template_schema, coach_template_schemas, CoachExercise, coach_exercise_schema, coach_exercise_schemas, Exercise, exercise_schema, exercise_schemas, ClientTemplate, client_template_schema, client_template_schemas, ClientSession, client_session_schema, client_session_schemas, ClientExercise, client_exercise_schema, client_exercise_schemas, CheckIn, check_in_schema, check_in_schemas, TrainingEntry, training_entry_schema, training_entry_schemas 
from helpers import sendVerificationEmail, sendApprovedEmail, forgotPasswordEmail
from middleware import http_guard

@app.route("/middleware", methods=["GET"])
@http_guard(renew=True, nullable=False)
def middleware(token_claims):
    return {
        "token_claims": token_claims
    }

@app.route("/health", methods=['GET'])
def health():
    return {
        "success": True
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
        print(e)
        return {
            "error": "Internal Server Error"
        }, 500
        raise

    # Refresh the user to grab the id
    db.session.refresh(user)

    # Grab the user from the database and dump the result into a user schema
    user = User.query.get(user.id)

    # Generate a new access token
    # encode own token and put it in session before calling the endpoint
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

    db.session.close()

    # Return the user
    return {
        "user": result
    }

@app.route('/approveClient', methods=['PUT'])
@http_guard(renew=True, nullable=False)
def approveClient(token_claims):
    body = request.get_json(force=True)
    # Check that the role of the requestee is COACH
    if token_claims['role'] != Role.COACH.name:
        return {
            "error": "Expected role of COACH"
        }, 400

    # retrieve user with id passed in
    user = User()
    user = User.query.get(body['id'])

    try:
        # update the approved field for this user
        user.approved = True
        # set coach_id to the id of the coach that is currently logged in
        user.coach_id = token_claims['id']
        db.session.commit()

    except Exception as e:
        return {
            "error": "Internal Server Error"
        }, 500
        raise

    # Grab the user from the database and dump the result into a user schema
    user = User.query.get(user.id)

    # Send an approved email
    err = sendApprovedEmail(mail, [user.email], user.first_name, user.last_name)
    if err != None:
        print(err)
        db.session.rollback()
        return {
             "error": "Internal Server Error"
        }, 500
    
    result = user_schema.dump(user)
    # remove the sensitive data fields
    del result['password']
    del result['access_token']
    del result['verification_token']

    db.session.close()
    # Return the user
    return {
        "Approved": result
    }

@app.route('/clientList', methods=['GET'])
@http_guard(renew=True, nullable=False)
def clientList(token_claims):
    # Check that the role of the requestee is COACH
    if token_claims['role'] != Role.COACH.name:
        return {
            "error": "Expected role of COACH"
    }, 400

    # retrieve list of clients 
    try:
        clients = User.query.filter_by(role='CLIENT').all()
        result = user_schemas.dump(clients)
        # create array's for type of client
        approvedClients = []
        unapprovedClients = []
        pastClients = []
        for client in result:
            # remove sensitive data
            del client['password']
            del client['access_token']
            del client['verification_token']

            # check client's approved filed
            # if approved this is a current client
            if client['approved'] == True:
                approvedClients.append(client)
            # if unapproved this is a client awaiting approval
            elif client['approved'] == False:
                unapprovedClients.append(client)
            # if null, this is a past client
            else:
                pastClients.append(client)
        # Return the clients
        # close db connection
        db.session.close()
        return {
            "approvedClients": approvedClients,
            "unapprovedClients": unapprovedClients,
            "pastClients": pastClients
        }
    except Exception as e:
        return {
            "error": "Internal Server Error"
        }, 500
        raise

@app.route('/updateProfile', methods=['PUT'])
@http_guard(renew=True, nullable=False)
def updateProfile(token_claims):
    body = request.get_json(force=True)
     # retrieve user with id passed in
    user = User()
    user = User.query.get(token_claims['id'])
    # check which parameters were passed into this function
    if 'email' in body:
        newEmail = True
        try:
            v = validate_email(body["email"]) # validate and get info
            email = v["email"] # replace with normalized form
        except EmailNotValidError as e:
            # email is not valid, return error code
            return {
                "error": "Invalid Email Format"
            }, 406
    else:
        newEmail = False

    if 'first_name' in body:
        newFirstName = True
    else:
        newFirstName = False

    if 'last_name' in body:
        newLastName = True
    else:
        newLastName = False
    
    if 'newPassword' in body:
        # check that the current password field was entered
        if 'oldPassword' not in body:
            return{
                "error": "User must enter old password"
            }
        # check that oldPassword matches the password in the database
        if not bcrypt.check_password_hash(user.password, body['oldPassword'].encode(encoding='utf-8')):
            return {
                "error": "The old password doesn't match the password in the database"
            }, 400
        newPassword = True
        encodedPassword = bcrypt.generate_password_hash(body['newPassword']).decode(encoding="utf-8")
    else:
        newPassword = False

     # update the requested fields for this user
    try:
        if newEmail == True:
            user.email = email
        if newFirstName == True:
            user.first_name = body['first_name']
        if newLastName == True:
            user.last_name = body['last_name']
        if newPassword == True:
            user.password = encodedPassword
        db.session.commit()
    except Exception as e:
        return {
            "error": "Internal Server Error"
        }, 500
        raise

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
    db.session.close()
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
    db.session.close()

    # Redirect to the frontend homepage
    return redirect(os.getenv("PROD_FRONTEND_URL"), code=302)

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
    db.session.close()
    return {
        "user": result
    }

@app.route("/auth/logout", methods=["GET"])
def logout():
    # Grab the access_token from the session
    token = session.get('access_token')
    if token == None or token == "":
        return {
            "error": "No user is currently logged in"
        }, 400

    # Check that there is a user who has the access_token
    user = User.query.filter_by(access_token=token).first()
    if user == None:
        return {
            "error": "Invalid access token"
        }, 400

    # Set the users access token to an empty string in the db
    user.access_token = ''
    db.session.commit()

    # Delete the access_token cookie from session
    session.pop('access_token')
    db.session.close()
    return {
        "success": True
    }

@app.route("/forgotPassword", methods=["GET"])
def forgotPassword():
    email = request.args.get('email')
    if email == None:
        return {
            "error": "No email parameter found in request"
        }, 404
    # validate email format
    try:
        v = validate_email(email) # validate and get info
        email = v["email"] # replace with normalized form
    except EmailNotValidError as e:
        # email is not valid, return error code
        return {
            "error": "Invalid Email Format"
        }, 406

    # retrieve user with id passed in
    user = User()
    user = User.query.filter_by(email=email).first()

    if user == None:
        return {
            "error": "Invalid email: Email not found"
        }, 404

    # create a reset token and set it to be this user's reset token
    resetToken = uuid.uuid1()
    user.reset_token = resetToken
    db.session.commit()

    # send forgot password email to the user
    err = forgotPasswordEmail(mail, [email], user.first_name, user.last_name, str(resetToken))
    if err != None:
        print(err)
        db.session.rollback()
        return {
             "error": "Internal Server Error"
        }, 500
    db.session.close()
    return {
        "success": True
    }

@app.route("/resetPassword", methods=["POST"])
def resetPassword():
    body = request.get_json(force=True)
    # Grab the verification token from the query parameter
    resetToken = body['reset_token']
    password = body['password']

    if resetToken == None:
        return {
            "error": "No reset_token present in query parameter"
        }, 400

    # Check that the reset_token belongs to the email
    user = User.query.filter_by(reset_token=resetToken).first()
    if user == None:
        return {
            "error": "Invalid reset_token or email"
        }, 404

    # If it does, then we set the password field to the new password, and remove the reset_token
    user.reset_token = ''
    # Encrypt the password
    encodedPassword = bcrypt.generate_password_hash(password).decode(encoding="utf-8")
    user.password = encodedPassword
    db.session.commit()
    db.session.close()

    # Redirect to the frontend homepage
    return {
        "success": True
    }

# terminate client endpoint
@app.route("/terminateClient", methods=["PUT"])
@http_guard(renew=True, nullable=False)
def terminateClient(token_claims):
    body = request.get_json(force=True)
    # Check that the role of the requestee is COACH
    if token_claims['role'] != Role.COACH.name:
        return {
            "error": "Expected role of COACH"
    }, 400

    # retrieve user with id passed in
    user = User()
    user = User.query.get(body['id'])

    try:
        # update the approved field for this user to null
        user.approved = None
        db.session.commit()
    except Exception as e:
        return {
            "error": body['id']
        }, 500
        raise

    # Grab the user from the database and dump the result into a user schema
    user = User.query.get(user.id)
    result = user_schema.dump(user)
    # remove the sensitive data fields
    del result['password']
    del result['access_token']
    del result['verification_token']

    db.session.close()
    # Return the user
    return {
        "user": result
    }

@app.route('/getUser', methods=['GET'])
@http_guard(renew=True, nullable=False)
def getUser(token_claims):
    # check the role of the requestee
    if token_claims['role'] != Role.COACH.name:
        return {
            "error": "Expected role of COACH"
    }, 400

    id = request.args.get('id')
    if id == None:
        return {
            "error": "No id parameter found in request"
        }, 404

    # retrieve user with id passed in
    user = User()
    user = User.query.get(id)

    # check that this user exits
    if user == None:
        return {
            "error": "Invalid id"
        }, 404
    
    result = user_schema.dump(user)
    # remove the sensitive data fields
    del result['password']
    del result['access_token']
    del result['verification_token']

    db.session.close()
    # Return the user
    return {
        "user": result
    }

@app.route('/user', methods=['DELETE'])
@http_guard(renew=True, nullable=False)
def deleteUser(token_claims):
    id = request.args.get('id')
    if id == None:
        return {
            "error": "No id paramter found in request query"
        }, 400

    user = User.query.get(id)
    if user == None:
        return {
            "error": "No user found with passed id"
        }, 404

    # Delete the user
    db.session.delete(user)
    db.session.commit()

    return {
        "success": True
    }



# Iteration 2 -- RELATIONSHIP TESTS


# 1: Coach_templates and Coach_sessions (WORKS)
# Coach_templates test
@app.route("/coachTemplate", methods=['GET'])
def coachTemplate():
    # retrieve template belonging to session
    coach_session = CoachSession()
    coach_session = CoachSession.query.first()
    # uses the backref argument "coach_template"
    template = coach_session.coach_template

    if template == None:
        return {
             "error": "Invalid template id"
         }, 404

    result = coach_template_schema.dump(template)

    return {
         "template": result
    }

# Coach_sessions test (DOES NOT WORK  COMPLETELY)
@app.route("/coachSession", methods=['GET'])
def coachSession():
    # retrieve sessions belonging to the template with the passed in template id
    coach_template = CoachTemplate()
    coach_template = CoachTemplate.query.filter_by(id='1').first()
    # retrieve using foreign key "coach_sessions"
    sessions = coach_template.coach_sessions
    
    if sessions == None:
        return {
            "error": "Invalid session id"
        }, 404

    result = coach_session_schemas.dump(sessions)
   
    return {
        "coach sessions": result
    }

# 2: Coach_exercises and Exercises (WORKS)
# Exercises test
@app.route("/exercise", methods=['GET'])
def exercise():
    # retrieve the corresponding exercise belonging to the given coach_exercise
    coach_exercise = CoachExercise()
    coach_exercise = CoachExercise.query.first()
    # uses the backref argument "exercise"
    exercise = coach_exercise.exercise

    if exercise == None:
        return {
             "error": "Invalid template id"
         }, 404

    result = exercise_schema.dump(exercise)

    return {
         "exercise": result
    }

# Coach_exercises test (DOES NOT WORK  COMPLETELY)
@app.route("/coachExercise", methods=['GET'])
def coachExercise():
    # retrieve coach_exercise belonging to the exercise with the passed in exercise id
    exercise = Exercise()
    exercise = Exercise.query.filter_by(id='1').first()
    # retrieve using foreign key "coach_exercises"
    coach_exercise = exercise.coach_exercises
    
    if coach_exercise == None:
        return {
            "error": "Invalid session id"
        }, 404

    result = coach_exercise_schema.dump(coach_exercise)
   
    return {
        "coach_exercise": result
    }

# 3: Coach_sessions and Coach_exercises
# Coach_sessions to coach_exercises (DOES NOT WORK  COMPLETELY)
@app.route("/cs_to_ce", methods=['GET'])
def cs_to_ce():
    # retrieve coach_session belonging to coach_exercise
    coach_exercise = CoachExercise()
    coach_exercise = CoachExercise.query.first()
    # uses the backref argument "coach_session"
    coach_session = coach_exercise.coach_session

    if coach_session== None:
        return {
             "error": "Invalid template id"
         }, 404

    result = coach_session_schema.dump(coach_session)

    return {
         "coach_session": result
    }

# Coach_exercises to coach_sessions (DOES NOT WORK  COMPLETELY)
@app.route("/ce_to_cs", methods=['GET'])
def ce_to_cs():
    # retrieve exercises belonging to the session with the passed in session id
    coach_session = CoachSession()
    coach_session = CoachSession.query.filter_by(id='1').first()
    # retrieve using foreign key "coach_exercises"
    exercises = coach_session.coach_exercises
    
    if exercises == None:
        return {
            "error": "Invalid session id"
        }, 404

    result = coach_exercise_schemas.dump(exercises)
   
    return {
        "Coach_exercises ": result
    }
