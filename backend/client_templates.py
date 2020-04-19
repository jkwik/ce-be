from backend import db, app
from backend.middleware.middleware import http_guard
from backend.models.user import User, Role
from backend.models.client_templates import ClientTemplate, client_template_schema, client_template_schemas, ClientSession, client_session_schema, ClientExercise, TrainingEntry, CheckIn, check_in_schema
from backend.models.coach_templates import CoachTemplate, CoachSession, CoachExercise, coach_exercise_schema
from backend.helpers.client_templates import findNextSessionOrder, setNonNullClientTemplateFields, setNonNullClientSessionFields, isSessionPresent
from backend.helpers.general import makeTemplateSlugUnique
from flask import request
from sqlalchemy.orm import load_only, Load, subqueryload
from datetime import datetime as dt
from datetime import date, timedelta
from slugify import slugify

DATE_FORMAT = '%Y-%m-%d'

@app.route("/client/templates", methods=["GET"])
@http_guard(renew=True, nullable=False)
def getClientTemplates(token_claims):
    user_id = request.args.get('user_id')
    if user_id == None:
        return {
            "error": "No query parameter user_id found in request"
        }, 400

    templates = db.session.query(
        ClientTemplate.id, ClientTemplate.name, ClientTemplate.slug, ClientTemplate.start_date,
        ClientTemplate.end_date, ClientTemplate.user_id, ClientTemplate.completed, ClientTemplate.active
    ).filter(ClientTemplate.user_id == user_id)

    result = client_template_schemas.dump(templates)

    return {
        "templates": result
    }

@app.route("/client/template", methods=["GET"])
@http_guard(renew=True, nullable=False)
def getClientTemplate(token_claims):
    # Any logged in user should be able to access this method
    id = request.args.get('client_template_id')
    slug = request.args.get('client_template_slug')

    if (id == None and slug == None) or (id != None and slug != None):
        return {
            "error": "Need to pass EITHER client_template_id or client_template_slug as a request parameter"
        }, 400

    template = ClientTemplate()
    if id != None:
        template = ClientTemplate.query.filter_by(id=id).first()
    else:
        template = ClientTemplate.query.filter_by(slug=slug).first()

    templateResult = client_template_schema.dump(template)

    return templateResult

@app.route("/client/template/active", methods=["GET"])
@http_guard(renew=True, nullable=False)
def getActiveClientTemplate(token_claims):
    # Any logged in user should be able to access this method
    user_id = request.args.get('user_id')
    if user_id == None:
        return {
            "error": "No query parameter user_id found in request"
        }, 400

    # We want to grab all active templates so that we can check that there is only one
    templates = ClientTemplate.query.filter_by(user_id=user_id, active=True).all()
    if len(templates) != 1:
        return {
            "error": "More than 1 active template found for client"
        }, 409

    templateResult = client_template_schema.dump(templates[0])

    return templateResult

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

    # Slugify the coach template name and make it unique. Making it unique checks for an existing client template slug and increments
    # the count, adds to end of slug if one exists
    client_template_slug = makeTemplateSlugUnique(ClientTemplate, slugify(coach_template.name + "-" + client.first_name + "-" + client.last_name))

    # Initialize client template and fill sessions, exercises and check ins as we go
    client_template = ClientTemplate(
        name=coach_template.name, slug=client_template_slug, start_date=str(date.today()), user_id=client_id,
        completed=False, active=True, sessions=[], check_ins=[]
    )
    # Set all other client templates if there are any to active false
    try:
        db.session.execute('UPDATE "Client_templates" SET active=False where user_id={}'.format(client_id))
        db.session.commit()
    except Exception as e:
        print(e)
        return {
            "error": "Internal Server Error"
        }, 500

    # Iterate through sessions and create client_sessions, and client_exercises from them
    for session in sessions:
        coach_session = CoachSession.query.filter_by(id=session['id'], coach_template_id=coach_template_id).first()
        if coach_session == None:
            return {
                "error": "No coach_session found with session id: " + str(session['id']) + " and template id: " + str(coach_template_id)
            }, 404

        # Initialize a client session and fill with client_exercises, we re-use the coach session slug as we know it will be unique within the template
        client_session = ClientSession(
            name=coach_session.name, slug=coach_session.slug, order=coach_session.order, completed=False, exercises=[], training_entries=[]
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

    # For each check_in date in the body, create a new check_in object for the template
    if 'check_ins' in body:
        for i, check_in_start_date in enumerate(body['check_ins']):
            client_check_in = CheckIn(completed=False)
            parsed_start_date = None

            # Sanity check the format of the start_date by parsing it
            try:
                parsed_start_date = dt.strptime(check_in_start_date, DATE_FORMAT)
            except Exception as e:
                return {
                    "Expected check_in dates to be of the format YYYY-MM-DD, not: " + check_in_start_date
                }, 400
            client_check_in.start_date = str(parsed_start_date)

            # The end date for each checkin will be the day before the next check_in starts if it isn't the last one
            if i != len(body['check_ins']) - 1:
                try:
                    parsed_next_start_date = dt.strptime(body['check_ins'][i+1], DATE_FORMAT)
                    client_check_in.end_date = parsed_next_start_date - timedelta(days=1)
                except Exception as e:
                    return {
                        "Expected check_in dates to be of the format YYYY-MM-DD, not: " + body['check_ins'][i+1]
                    }
            else:
                client_check_in.end_date = None
            
            client_template.check_ins.append(client_check_in)

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

    return result

@app.route("/client/template", methods=["PUT"])
@http_guard(renew=True, nullable=False)
def updateClientTemplate(token_claims):
    body = request.get_json(force=True)

    if 'id' not in body:
        return {
            "error": "No parameter id found in request body"
        }, 400

    # Get the client template
    client_template = ClientTemplate.query.get(body['id'])
    if client_template == None:
        return {
            "error": "No client template found with id: " + str(body['id'])
        }, 404

    # Set all client_templates belonging to the user to active=False so that we can set the updated template to active=True
    try:
        db.session.execute('UPDATE "Client_templates" SET active=False where user_id={}'.format(body['user_id']))
        db.session.commit()
    except Exception as e:
        print(e)
        return {
            "error": "Internal Server Error"
        }, 500

    # Set all fields in client_template that were present in the body
    setNonNullClientTemplateFields(client_template, body)

    # Set the client_template to be the active template
    client_template.active = True

    # Iterate through the client_sessions and for each session, check if it is present in the body, if it is, then update the session
    # and insert it into client_sessions. If it isn't present, then don't insert into client_sessions
    if 'sessions' in body:
        client_sessions = []
        for client_session in client_template.sessions:
            present, index = isSessionPresent(client_session, body['sessions'])
            if present:
                setNonNullClientSessionFields(client_session, body['sessions'][index])
                client_sessions.append(client_session)

        client_template.sessions = client_sessions
                
    try:
        db.session.commit()
        db.session.refresh(client_template)
    except Exception as e:
        print(e)
        return {
            "error": "Internal Server Error"
        }, 500
        raise

    return client_template_schema.dump(client_template)

@app.route("/client/session", methods=["GET"])
@http_guard(renew=True, nullable=False)
def getClientSession(token_claims):
    # Any logged in user should be able to access this method
    session_id = request.args.get('client_session_id')
    template_slug = request.args.get('client_template_slug')
    session_slug = request.args.get('client_session_slug')

    if (session_id == None and template_slug == None and session_slug == None) or (session_id != None and template_slug != None and session_slug != None):
        return {
            "error": "Pass EITHER client_session_id OR client_template_slug + client_session_slug in the request parameter"
        }, 400
    
    if session_id == None:
        if (template_slug != None and session_slug == None) or (template_slug == None and session_slug != None) or (template_slug == None and session_slug == None):
            return {
                "error": "Pass EITHER client_session_id OR client_template_slug + client_session_slug in the request parameter"
            }, 400
    
    session = ClientSession()
    if session_id != None:
        session = ClientSession.query.filter_by(id=session_id).first()
    else:
        client_template = ClientTemplate.query.filter_by(slug=template_slug).first()
        if client_template == None:
            return {
                "error": "No client template found with slug: " + template_slug
            }, 404
        session = ClientSession.query.filter_by(slug=session_slug, client_template_id=client_template.id).first()

    if session == None:
        return {
            "error": "No client session found"
        }, 404

    sessionResult = client_session_schema.dump(session)

    return sessionResult

@app.route("/client/session/next", methods=["GET"])
@http_guard(renew=True, nullable=False)
def getNextClientSession(token_claims):
    # Any logged in user should be able to access this method
    client_id = request.args.get('client_id')

    if client_id == None:
        return {
            "error": "No query parameter client_id found in request"
        }, 400
    # get the active tempalte
    template = ClientTemplate.query.filter_by(user_id=client_id, active=True).first()
    if template == None:
        return {
            "error": "No active template found with client_id: " + client_id
        }, 404

    for session in template.sessions:
        if session.completed == False:
            nextSession = session
            break

    result = client_session_schema.dump(nextSession)

    return result

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

    # Check for duplicate session name
    existing_session = ClientSession.query.filter_by(client_template_id=client_template.id, name=body['name']).first()
    if existing_session != None:
        return {
            "error": "Duplicate session name found in template: " + body['name']
        }, 409

    # Set all client_templates belonging to the user to active=False so that we can set the corresponding template for this session to active=True
    try:
        db.session.execute('UPDATE "Client_templates" SET active=False where user_id={}'.format(client_template.user_id))
        db.session.commit()
    except Exception as e:
        print(e)
        return {
            "error": "Internal Server Error"
        }, 500

    # Set the current client_template to active=True
    client_template.active = True

    # Find the next order for the client_session/training_entry based on the role of the requester
    next_order = findNextSessionOrder(body['client_template_id'])

    # Slugify the session name
    session_slug = slugify(body['name'])

    # Create a new client_session and insert it into the database
    client_session = ClientSession(
        name=body['name'], slug=session_slug, order=next_order, client_template_id=body['client_template_id'],
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

    return result

@app.route("/client/session", methods=["PUT"])
@http_guard(renew=True, nullable=False)
def updateClientSession(token_claims):
    body = request.get_json(force=True)

    if 'id' not in body:
        return {
            "error": "No id parameter found in request body"
        }, 400

    client_session = ClientSession.query.get(body['id'])
    if client_session == None:
        return {
            "error": "No client session found with supplied id"
        }, 404

    client_template = ClientTemplate.query.get(client_session.client_template_id)
    if client_template == None:
        return {
            "error": "No client template found with id: " + str(client_session.client_template_id)
        }, 404

    # Set all client_templates belonging to the user to active=False so that we can set the corresponding template for this session to active=True
    try:
        db.session.execute('UPDATE "Client_templates" SET active=False where user_id={}'.format(client_template.user_id))
        db.session.commit()
    except Exception as e:
        print(e)
        return {
            "error": "Internal Server Error"
        }, 500

    # Set the current client_template to active=True
    client_template.active = True

    # Update the session metadata that the request has asked for, handle updating client_exercises separately
    setNonNullClientSessionFields(client_session, body)

    # Update the client_exercises by replacing the ones in client_session with the ones passed in the request
    if 'exercises' in body:
        client_exercises = []
        for client_exercise in body['exercises']:
            client_exercises.append(
                ClientExercise(
                    name=client_exercise['name'], category=client_exercise['category'], sets=client_exercise['sets'],
                    reps=client_exercise['reps'], weight=client_exercise['weight'], order=client_exercise['order']
                )
            )
        client_session.exercises = client_exercises
    
    # Update the training_entries by replacing the ones in client_session with the ones passed in the request
    if 'training_entries' in body:
        client_training_entries = []
        for client_training_entry in body['training_entries']:
            client_training_entries.append(
                TrainingEntry(
                    name=client_training_entry['name'], category=client_training_entry['category'], sets=client_training_entry['sets'],
                    reps=client_training_entry['reps'], weight=client_training_entry['weight'], order=client_training_entry['order']
                )
            )
        client_session.training_entries = client_training_entries

    try:
        db.session.commit()
        db.session.refresh(client_session)
    except Exception as e:
        print(e)
        return {
            "error": "Internal Server Error"
        }, 500
        raise

    return client_session_schema.dump(client_session)

@app.route("/checkin", methods=["GET"])
@http_guard(renew=True, nullable=False)
def getCheckin(token_claims):
    checkin_id = request.args.get('checkin_id')
    if checkin_id == None:
        return {
            "error": "No query parameter checkin_id found in request"
        }, 400
    # get the checkin from the Checkins table with given checkin_id
    checkin = CheckIn.query.filter_by(id=checkin_id).first()
    if checkin == None:
        return {
        "error": "No checkin found with supplied checkin_id"
    }, 404

    split_end_date = checkin.end_date.split('-')
    split_start_date = checkin.start_date.split('-')
    checkin_end_date = date(int(split_end_date[0]), int(split_end_date[1]), int(split_end_date[2]))
    checkin_start_date = date(int(split_start_date[0]), int(split_start_date[1]), int(split_start_date[2]))

    print(checkin_end_date)
    print(checkin_start_date)
    # get the client tempalte that the given checken corresponds to
    client_template = ClientTemplate.query.filter_by(id=checkin.client_template_id).first()
    if client_template == None:
        return {
        "error": "No client template found with supplied checkin_id"
    }, 404
    
    # for session in client_template.sessions:
    #     session_completed_date = session.completed_date
    #     if session.completed_date
  

    result = check_in_schema.dump(checkin)

    return {
        "checkin": result
    }
