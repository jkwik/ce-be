import os
import tempfile

import pytest
from app import app


def test_empty_db(client):
    rv = client.get('/')

    assert b'No entries here so far' in rv.data

def test_health(client):
    rv = client.get('/health')

    assert b''