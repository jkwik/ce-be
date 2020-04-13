import os
import tempfile
import pytest
import json
import pdb
import unittest
from backend import app, db
from backend.models.user import User, UserSchema, user_schema, Role
from flask_sqlalchemy import SQLAlchemy
from flask_session import Session

#  ----------------- SETUP -----------------

# Test client object that should be used when creating test clients
test_client = {
    'first_name': 'backend_tests_client',
    'last_name': 'backend_tests_client',
    'email': 'test@client.com',
    'password': 'fakepassword',
    'role': 'CLIENT'
}

# Test client object that should be used when creating test coaches
test_coach = {
    'first_name': 'backend_tests_coach',
    'last_name': 'backend_tests_coach',
    'email': 'test@coach.com',
    'password': 'fakepassword',
    'role': 'COACH'
}

# Creates the app test client so that we can use it to call endpoints in our applicatoin
@pytest.fixture(scope='function')
def client(request):
    test_client = app.test_client()
    return test_client

# Database fixture. We create an in-memory SQlite database and use this for all tests. That way
# we don't put stress on our production database. It's important here that the scope is set to function
# so that the transactions are rolled back on every transaction
@pytest.fixture(scope='function')
def _db():
    app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite://"
    # Comment above and uncomment below to persist the database to the local folder structure
    # app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite://test.db"
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

    # Create sessions table to handle login sessions
    session = Session(app)
    session.app.session_interface.db.create_all()

    # We migrate the model into the sqlite database. It will create all tables based on the schema.
    # We need to use the production database in order to migrate the data because the models are attached to this
    # object
    db.create_all()

    return db

#  ----------------- CONFIGURATION TEST -----------------

# Test that the mocked db_session works and doesn't persist beyond the scope of a test
def test_a_transaction(db_session):
    user = User(
        first_name=test_client['first_name'], last_name=test_client['last_name'],
        email=test_client['email'], password=test_client['password'],
        role=test_client['role'], verified=False
    )

    db_session.add(user)
    db_session.commit()

def test_transaction_doesnt_persist(db_session):
    user = db_session.query(User).filter_by(email=test_client['email']).first()
    assert user == None

def test_health(client):
    resp, code = request(client, 'GET', '/health')
    assert code == 200
    assert resp == {'success': True}

#  ----------------- USER TESTS -----------------

def test_signup(client, db_session):
    resp = sign_up_user_for_testing(client, test_client)
    del resp['user']['id']
    assert resp ==\
        {
            'user': {
                'approved': False,
                'check_in': None,
                'coach_id': None,
                'email': test_client['email'],
                'first_name': test_client['first_name'],
                'last_name': test_client['last_name'],
                'reset_token': None,
                'role': test_client['role'],
                'verified': False
            }
        }

def test_verify_client(client, db_session):
    # Create an unapproved user
    resp = sign_up_user_for_testing(client, test_client)
    assert resp['user']['approved'] == False

    # Query the user so we can grab the verification token
    user = User.query.filter_by(email=resp['user']['email']).first()
    assert user != None
    assert user.verification_token != None and user.verification_token != ""

    # Approve the user using his verification token
    url = '/verifyUser?verification_token={}&email={}'.format(user.verification_token, user.email)
    resp, code = request(client, "GET", url)

    # Refresh the user and check that they have been verified
    user = User.query.get(user.id)
    assert user.verified == True

    # Check that the server redirected the client
    assert code == 302
    assert resp == None

def test_client_list(client, db_session):
    # Sign up a coach so that sign is as a coach.
    user = sign_up_user_for_testing(client, test_coach)
    assert user['user'] != None
    assert user['user']['role'] == 'COACH'

    # Sign into the coach
    login_resp = login_user_for_testing(client, test_coach)
    assert login_resp['user']['id'] != None and login_resp['user']['id'] != ""

    # Populate the database with approved, unapproved and past clients
    clients = [
        User(
            first_name='test1', last_name='test1',
            email='test1@user.com', password='fakepassword',
            role='CLIENT', verified=False, approved=None
        ),
        User(
            first_name='test2', last_name='test2',
            email='test2@user.com', password='fakepassword',
            role='CLIENT', verified=False, approved=True
        ),
        User(
            first_name='test3', last_name='test3',
            email='test3@user.com', password='fakepassword',
            role='CLIENT', verified=False, approved=False
        )
    ]
    db_session.bulk_save_objects(clients)
    db_session.commit()

    # Grab the clients through the endpoint
    clients_resp, code = request(client, "GET", '/clientList')
    assert clients_resp != None and code == 200
    
    # Check that the clients are returned
    assert len(clients_resp['approvedClients']) != 0
    assert len(clients_resp['unapprovedClients']) != 0
    assert len(clients_resp['pastClients']) != 0

def test_update_profile(client, db_session):
    # sign up user
    resp = sign_up_user_for_testing(client, test_client)
    assert user['user'] != None
    assert resp['user']['first_name'] == 'backend_tests_client'

    # Sign as user
    login_resp = login_user_for_testing(client, test_client)
    assert login_resp['user']['id'] != None and login_resp['user']['id'] != ""

    # grab the user
    user = User.query.filter_by(email=resp['user']['email']).first()
    # change first_name


    db_session.commit()



# def test_verify_user(client):
#     assert True

# def test_login(client):
#     # have to create new user since changes to database are reverted after every test
#     new_user = create_new_user()
#     signup_rv = sign_up_user_for_testing(client, new_user)
#     login_rv = login_user_for_testing(client, new_user)

#     del login_rv.json['user']['id']
#     assert login_rv.json == { 'user': {'approved': False, 'check_in': None, 'coach_id': None, 'email': 'test@gmail.com', 'first_name': 'test_first', 'last_name': 'test_last', 'reset_token': None, 'role': 'CLIENT', 'verified': False }}

# def test_logout(client):
#     new_user = create_new_user()
#     signup_rv = sign_up_user_for_testing(client, new_user)
#     login_rv = login_user_for_testing(client, new_user)
#     logout_rv = client.get("auth/logout")
#     assert logout_rv.json == {'success': True}

# def test_forgot_password(client):
#     assert True

# def test_reset_password(client):
#     assert True

# def test_terminate_client(client):
#     new_coach = create_new_coach()
#     new_user = create_new_user(True, True)
#     user_id = get_user_id()
#     new_user_data = user_schema.dump(new_user)
#     coach_signup_rv = sign_up_user_for_testing(client, new_coach)
#     coach_login_rv = login_user_for_testing(client, new_coach)
#     client_signup_rv = sign_up_user_for_testing(client, new_user)

#     # url = "/terminateClient?id={}".format(user_id)
#     # terminate_client_rv = client.put(url)
#     assert True

# def test_get_user(client):
#     new_user = create_new_user()
#     signup_rv = sign_up_user_for_testing(client, new_user)
#     user_id = get_user_id()
#     url = '/getUser?id={}'.format(user_id)
#     get_user_rv = client.get(url)
#     expected_json = {'user': {'approved': False, 'check_in': None, 'coach_id': None, 'email': 'test@gmail.com', 'first_name': 'test_first', 'id': user_id, 'last_name': 'test_last', 'reset_token': None, 'role': 'CLIENT', 'verified': False}}
#     assert get_user_rv.json == expected_json

# def create_new_coach():
#     body = {
#     'first_name': 'coach_first',
#     'last_name': 'coach_last',
#     'email': 'coach@gmail.com',
#     'password': 'password',
#     'role': 'COACH'
#     }
#     user = User(
#         first_name=body['first_name'], last_name=body['last_name'],
#         email=body['email'], password=body['password'],
#         approved=False, role=body['role'],
#         verified=False
#     )    
#     return user

# sign up a user. It returns the user response. It also error checks
def sign_up_user_for_testing(client, user):
    mimetype = 'application/json'
    headers = {
        'Content-Type': mimetype,
        'Accept': mimetype
    }
    data = {
        'first_name': user['first_name'],
        'last_name': user['last_name'],
        'email': user['email'],
        'password': user['password'],
        'role': user['role']
    }
    
    resp = client.post('signUp', data=json.dumps(data), headers=headers)

    assert resp.json != None
    assert resp._status_code == 200

    return resp.json

# request is a helper method to make a request with the application client
def request(client, method, url, data=None):
    mimetype = 'application/json'
    headers = {
        'Content-Type': mimetype,
        'Accept': mimetype
    }

    resp = None
    if method == "GET":
        resp = client.get(url)
    elif method == "POST":
        resp = client.post(url, data=json.dumps(data), headers=headers)

    return resp.json, resp._status_code

# test http guard 

# Logs a user in. Input user should contain email and password. It also error checks
def login_user_for_testing(client, user):
    mimetype = 'application/json'
    headers = {
        'Content-Type': mimetype,
        'Accept': mimetype
    }
    data = {
        'email': user['email'],
        'password': user['password']
    }

    resp = client.post("/auth/login", data=json.dumps(data), headers=headers)

    assert resp.json != None
    assert resp._status_code == 200

    return resp.json

# # a method to get the current user id
# # there is probably a better way to do this 
# # but this is the only way I could make it work
# def get_user_id():
#     user = User()
#     users = User.query.filter(User.email == 'test@gmail.com').all()
#     user_id = None
#     for user in users:
#         user_id = user.id
    
#     return user_id
