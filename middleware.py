from flask import session
from functools import wraps
from models import User
from app import db

def http_guard(renew=True, nullable=False):
    """Checks for the presence and validity of the access token. It also handles renewing the access_token
    and updating it in the db if it is expired

    Parameters
    ----------
    renew : bool (default True)
        Whether or not the access_token should be renewed and updated in the users DB if expired
    nullable : bool (default False)
        Whether non-existent or empty access_tokens should be granted access to the endpoint

    Injects (as a parameter into endpoint method)
    -------
    user : dict
        Dictionary containing decoded contents of the access_token
    """
    def _http_guard(f):
        @wraps(f)
        def __http_guard():
            # Grab the access_token from the session
            token = session.get('access_token', None)

            # If it is empty, or it doesn't exist, this means user is not logged in. Return unauthorized
            # if nullable is False
            if (token == None or token == "") and nullable == False:
                return {
                    "error": "Unauthorized. User is not logged in"
                }, 401

            # Check that there is a user who owns the access_token. Return unauthorized
            # if nullable is False
            user = User.query.filter_by(access_token=token).first()
            if user == None:
                return {
                    "error": "Unauthorized. Invalid access token"
                }, 401

            # Check that the token is expired or not. Renew it if renew is True
            payload = user.decode_auth_token(user.access_token)
            if payload == 'Expired' and renew == True:
                token = user.encode_auth_token({
                    'id': user.id,
                    'role': user.role
                })

                # Update the users access_token in the db
                user.access_token = token
                db.session.commit()

                # Set the session access_token cookie
                session['access_token'] = token

            result = f(user.decode_auth_token(token))
            return result
        return __http_guard
    return _http_guard
