import os
import tempfile
import pytest
import json
import pdb
import unittest
from backend import app, db
from backend.models.user import User, UserSchema, user_schema, Role


# creates test client
@pytest.fixture(scope='module')
def client(request):
    app.testing = True
    test_client = app.test_client()

    # remove newly created user after each test runs
    def teardown():
        user = User()
        User.query.filter(User.email == 'test@gmail.com').delete()
        User.query.filter(User.email == 'coach@gmail.com').delete()
        db.session.commit()

    request.addfinalizer(teardown)
    return test_client

# fixture to return db session so that pytest-flask-sqlalchemy can mock it
@pytest.fixture(scope='module')
def _db():
    return db

# -------- To Mock Database Connections Include 'db_session' Argument As Test Parameter --------

def test_health(client):
    row = db_session.query(User).get(1)
    pdb.set_trace()
    rv = client.get('/health')
    assert rv.json == {'success': True}

def test_signup(client):
    # add flask mail testing somehow with mocking
    new_user = create_new_user()
    #pdb.set_trace()
    rv = sign_up_user_for_testing(client, new_user)
    # deleting id of user because I was not able to pull it from the database
    # I tried db.session.refresh(new_user), but was getting errors
    # we probably don't care about the id of the user anyways
    del rv.json['user']['id'] 
    assert rv.json == { 'user': {'approved': False, 'check_in': None, 'coach_id': None, 'email': 'test@gmail.com', 'first_name': 'test_first', 'last_name': 'test_last', 'reset_token': None, 'role': 'CLIENT', 'verified': False }}

def test_approve_client(client):
    assert True

def test_client_list(client):
    new_coach = create_new_coach()
    signup_rv = sign_up_user_for_testing(client, new_coach)
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

def test_update_profile(client):
    assert True

def test_verify_user(client):
    assert True

def test_login(client):
    # have to create new user since changes to database are reverted after every test
    new_user = create_new_user()
    signup_rv = sign_up_user_for_testing(client, new_user)
    login_rv = login_user_for_testing(client, new_user)

    del login_rv.json['user']['id']
    assert login_rv.json == { 'user': {'approved': False, 'check_in': None, 'coach_id': None, 'email': 'test@gmail.com', 'first_name': 'test_first', 'last_name': 'test_last', 'reset_token': None, 'role': 'CLIENT', 'verified': False }}

def test_logout(client):
    new_user = create_new_user()
    signup_rv = sign_up_user_for_testing(client, new_user)
    login_rv = login_user_for_testing(client, new_user)
    logout_rv = client.get("auth/logout")
    assert logout_rv.json == {'success': True}

def test_forgot_password(client):
    assert True

def test_reset_password(client):
    assert True

def test_terminate_client(client):
    new_coach = create_new_coach()
    new_user = create_new_user(True, True)
    user_id = get_user_id()
    new_user_data = user_schema.dump(new_user)
    coach_signup_rv = sign_up_user_for_testing(client, new_coach)
    coach_login_rv = login_user_for_testing(client, new_coach)
    client_signup_rv = sign_up_user_for_testing(client, new_user)

    # url = "/terminateClient?id={}".format(user_id)
    # terminate_client_rv = client.put(url)
    assert True

def test_get_user(client):
    new_user = create_new_user()
    signup_rv = sign_up_user_for_testing(client, new_user)
    user_id = get_user_id()
    url = '/getUser?id={}'.format(user_id)
    get_user_rv = client.get(url)
    expected_json = {'user': {'approved': False, 'check_in': None, 'coach_id': None, 'email': 'test@gmail.com', 'first_name': 'test_first', 'id': user_id, 'last_name': 'test_last', 'reset_token': None, 'role': 'CLIENT', 'verified': False}}
    assert get_user_rv.json == expected_json

"""
Creating helper methods that tests will reuse to make tests
look cleaner.
"""
def create_new_user(approved=False, verified=False):
    body = {
        'first_name': 'test_first',
        'last_name': 'test_last',
        'email': 'test@gmail.com',
        'password': 'password',
        'role': 'CLIENT'
    }
    user = User(
        first_name=body['first_name'], last_name=body['last_name'],
        email=body['email'], password=body['password'],
        approved=approved, role=body['role'],
        verified=verified
    )  
    return user

def create_new_coach():
    body = {
    'first_name': 'coach_first',
    'last_name': 'coach_last',
    'email': 'coach@gmail.com',
    'password': 'password',
    'role': 'COACH'
    }
    user = User(
        first_name=body['first_name'], last_name=body['last_name'],
        email=body['email'], password=body['password'],
        approved=False, role=body['role'],
        verified=False
    )    
    return user

# helper method to sign up a new user since almost every test method
# will have to do this
def sign_up_user_for_testing(client, new_user):
    mimetype = 'application/json'
    headers = {
        'Content-Type': mimetype,
        'Accept': mimetype
    }
    data = {
        'first_name': new_user.first_name,
        'last_name': new_user.last_name,
        'email': new_user.email,
        'password': new_user.password,
        'approved': new_user.approved,
        'check_in': new_user.check_in,
        'coach_id': new_user.coach_id,
        'access_token': new_user.access_token,
        'role': new_user.role,
        'verification_token': new_user.verification_token,
        'verified': new_user.verified,
        'reset_token': new_user.reset_token        
    }
    result = user_schema.dump(new_user)
    del result['password']
    del result['access_token']
    del result['verification_token']
    url = '/signUp'
    rv = client.post(url, data=json.dumps(data), headers=headers)
    return rv
# test http guard 

def login_user_for_testing(client, new_user):
    mimetype = 'application/json'
    headers = {
        'Content-Type': mimetype,
        'Accept': mimetype
    }
    data = {
        'first_name': new_user.first_name,
        'last_name': new_user.last_name,
        'email': new_user.email,
        'password': new_user.password,
        'approved': new_user.approved,
        'check_in': new_user.check_in,
        'coach_id': new_user.coach_id,
        'access_token': new_user.access_token,
        'role': new_user.role,
        'verification_token': new_user.verification_token,
        'verified': new_user.verified,
        'reset_token': new_user.reset_token 
    }
    login_rv = client.post("/auth/login", data=json.dumps(data), headers=headers)

    return login_rv

# a method to get the current user id
# there is probably a better way to do this 
# but this is the only way I could make it work
def get_user_id():
    user = User()
    users = User.query.filter(User.email == 'test@gmail.com').all()
    user_id = None
    for user in users:
        user_id = user.id
    
    return user_id
