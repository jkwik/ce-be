from backend import app, db
from backend.middleware.middleware import http_guard
from flask import request, session
from sqlalchemy.exc import IntegrityError
from sqlalchemy import func
# from sqlalchemy.orm import defer, joinedload, load_only, subqueryload, lazyload
from backend.models.user import Role
from backend.models.coach_templates import CoachTemplate, coach_template_schema, coach_template_schemas, coach_session_schema, coach_session_schemas, Exercise, coach_exercise_schema, CoachSession, coach_exercise_schemas, CoachExercise, exercise_schemas, exercise_schema

# Iteration 2
# Return a list of templates the coach has created from the Templates table
@app.route("/coach/templates", methods=['GET'])
@http_guard(renew=True, nullable=False)
def coachTemplates(token_claims):
    # check that the user's role is COACH
    if token_claims['role'] != Role.COACH.name:
        return {
            "error": "Expected role of COACH"
    }, 400

    templates = CoachTemplate.query.all()

    if templates == None:
        return {
            "error": "There are no Coach_templates"
        }

    result = coach_template_schemas.dump(templates)

    return {
        "templates": result
    }

# Return the coach_template from coach_template_id passed in
@app.route("/coach/template", methods=['GET'])
@http_guard(renew=True, nullable=False)
def coachTemplate(token_claims):
    # check that the user's role is COACH
    if token_claims['role'] != Role.COACH.name:
        return {
            "error": "Expected role of COACH"
    }, 400

    id = request.args.get('coach_template_id')
    
    if id == None:
        return {
            "error": "No query parameter id found in request"
        }, 400
    
    template = CoachTemplate.query.filter_by(id=id).first()

    if template == None:
        return {
            "error": "Coach_template not found with given id: " + id
        }

    result = coach_template_schema.dump(template)
    
    return result


# Return the coach_session from the coach_session_id passed in
@app.route("/coach/session", methods=['GET'])
@http_guard(renew=True, nullable=False)
def coachSession(token_claims):
    # check that the user's role is COACH
    if token_claims['role'] != Role.COACH.name:
        return {
            "error": "Expected role of COACH"
    }, 400

    id = request.args.get('coach_session_id')
    if id == None:
        return {
            "error": "No query parameter id found in request"
        }, 400
    
    session = CoachSession.query.filter_by(id=id).first()

    if session == None:
        return {
            "error": "Coach_session not found with given id: " + id
        }

    result = coach_session_schema.dump(session)
    
    return result


# Return the coach_exercise from the coach_exercise_id passed in
@app.route("/coach/exercise", methods=['GET'])
@http_guard(renew=True, nullable=False)
def coachExercise(token_claims):
    # check that the user's role is COACH
    if token_claims['role'] != Role.COACH.name:
        return {
            "error": "Expected role of COACH"
    }, 400

    id = request.args.get('coach_exercise_id')

    if id == None:
        return {
            "error": "No query parameter id found in request"
        }, 400
    
    exercise = CoachExercise.query.filter_by(id=id).first()

    if exercise == None:
        return {
            "error": "Coach_exercise not found with given id: " + id
        }, 404

    result = coach_exercise_schema.dump(exercise)

    return result


# Return all exercises from the Exercises Table
@app.route("/exercises", methods=['GET'])
@http_guard(renew=True, nullable=False)
def exercises(token_claims):
    # check that the user's role is COACH
    if token_claims['role'] != Role.COACH.name:
        return {
            "error": "Expected role of COACH"
    }, 400
    
    exercises = Exercise.query.all()

    if exercises == None:
        return {
            "error": "No exercises have been created yet"
        }, 404

    result = exercise_schemas.dump(exercises)

    return {
        "exercises": result
    }


@app.route("/coach/template", methods=['POST'])
@http_guard(renew=True, nullable=False)
def createTemplate(token_claims):
    # check that the user's role is COACH
    if token_claims['role'] != Role.COACH.name:
        return {
            "error": "Expected role of COACH"
        }, 400

    body = request.get_json(force=True)

    if 'name' not in body:
        return {
            "error": "Must specify name (string))"
        }, 400
    
    # check if template name is available, no duplicates allowed
    check_duplicate = CoachTemplate.query.filter_by(name=body['name']).first()

    if check_duplicate:
        return {
            "error": "Template name already exists"
        }, 400
    
    
    new_template = CoachTemplate(name=body['name'])
    
    try:
        # create new template in CoachTemplate table
        db.session.add(new_template)
        db.session.commit()
    except Exception as e:
        return {
            "error": "Internal Server Error"
        }, 500
        raise

    # retrieve created template
    template = CoachTemplate.query.filter_by(name=body['name']).first()

    result = coach_template_schema.dump(template)
    
    return result


@app.route("/coach/session", methods=['POST'])
@http_guard(renew=True, nullable=False)
def createSession(token_claims):
    if token_claims['role'] != Role.COACH.name:
        return {
            "error": "Expected role of COACH"
        }, 400

    body = request.get_json(force=True)

    if 'coach_template_id' not in body or 'name' not in body:
        return {
            "error": "Must specify coach_template_id (integer) and name (string))"
        }, 400
    
    # check if template name is available, no duplicates allowed
    check_duplicate = CoachSession.query.filter_by(name=body['name'], coach_template_id=body['coach_template_id']).first()

    if check_duplicate:
        return {
            "error": "Session name already exists for this template"
        }, 400
    
    # find current max order value for sessions belonging to the passed in coach_template_id
    max_order = db.session.query(func.max(CoachSession.order)).filter_by(coach_template_id=body['coach_template_id']).scalar()
    
    # if no sessions exist for this template, the newly created session will have order = 1
    if max_order is None:
        max_order = 1
    else:
        # increment the order by 1
        max_order += 1

    # create the new session with name, coach_template_id, and order
    new_session = CoachSession(name=body['name'], coach_template_id=body['coach_template_id'], order=max_order)
    
    try:
        # create new template in CoachTemplate table
        db.session.add(new_session)
        db.session.commit()
    except Exception as e:
        return {
            "error": "Internal Server Error"
        }, 500
        raise

    # retrieve created session
    session = CoachSession.query.filter_by(name=body['name'], coach_template_id=body['coach_template_id']).first()

    result = coach_session_schema.dump(session)
    
    return result


@app.route("/coach/exercise", methods=['POST'])
@http_guard(renew=True, nullable=False)
def createCoachExercise(token_claims):
    if token_claims['role'] != Role.COACH.name:
        return {
            "error": "Expected role of COACH"
        }, 400

    body = request.get_json(force=True)
    
    if 'coach_session_id' not in body or 'exercise_id' not in body:
        return {
            "error": "Must specify coach_session_id (integer) and exercise_id (integer)"
        }, 400 
        
    # find current max order value for sexercise belonging to the passed in coach_session_id
    max_order = db.session.query(func.max(CoachExercise.order)).filter_by(coach_session_id=body['coach_session_id']).scalar()

    # if no sessions exist for this template, the newly created session will have order = 1
    if max_order is None:
        max_order = 1
    else:
        # increment the order by 1
        max_order += 1

    # create the new coach exercise with coach_exercise_id, coach_session_id, and order
    new_exercise = CoachExercise(exercise_id=body['exercise_id'], coach_session_id=body['coach_session_id'], order=max_order)
    
    try:
        # create new template in CoachTemplate table
        db.session.add(new_exercise)
        db.session.commit()
    except Exception as e:
        return {
            "error": "Internal Server Error"
        }, 500
        raise

    # retrieve created exercises
    exercises = CoachExercise.query.filter_by(coach_session_id=body['coach_session_id'])

    result = coach_exercise_schemas.dump(exercises)
    
    return {
        "session_exercises": result
    }

@app.route("/exercise", methods=['POST'])
@http_guard(renew=True, nullable=False)
def createExercise(token_claims):
    if token_claims['role'] != Role.COACH.name and token_claims['role'] != Role.CLIENT.name:
        return {
            "error": "Expected role of COACH or CLIENT"
        }, 400

    body = request.get_json(force=True)
    
    if 'name' not in body or 'category' not in body:
        return {
            "error": "Must specify exercise name (string) and category (string)"
        }, 400    
    # create the new exercise with name and category
    new_exercise = Exercise(name=body['name'], category=body['category'])
    
    try:
        # create new template in CoachTemplate table
        db.session.add(new_exercise)
        db.session.commit()
    except Exception as e:
        return {
            "error": "Internal Server Error"
        }, 500
        raise

    # retrieve created exercises
    exercises = Exercise.query.all()
    result = exercise_schemas.dump(exercises)
    
    return {
        "exercises": result
    }


@app.route("/coach/template/delete", methods=['PUT'])
@http_guard(renew=True, nullable=False)
def deleteTemplate(token_claims):
    if token_claims['role'] != Role.COACH.name:
        return {
            "error": "Expected role of COACH"
    }, 400

    body = request.get_json(force=True)
    id = body['coach_template_id']
    
    # check that the correct param is passed
    if id == None:
        return {
            "error": "No query parameter coach_template_id found in request"
        }, 400

    # grab table to be deleted
    template = CoachTemplate.query.filter_by(id=id).first()

    # check that table to delte actually exists
    if template == None:
        return {
            "error": "Coach_template not found with given id"
        }
    
    try:
        # Delete table from database
        CoachTemplate.query.filter_by(id=id).delete()
        db.session.commit()
    except Exception as e:
        return {
            "error": "Internal Server Error"
        }, 500
        raise

    return {
        "success": True
    }


@app.route("/coach/template", methods=['PUT'])
@http_guard(renew=True, nullable=False)
def updateTemplate(token_claims):
    if token_claims['role'] != Role.COACH.name:
        return {
            "error": "Expected role of COACH"
        }, 400

    body = request.get_json(force=True)

    if 'id' not in body or 'name' not in body or 'sessions' not in body:
        return {
            "error": "Must specify id (int) name (string) and sessions (array)"
        }, 400
    # grab the template being updated
    update_template = CoachTemplate.query.filter_by(id=body['id']).first()

    # check if coach wants to change the template name
    change_name = False
    # only change name if it is different than the name currently in the database
    if body['name'] != update_template.name:
        change_name = True

    # grab incoming session ids
    incoming_ids = []
    for val in body['sessions']:
        incoming_ids.append(val['id'])

    # Grab all the sessions belonging to the template being updated
    sessions = CoachSession.query.filter_by(coach_template_id=body['id'])

    try:
        # update template name if the coach requested it to be changed
        if change_name == True:
            update_template.name = body['name']
            db.session.commit()
        # update session in CoachSessions table
    except Exception as e:
        return {
            "error": "Internal Server Error"
        }, 500
        raise

    # For each session in the CoachSessions table belonging to this template, 
    for s in sessions:
        # if current_session_id is present in the array of sessions they’ve passed
        # Then update the order of that session
        if s.id in incoming_ids:
            # find the correct incoming order value to update this session.order
            for x in body['sessions']:
                if x['id'] == s.id:
                    s.order = x['order']
                    db.session.commit()
        # Else delete the current_session_id from the database
        else:
            try:
                # delete this session
                CoachSession.query.filter_by(id=s.id).delete()
                db.session.commit()
            except Exception as e:
                return {
                    "error": "Internal Server Error"
                }, 500
                raise

    
    template = CoachTemplate.query.filter_by(id=body['id']).first()
    result = coach_template_schema.dump(template)
    
    return result