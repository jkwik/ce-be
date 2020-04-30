from backend import app, db, bcrypt, mail
from backend.models.user import User, user_schema, Role, user_schemas
from backend.helpers.emails import sendVerificationEmail, sendApprovedEmail
from backend.helpers.imgur import createAlbum
from backend.middleware.middleware import http_guard
from flask import request, session
from email_validator import validate_email, EmailNotValidError
import uuid
from sqlalchemy.exc import IntegrityError

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
            "error": "No id parameter found in request query"
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

@app.route("/signUp", methods=['POST'])
def signUp():
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
        email=email, password=encodedPassword,
        approved=False, role=body['role'],
        verified=False
    )

    # Create an album in imgur if we aren't being run by a test
    create_album = True
    if 'test' in body:
        if body['test'] == True:
            create_album = False

    if create_album:
        album_id, album_deletehash, code = createAlbum()
        if code != 200:
            print("Failed to create imgur album for user with code: " + str(code))
            return {
                "error": "Internal Server Error"
            }, 500
        
        user.album_id = album_id
        user.album_deletehash = album_deletehash

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
    verificationToken = str(uuid.uuid1())

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
