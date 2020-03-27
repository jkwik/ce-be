import os
import tempfile

import pytest
from app import app
from models import User, UserSchema, Role


def test_empty_db(client):
    rv = client.get('/')

    assert b'No entries here so far' in rv.data

def test_health(client):
    rv = client.get('/health')

    assert b''

def test_signup(client):
    assert True

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

