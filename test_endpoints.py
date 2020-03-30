import os
import tempfile
import pytest
import json
import pdb
from app import app, db
from models import User, UserSchema, user_schema, Role


# creates test client
@pytest.fixture(scope='module')
def client(request):
    test_client = app.test_client()

    # remove newly created user after each test runs
    def teardown():
        user = User()
        User.query.filter(User.email == 'test@gmail.com').delete()
        db.session.commit()

    request.addfinalizer(teardown)
    return test_client

def test_health(client):
    rv = client.get('/health')
    assert rv.json == {'success': True}

def test_signup(client):
    # add flask mail testing somehow with mocking

    new_user, rv = sign_up_user_for_testing(client)

    # deleting id of user because I was not able to pull it from the database
    # I tried db.session.refresh(new_user), but was getting errors
    #pdb.set_trace()
    del rv.json['user']['id'] 
    assert rv.json == { 'user': {'approved': False, 'check_in': None, 'coach_id': None, 'email': 'test@gmail.com', 'first_name': 'test_first', 'last_name': 'test_last', 'reset_token': None, 'role': 'CLIENT', 'verified': False }}

def test_approve_client(client):
    assert True

def test_client_list(client):
    assert True

def test_update_profile(client):
    assert True

def test_verify_user(client):
    assert True

def test_login(client):
    # have to create new user since changes to database are reverted after every test
    new_user, signup_rv = sign_up_user_for_testing(client)
    login_rv = login_user_for_testing(client)

    del login_rv.json['user']['id']
    assert login_rv.json == { 'user': {'approved': False, 'check_in': None, 'coach_id': None, 'email': 'test@gmail.com', 'first_name': 'test_first', 'last_name': 'test_last', 'reset_token': None, 'role': 'CLIENT', 'verified': False }}

def test_logout(client):
    new_user, signup_rv = sign_up_user_for_testing(client)
    login_rv = login_user_for_testing(client)
    logout_rv = client.get("auth/logout")
    assert logout_rv.json == {'success': True}

def test_forgot_password(client):
    assert True

def test_reset_password(client):
    assert True

def test_terminate_client(client):
    assert True

"""
Creating helper methods that tests will reuse to make tests
look cleaner.
"""
def create_new_user():
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
        approved=False, role=body['role'],
        verified=False
    )    
    return user

# helper method to sign up a new user since almost every test method
# will have to do this
def sign_up_user_for_testing(client):
    new_user = create_new_user()
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
    return new_user, rv
# test http guard 

def login_user_for_testing(client):
    new_user, signup_rv = sign_up_user_for_testing(client)
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

