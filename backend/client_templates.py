from backend import db, app
from backend.middleware.middleware import http_guard
from backend.models.user import User, Role
from backend.models.client_templates import ClientTemplate, client_template_schema, client_template_schemas, ClientSession, client_session_schema, ClientExercise, client_exercise_schema, client_session_schemas, TrainingEntry, CheckIn, check_in_schema, check_in_schemas, training_log_schemas
from backend.models.coach_templates import CoachTemplate, CoachSession, CoachExercise, coach_exercise_schema
from backend.helpers.client_templates import findNextSessionOrder, setNonNullClientTemplateFields, setNonNullClientSessionFields, isSessionPresent, setNonNullCheckinFields, setUpdateSessionFields
from backend.helpers.general import makeTemplateSlugUnique, paginate
from backend.helpers.imgur import addImage
from flask import request
from sqlalchemy.orm import load_only, Load, subqueryload
from datetime import datetime as dt
from datetime import date, timedelta
from slugify import slugify
import json

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
    if 'sessions' not in body or 'template_id' not in body or 'client_id' not in body or 'role' not in body:
        return {
            "error": "Need to specify a valid template_id (int), client_id (int), sessions (array), and role (enum)"
        }, 400
    template_id = body['template_id']
    client_id = body['client_id']
    sessions = body['sessions']
    if len(sessions) <= 0:
        return {
            "error": "Length of sessions supplied is 0"
        }, 400

    # Grab a coach or client template depending on the role specified
    template = None

    if body['role'] == Role.COACH.name:
        template = CoachTemplate.query.filter_by(id=template_id).first()
        if template == None:
            return {
                "error": "No coach template found with coach_template_id: " + str(template_id)
            }, 404
    elif body['role'] == Role.CLIENT.name:
        template = ClientTemplate.query.filter_by(id=template_id).first()
        if template == None:
            return {
                "error": "No client template found with client_template_id: " + str(template_id)
            }
    else:
        return {
            "error": "Parameter role should be either COACH or CLIENT"
        }, 400

    # Grab the user with the client id
    client = User.query.filter_by(id=client_id).first()
    if client == None:
        return {
            "error": "No user found with user_id: " + str(client_id)
        }, 404

    # Slugify the coach template name and make it unique. Making it unique checks for an existing client template slug and increments
    # the count, adds to end of slug if one exists
    client_template_slug = makeTemplateSlugUnique(ClientTemplate, slugify(template.name + "-" + client.first_name + "-" + client.last_name))

    # Initialize client template and fill sessions, exercises and check ins as we go
    client_template = ClientTemplate(
        name=template.name, slug=client_template_slug, start_date=str(date.today()), user_id=client_id,
        completed=False, active=True, sessions=[]
    )
    # Set all other client templates if there are any to active false because we set this one as active
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
        template_session = None
        if body['role'] == Role.COACH.name:
            template_session = CoachSession.query.filter_by(id=session['id'], coach_template_id=template_id).first()
        else:
            template_session = ClientSession.query.filter_by(id=session['id'], client_template_id=template_id).first()
        
        if template_session == None:
            return {
                "error": "No session found with session id: " + str(session['id']) + " and template id: " + str(template_id)
            }, 404

        # Initialize a client session and fill with client_exercises, we re-use the coach session slug as we know it will be unique within the template
        client_session = ClientSession(
            name=template_session.name, slug=template_session.slug, order=template_session.order, completed=False, exercises=[], training_entries=[]
        )
        for exercise in session['exercises']:
            template_exercise = None

            if body['role'] == Role.COACH.name:
                template_exercise = CoachExercise.query.filter_by(id=exercise['id']).first()
            else:
                template_exercise = ClientExercise.query.filter_by(id=exercise['id']).first()

            if template_exercise == None:
                return {
                    "error": "No exercise found with id: " + str(exercise['id'])
                }

            exercise_dump = None
            if body['role'] == Role.COACH.name:
                exercise_dump = coach_exercise_schema.dump(template_exercise)
            else:
                exercise_dump = client_exercise_schema.dump(template_exercise)
            
            client_session.exercises.append(
                ClientExercise(
                    sets=exercise['sets'], reps=exercise['reps'], weight=exercise['weight'],
                    category=exercise_dump['category'], name=exercise_dump['name'], order=exercise_dump['order']
                )
            )
        client_template.sessions.append(client_session)

    # Create the check-in date by adding number of total sessions (as days) to todays date
    check_in_start_date = date.today()
    check_in_end_date = check_in_start_date + timedelta(days=len(client_template.sessions))
    client_check_in = CheckIn(
        completed=False, start_date=check_in_start_date.strftime(DATE_FORMAT),
        end_date=check_in_end_date.strftime(DATE_FORMAT), coach_viewed=False
    )
    client_template.check_in = client_check_in

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

    # update the session exercises and/or training_entries
    client_session = setUpdateSessionFields(client_template, client_session, body)

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

@app.route("/client/trainingLog", methods=["GET"])
@http_guard(renew=True, nullable=False)
def getTrainingLog(token_claims):
    client_id = request.args.get('client_id')

    if client_id == None:
        return {
            "error": "No query parameter client_id found in query parameter"
        }, 400

    # Grab all templates belonging to the client, order templates descending by start_date
    client_templates = ClientTemplate.query.filter(ClientTemplate.user_id == client_id).order_by(ClientTemplate.start_date.desc()).all()

    sessions = []

    for client_template in client_templates:
        # Grab all completed sessions belonging to the template
        client_sessions = ClientSession.query.filter(
            ClientSession.client_template_id == client_template.id, ClientSession.completed == True
        ).order_by(ClientSession.completed_date.desc()).all()

        sessions = sessions + client_sessions

    sessions = sorted(sessions, key=lambda k: k.completed_date, reverse=True)

    sessions_result = training_log_schemas.dump(sessions)

    # Paginate the results if pagination is specified
    page_size = request.args.get('page_size')
    page = request.args.get('page')
    if page_size != None and page != None:
        paginated_sessions, current_page, end_page = paginate(sessions_result, int(page), int(page_size))
        return {
            "current_page": current_page,
            "end_page": end_page,
            "sessions": paginated_sessions
        }

    return {
        "sessions": sessions_result
    }

@app.route("/checkin", methods=["GET"])
@http_guard(renew=True, nullable=False)
def getCheckin(token_claims):
    if token_claims['role'] == Role.COACH.name:
        checkin_id = request.args.get('checkin_id')

        if checkin_id == None:
            return {
            "error": "checkin_id not found in query parameter, checkin_id must be passed when a coach calls this endpoint"
        }, 400

        # get the checkin from the Checkins table with given checkin_id
        checkin = CheckIn.query.filter_by(id=checkin_id).first()
    else:
        client_id = request.args.get('client_id')

        if client_id == None:
            return {
            "error": "client_id not found in query parameter, client_id must be passed when a client calls this endpoint"
        }, 400
        # get active client template that belongs to this client_id
        template = ClientTemplate.query.filter(ClientTemplate.user_id==client_id, ClientTemplate.active==True).first()

        if template == None:
            return {
                "error": "No active template found with client_id: " + client_id
            }, 404
        # get checkin using the client_template_id
        checkin = CheckIn.query.filter_by(client_template_id=template.id).first()

    if checkin == None:
            return {
            "error": "No checkin found with the supplied parameter"
        }, 404
    
    # format the checkin_start_date and checkin_end_date so that we can compare them to the session_completed_date
    checkin_start_date = dt.strptime(str(checkin.start_date), '%Y-%m-%d')

    # get the client template that the given checkin_id corresponds to
    client_template = ClientTemplate.query.filter_by(id=checkin.client_template_id).first()
    if client_template == None:
        return {
        "error": "No client template found with supplied checkin_id"
    }, 404

    # this array will store the sessions that were completed within the span of the given checkin's start and end dates
    valid_sessions = []

    # loop through every session belonging to the client_template corresponding to the given checkin_id
    for session in client_template.sessions:
        # format session_completed_date only if the session is completed
        if session.completed == True:
            session_completed_date = dt.strptime(str(session.completed_date), '%Y-%m-%d')
        # if a session is incomplete or if a session has been completed after the start date of this checkin, return this session (valid session)
        if session.completed == False or session_completed_date > checkin_start_date:
            valid_sessions.append(session)
  
    checkin_result = check_in_schema.dump(checkin)
    session_result = client_session_schemas.dump(valid_sessions)

    return {
        "template_name": client_template.name,
        "check_in": checkin_result,
        "sessions": session_result
    }

@app.route("/checkins", methods=["GET"])
@http_guard(renew=True, nullable=False)
def getCheckins(token_claims):
    if token_claims['role'] != Role.COACH.name:
        return {
            "error": "User must be of type COACH to call endpoint"
        }, 401

    try:
        # Grab all completed check_ins who's end_date is before todays date. Order this descending so the most recent one is viewed
        completed_check_ins = CheckIn.query.filter(CheckIn.end_date <= date.today().strftime(DATE_FORMAT), CheckIn.completed == True).order_by(CheckIn.end_date.desc()).all()

        # Grab all noncompleted check_ins whos end_date is before todays date. Order this ascending so the oldest one is viewed
        noncompleted_check_ins = CheckIn.query.filter(CheckIn.end_date <= date.today().strftime(DATE_FORMAT), CheckIn.completed == False).order_by(CheckIn.end_date.desc()).all()

        completed_check_ins_result = check_in_schemas.dump(completed_check_ins)
        noncompleted_check_ins_result = check_in_schemas.dump(noncompleted_check_ins)

        return {
            "completed": completed_check_ins_result,
            "uncompleted": noncompleted_check_ins_result
        }
    except Exception as e:
        print(e)
        return {
            "error": "Internal Server Error"
        }, 500
        
@app.route("/client/checkins", methods=["GET"])
@http_guard(renew=True, nullable=False)
def getClientCheckins(token_claims):
    client_id = request.args.get('client_id')
    if client_id == None:
        return {
            "error": "No query parameter client_id found in request"
        }, 400
    # get the client_templates that this client has been assigned to (past or present), given the client_id
    client_templates = ClientTemplate.query.filter_by(user_id=client_id).all()

    if client_templates == None:
        return {
        "error": "No client_templates found with supplied client_id"
        }, 404

    complete_checkins = []
    incomplete_checkins = []
    # for each client_template, get the corresponding checkin
    for template in client_templates:
        # get checkin with the given client_template_id
        checkin = CheckIn.query.filter_by(client_template_id=template.id).first()
        # this means that the client_template was made without a checkin
        if checkin == None:
            continue
        # only include checkins that ended today or before today
        today = dt.today().strftime('%Y-%m-%d')
        if checkin.end_date <= today:
            if checkin.completed == True:
                complete_checkins.append(checkin)
            else:
                incomplete_checkins.append(checkin)

    # sort the completed checkins by start_date
    complete_checkins = sorted(complete_checkins, key=lambda k: k.start_date, reverse=True)
    # sort the incompleted checkins by start_date
    incomplete_checkins = sorted(incomplete_checkins, key=lambda k: k.start_date, reverse=True)

    complete_checkin_results = check_in_schemas.dump(complete_checkins)
    incomplete_checkin_results = check_in_schemas.dump(incomplete_checkins)

    return {
        "completed": complete_checkin_results,
        "uncompleted": incomplete_checkin_results
    }

@app.route("/submitCheckin", methods=["PUT"])
@http_guard(renew=True, nullable=False)
def submitCheckin(token_claims):
    try:
        form = request.form['body']
        body = json.loads(form)
    except Exception as e:
        body = request.get_json(force=True)

    if 'sessions' not in body and 'check_in' not in body:
        return {
            "error": "Must have either 'sessions', 'check_in' or both in request"
        }, 404

    if 'sessions' in body:
        client_sessions = []
        # Iterate through sessions and update client_sessions and client_exercises
        for session in body['sessions']:
            client_session = ClientSession.query.filter_by(id=session['id']).first()
            if client_session == None:
                return {
                    "error": "No client_session found with session id: " + str(session['id'])
                }, 404

            # Update the session metadata that the request has asked for, handle updating client_exercises separately
            setNonNullClientSessionFields(client_session, session)
            # get the client_template this session belongs to
            client_template = ClientTemplate.query.filter_by(id=client_session.client_template_id).first()
            # update the exercises and training_entries
            client_session = setUpdateSessionFields(client_template, client_session, session)
            client_sessions.append(client_session)
            try:
                db.session.commit()
                db.session.refresh(client_session)
            except Exception as e:
                print(e)
                return {
                    "error": "Internal Server Error"
                }, 500
                raise
        client_session_results = client_session_schemas.dump(client_sessions)
    else:
        client_session_results = None
    
    # update the check_in fields as necessary
    if 'check_in' in body:
        checkin = CheckIn.query.filter_by(id=body['check_in']['id']).first()
        setNonNullCheckinFields(checkin, body['check_in'])

        # post an image to imgur if this endpoint is not being run by a test
        create_image = True
        if 'test' in body:
            if body['test'] == True:
                create_image = False
        
        if create_image:
            # get the album the image needs to be added to
            template = ClientTemplate.query.filter_by(id=checkin.client_template_id).first()
            if template == None:
                return {
                    "error": "No template found with checkin_id: " + str(body['check_in']['id'])
                }, 404
            user = User.query.filter_by(id=template.user_id).first()
            if user == None:
                return {
                    "error": "No user found with client_template_id: " + str(body['check_in']['id'])
                }, 404
            album = user.album_deletehash              
            if 'front' in request.files:
                front = request.files['front']
                image_link, code = addImage(album, front)
                if code != 200:
                    print("Failed to add front image to imgur album for user with code: " + str(code))
                    return {
                        "error": "Internal Server Error"
                    }, 500
                checkin.front = image_link
            if 'back' in request.files:
                back = request.files['back']
                image_link, code = addImage(album, back)
                if code != 200:
                    print("Failed to add back image to imgur album for user with code: " + str(code))
                    return {
                        "error": "Internal Server Error"
                    }, 500
                checkin.back = image_link
            if 'side_a' in request.files:
                side_a = request.files['side_a']
                image_link, code = addImage(album, side_a)
                if code != 200:
                    print("Failed to add side_a image to imgur album for user with code: " + str(code))
                    return {
                        "error": "Internal Server Error"
                    }, 500
                checkin.side_a = image_link
            if 'side_b' in request.files:
                side_b = request.files['side_b']
                image_link, code = addImage(album, side_b)
                if code != 200:
                    print("Failed to add side_b image to imgur album for user with code: " + str(code))
                    return {
                        "error": "Internal Server Error"
                    }, 500
                checkin.side_b = image_link

    # set user.check_in to true only if a client has accessed this endpoint
    if token_claims['role'] == Role.CLIENT.name:
        user.check_in = True

    try:
        db.session.commit()
        db.session.refresh(checkin)
        db.session.refresh(user)
    except Exception as e:
        print(e)
        return {
            "error": "Internal Server Error here"
        }, 500
        raise
    check_in_result = check_in_schema.dump(checkin)
    
    return {
        "check_in": check_in_result,
        "sessions": client_session_results
    }
