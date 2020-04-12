from backend import db, app
from backend.middleware.middleware import http_guard
from backend.models.user import User, Role
from backend.models.client_templates import ClientTemplate, client_template_schema, client_template_schemas, ClientSession, client_session_schema, ClientExercise, TrainingEntry
from backend.models.coach_templates import CoachTemplate, CoachSession, CoachExercise, coach_exercise_schema
from flask import request
from sqlalchemy.orm import load_only, Load, subqueryload
from datetime import date
from sqlalchemy import func

@app.route("/client/templates", methods=["GET"])
@http_guard(renew=True, nullable=False)
def getClientTemplates(token_claims):
    user_id = request.args.get('user_id')
    if user_id == None:
        return {
            "error": "No query parameter user_id found in request"
        }, 400

    templates = db.session.query(
        ClientTemplate.id, ClientTemplate.name, ClientTemplate.start_date, ClientTemplate.end_date,
        ClientTemplate.user_id, ClientTemplate.completed
    ).filter(ClientTemplate.user_id == user_id)

    result = client_template_schemas.dump(templates)

    return {
        "templates": result
    }

@app.route("/client/template", methods=["GET"])
@http_guard(renew=True, nullable=False)
def getClientTemplate(token_claims):
    # Any logged in user should be able to access this method
    id = request.args.get('id')
    if id == None:
        return {
            "error": "No query parameter id found in request"
        }, 400
    
    template = ClientTemplate.query.filter_by(id=id).first()

    templateResult = client_template_schema.dump(template)

    return {
        "template": templateResult
    }

@app.route("/client/template", methods=["POST"])
@http_guard(renew=True, nullable=False)
def createClientTemplate(token_claims):
    if token_claims['role'] != Role.COACH.name:
        return {
            "error": "Logged in user doesn't have a role of COACH"
        }, 401
    
    body = request.get_json(force=True)

    # Sanity check body data
    if 'sessions' not in body or 'coach_template_id' not in body or 'client_id' not in body:
        return {
            "error": "Need to specify a valid coach_template_id (int), client_id (int) and sessions (array)"
        }, 400
    coach_template_id = body['coach_template_id']
    client_id = body['client_id']
    sessions = body['sessions']
    if len(sessions) <= 0:
        return {
            "error": "Length of sessions supplied is 0"
        }, 400

    # Grab the coach template
    coach_template = CoachTemplate.query.filter_by(id=coach_template_id).first()
    if coach_template == None:
        return {
            "error": "No coach template found with coach_template_id: " + str(coach_template_id)
        }, 404
    # Grab the user with the client id
    client = User.query.filter_by(id=client_id).first()
    if client == None:
        return {
            "error": "No user found with user_id: " + str(client_id)
        }, 404

    # Initialize client template and fill sessions, exercises and check ins as we go
    client_template = ClientTemplate(
        name=coach_template.name, start_date=str(date.today()), user_id=client_id, completed=False, sessions=[]
    )

    # Iterate through sessions and create client_sessions, and client_exercises from them
    for session in sessions:
        coach_session = CoachSession.query.filter_by(id=session['id'], coach_template_id=coach_template_id).first()
        if coach_session == None:
            return {
                "error": "No coach_session found with session id: " + str(session['id']) + " and template id: " + str(coach_template_id)
            }, 404

        # Initialize a client session and fill with client_exercises
        client_session = ClientSession(
            name=coach_session.name, order=coach_session.order, completed=False, exercises=[], training_entries=[]
        )
        for coach_exercise in session['coach_exercises']:
            exercise = CoachExercise.query.filter_by(id=coach_exercise['id']).first()
            if exercise == None:
                return {
                    "error": "No exercise found with id: " + str(session['id'])
                }

            exercise_dump = coach_exercise_schema.dump(exercise)
            client_session.exercises.append(
                ClientExercise(
                    sets=coach_exercise['sets'], reps=coach_exercise['reps'], weight=coach_exercise['weight'],
                    category=exercise_dump['category'], name=exercise_dump['name'], order=exercise_dump['order']
                )
            )
        client_template.sessions.append(client_session)

    try:
        # create new template in CoachTemplate table
        db.session.add(client_template)
        db.session.commit()
    except Exception as e:
        print(e)
        return {
            "error": "Internal Server Error"
        }, 500
        raise

    db.session.refresh(client_template)

    result = client_template_schema.dump(client_template)

    return {
        "template": result
    }

@app.route("/client/session", methods=["GET"])
@http_guard(renew=True, nullable=False)
def getClientSession(token_claims):
    # Any logged in user should be able to access this method
    template_id = request.args.get('template_id')
    session_id = request.args.get('session_id')
    if template_id == None:
        return {
            "error": "No query parameter template_id found in request"
        }, 400
    if session_id == None:
        return {
            "error": "No query parameter session_id found in request"
        }, 400
    
    session = ClientSession.query.filter_by(id=session_id, client_template_id=template_id).first()
    if session == None:
        return {
            "error": "No session found with template_id: " + template_id + " and session_id: " + session_id
        }, 404

    sessionResult = client_session_schema.dump(session)

    return {
        "session": sessionResult
    }

@app.route("/client/session", methods=["POST"])
@http_guard(renew=True, nullable=False)
def createClientSession(token_claims):
    body = request.get_json(force=True)

    if 'client_template_id' not in body or 'name' not in body or 'exercises' not in body:
        return {
            "error": "Must specify client_template_id (int) name (string) and exercises (array)"
        }, 400

    # Check that a template with client_template_id exists
    client_template = ClientTemplate.query.filter_by(id=body['client_template_id']).first()
    if client_template == None:
        return {
            "error": "No client template found with template id: " + str(body['client_template'])
        }, 404

    # Find the next order for the client_session/training_entry based on the role of the requester
    next_order = findNextSessionOrder(body['client_template_id'])

    # Create a new client_session and insert it into the database
    client_session = ClientSession(
        name=body['name'], order=next_order, client_template_id=body['client_template_id'],
        exercises=[], training_entries=[]
    )

    # Iterate through the exercises and insert them as exercises if COACH or training_entries if CLIENT
    for exercise in body['exercises']:
        if token_claims['role'] == Role.COACH.name:
            client_session.completed = False
            client_session.exercises.append(
                ClientExercise(
                    sets=exercise['sets'], reps=exercise['reps'], weight=exercise['weight'],
                    category=exercise['category'], name=exercise['name'], order=exercise['order']
                )
            )
        else:
            client_session.completed = True
            client_session.training_entries.append(
                TrainingEntry(
                    sets=exercise['sets'], reps=exercise['reps'], weight=exercise['weight'],
                    category=exercise['category'], name=exercise['name'], order=exercise['order']
                )
            )

    # Add session into the database, refresh its contents and return as json
    try:
        # create new template in CoachTemplate table
        db.session.add(client_session)
        db.session.commit()
    except Exception as e:
        print(e)
        return {
            "error": "Internal Server Error"
        }, 500
        raise

    db.session.refresh(client_session)
    
    result = client_session_schema.dump(client_session)

    return {
        "session": result
    }

def findNextSessionOrder(client_template_id):
    """
    Finds the next order in a client templates session
    """
    next_order = db.session.query(func.max(ClientSession.order)).filter_by(client_template_id=client_template_id).scalar()
    
    if next_order == None:
        return 1

    return next_order + 1
