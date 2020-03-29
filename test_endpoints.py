import os
import tempfile
import pytest
import json
import pdb
from app import app
from models import User, UserSchema, user_schema, Role


@pytest.fixture(scope='module')
def client(request):
    test_client = app.test_client()

    def teardown():
        pass

    request.addfinalizer(teardown)
    return test_client

@pytest.fixture(scope='module')
def new_user():
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

def test_health(client):
    rv = client.get('/health')
    assert rv.json == {'success': True}

def test_signup(client, new_user):
    # flask mail mocking
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
    rv = client.post(url, data=json.dumps(data), headers=headers )
    assert rv.json == { 'user': result}

def test_approve_client(client):
    assert True

def test_client_list(client):
    assert True

def test_update_profile(client):
    assert True

def test_verify_user(client):
    assert True

def test_login(client):
    assert True

def test_logout(client):
    assert True

def test_forgot_password(client):
    assert True

def test_reset_password(client):
    assert True

def test_terminate_client(client):
    assert True

    

# test http guard 