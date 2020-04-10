import os
import tempfile
import pytest
import json
import pdb
import unittest
from backend import app, db
from backend.models.user import User, UserSchema, user_schema, Role
import backend

# Test client object that should be used when creating test clients
test_client = {
    'first_name': 'backend_tests_client',
    'last_name': 'backend_tests_client',
    'email': 'backendclient@test.com',
    'password': 'fakepassword',
    'role': 'CLIENT'
}

# Test client object that should be used when creating test coaches
test_coach = {
    'first_name': 'backend_tests_coach',
    'last_name': 'backend_tests_coach',
    'email': 'backendcoach@test.com',
    'password': 'fakepassword',
    'role': 'COACH'
}

# Creates the app test client so that we can use it to call endpoints in our applicatoin
@pytest.fixture(scope='module')
def client(request):
    test_client = app.test_client()
    return test_client

# Fixture 
@pytest.fixture(scope='module')
def _db():
    return db

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

def test_approve_client(client, db_session):
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
    resp = sign_up_user_for_testing(client, test_coach)
    assert resp != None

    login_rv = login_user_for_testing(client, new_coach)
    client_list_rv = client.get("/clientList")

    # these would need to be populate with all of the
    # approved/unapproved/past clients in our database
    # so for now we are going to test if the response
    # simply gives us data back
    approvedClients = []
    unapprovedClients = []
    pastClients = []
    expected_json_response = {
            "approvedClients": approvedClients,
            "unapprovedClients": unapprovedClients,
            "pastClients": pastClients
        }
    
    assert client_list_rv.json != None

# def test_update_profile(client):
#     assert True

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

# helper method to sign up a new user since almost every test method
# will have to do this
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

# def login_user_for_testing(client, new_user):
#     mimetype = 'application/json'
#     headers = {
#         'Content-Type': mimetype,
#         'Accept': mimetype
#     }
#     data = {
#         'first_name': new_user.first_name,
#         'last_name': new_user.last_name,
#         'email': new_user.email,
#         'password': new_user.password,
#         'approved': new_user.approved,
#         'check_in': new_user.check_in,
#         'coach_id': new_user.coach_id,
#         'access_token': new_user.access_token,
#         'role': new_user.role,
#         'verification_token': new_user.verification_token,
#         'verified': new_user.verified,
#         'reset_token': new_user.reset_token 
#     }
#     login_rv = client.post("/auth/login", data=json.dumps(data), headers=headers)

#     return login_rv

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
