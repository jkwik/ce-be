from backend import app, bcrypt, mail, db
from backend.models.user import User, user_schema
from backend.helpers.emails import forgotPasswordEmail
from flask import request, session, redirect
from email_validator import validate_email, EmailNotValidError
import os
import uuid

@app.route("/auth/login", methods=["POST"])
def login():
    body = request.get_json(force=True)

    #  trim the email to remove unnecessary spaces
    email = body['email'].strip()
    # convert input email to lowercase
    email = email.lower()
    # Validate that the email is the correct format
    try:
        v = validate_email(email) # validate and get info
        email = v["email"] # replace with normalized form
    except EmailNotValidError as e:
        # email is not valid, return error code
        return {
            "error": "Invalid Email Format"
        }, 406

    # Grab user from the database given email and password combination
    user = User.query.filter_by(email=email).first()
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
    user.reset_token = str(resetToken)
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
