from backend import app, db
from backend.middleware.middleware import http_guard
from flask import request, session
from sqlalchemy.exc import IntegrityError
from sqlalchemy import func
# from sqlalchemy.orm import defer, joinedload, load_only, subqueryload, lazyload
from backend.models.user import Role
from backend.models.coach_templates import CoachTemplate, coach_template_schema, coach_template_schemas, coach_session_schema, coach_session_schemas, Exercise, coach_exercise_schema, CoachSession, coach_exercise_schemas, CoachExercise, exercise_schemas, exercise_schema
from backend.helpers.coach_templates import setNonNullCoachSessionFields, isSessionPresent
from slugify import slugify

# Iteration 2
# Return a list of templates the coach has created from the Templates table
@app.route("/coach/templates", methods=['GET'])
@http_guard(renew=True, nullable=False)
def coachTemplates(token_claims):
    # check that the user's role is COACH
    if token_claims['role'] != Role.COACH.name:
        return {
            "error": "Expected role of COACH"
    }, 401

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
    }, 401

    id = request.args.get('coach_template_id')
    slug = request.args.get('coach_template_slug')
    
    if (id == None and slug == None) or (id != None and slug != None):
        return {
            "error": "Pass EITHER coach_template_id OR coach_template_slug in the request parameter"
        }, 400
    
    template = CoachTemplate()
    if id != None:        
        template = CoachTemplate.query.filter_by(id=id).first()
    else:
        template = CoachTemplate.query.filter_by(slug=slug).first()

    if template == None and id != None:
        return {
            "error": "Coach_template not found with given id: " + id
        }, 404
    elif template == None and slug != None:
        return {
            "error": "Coach_template not found with given slug: " + slug
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
        }, 401

    session_id = request.args.get('coach_session_id')
    template_slug = request.args.get('coach_template_slug')
    session_slug = request.args.get('coach_session_slug')

    if (session_id == None and template_slug == None and session_slug == None) or (session_id != None and template_slug != None and session_slug != None):
        return {
            "error": "Pass EITHER coach_session_id OR coach_template_slug + coach_session_slug in the request parameter"
        }, 400
    
    if session_id == None:
        if (template_slug != None and session_slug == None) or (template_slug == None and session_slug != None) or (template_slug == None and session_slug == None):
            return {
                "error": "Pass EITHER coach_session_id OR coach_template_slug + coach_session_slug in the request parameter"
            }, 400

    session = CoachSession()
    if session_id != None:
        session = CoachSession.query.filter_by(id=session_id).first()
    else:
        coach_template = CoachTemplate.query.filter_by(slug=template_slug).first()
        if coach_template == None:
            return {
                "error": "No coach template found with slug: " + template_slug
            }, 404
        session = CoachSession.query.filter_by(slug=session_slug, coach_template_id=coach_template.id).first()

    if session == None:
        return {
            "error": "No coach session found"
        }, 404

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
    }, 401

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
    }, 401
    
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
        }, 401

    body = request.get_json(force=True)

    if 'name' not in body:
        return {
            "error": "Must specify name (string))"
        }, 400

    if 'sessions' not in body:
        return {
            "error": "Must specify a session list with at least 1 session"
        }, 400
    
    # check if template name is available, no duplicates allowed
    check_duplicate = CoachTemplate.query.filter_by(name=body['name']).first()

    if check_duplicate:
        return {
            "error": "Template name already exists"
        }, 400
    
    # If the template name is free, then we create a slug from it
    template_slug = slugify(body['name'])
    
    new_template = CoachTemplate(name=body['name'], sessions=[], slug=template_slug)
    # Enter each session and its corresponding coach exercises into the template
    for session in body['sessions']:
        session_slug = slugify(session['name'])
        coach_session = CoachSession(
            name=session['name'], slug=session_slug, order=session['order'], coach_exercises=[]
        )
        for coach_exercise in session['coach_exercises']:
            # Check if the exercise_id was supplied, if not then create a new exercise using the category and name
            if 'exercise_id' not in coach_exercise:
                if 'category' not in coach_exercise or 'name' not in coach_exercise:
                    return {
                        "error": "Each coach_exercise needs to specify an exercise_id OR a category and name pair"
                    }, 400
                exercise = Exercise(category=coach_exercise['category'], name=coach_exercise['name'])
                db.session.add(exercise)
                try:
                    db.session.commit()
                    db.session.refresh(exercise)
                except Exception as e:
                    return {
                        "error": "Internal Server Error"
                    }, 500

                coach_session.coach_exercises.append(CoachExercise(
                    exercise_id=exercise.id, order=coach_exercise['order']
                ))
            else:
                coach_session.coach_exercises.append(CoachExercise(
                    exercise_id=coach_exercise['exercise_id'], order=coach_exercise['order']
                ))

        new_template.sessions.append(coach_session)
    
    try:
        # create new template in CoachTemplate table
        db.session.add(new_template)
        db.session.commit()
    except Exception as e:
        print(e)
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
        }, 401

    body = request.get_json(force=True)

    if 'coach_template_id' not in body or 'name' not in body:
        return {
            "error": "Must specify coach_template_id (integer) and name (string))"
        }, 400

    coach_template = CoachTemplate.query.get(body['coach_template_id'])
    if coach_template == None:
        return {
            "error": "No coach template found with the supplied coach_template_id"
        }, 404
    
    # Check for duplicate session name
    coach_session = CoachSession.query.filter_by(coach_template_id=coach_template.id, name=body['name']).first()
    if coach_session != None:
        return {
            "error": "Duplicate session name found"
        }, 409

    # find current max order value for sessions belonging to the passed in coach_template_id
    max_order = db.session.query(func.max(CoachSession.order)).filter_by(coach_template_id=body['coach_template_id']).scalar()
    
    # if no sessions exist for this template, the newly created session will have order = 1
    if max_order is None:
        max_order = 1
    else:
        # increment the order by 1
        max_order += 1

    # create a slug based on the session name
    session_slug = slugify(body['name'])

    # create the new session with name, coach_template_id, and order
    new_session = CoachSession(
        name=body['name'], slug=session_slug, coach_template_id=body['coach_template_id'],
        order=max_order, coach_exercises=[]
    )

    # Check if they passed in coach_exercises
    if 'coach_exercises' in body:
        for coach_exercise in body['coach_exercises']:
            # Check if the exercise_id was supplied, if not then create a new exercise using the category and name
            if 'exercise_id' not in coach_exercise:
                if 'category' not in coach_exercise or 'name' not in coach_exercise:
                    return {
                        "error": "Each coach_exercise needs to specify an exercise_id OR a category and name pair"
                    }, 400
                exercise = Exercise(category=coach_exercise['category'], name=coach_exercise['name'])
                db.session.add(exercise)
                try:
                    db.session.commit()
                    db.session.refresh(exercise)
                except Exception as e:
                    return {
                        "error": "Internal Server Error"
                    }, 500

                new_session.coach_exercises.append(CoachExercise(
                    exercise_id=exercise.id, order=coach_exercise['order']
                ))
            else:
                new_session.coach_exercises.append(CoachExercise(
                    exercise_id=coach_exercise['exercise_id'], order=coach_exercise['order']
                ))
    
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


@app.route("/exercise", methods=['POST'])
@http_guard(renew=True, nullable=False)
def createExercise(token_claims):
    if token_claims['role'] != Role.COACH.name and token_claims['role'] != Role.CLIENT.name:
        return {
            "error": "Expected role of COACH or CLIENT"
        }, 401

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
    }, 401

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
        }, 401

    body = request.get_json(force=True)

    if 'id' not in body:
        return {
            "error": "No parameter id found in request body"
        }, 400

    # grab the template being updated
    coach_template = CoachTemplate.query.filter_by(id=body['id']).first()

    # check if coach wants to change the template name
    # only change name if it is different than the name currently in the database
    if 'name' in body:
        if body['name'] != coach_template.name:
            coach_template.name = body['name']

    # Iterate through the coach_sessions and for each session, check if it is present in the body, if it is, then update the session
    # and insert it into coach_sessions. If it isn't present, then don't insert into coach_sessions
    if 'sessions' in body:
        coach_sessions = []
        for coach_session in coach_template.sessions:
            present, index = isSessionPresent(coach_session, body['sessions'])
            if present:
                setNonNullCoachSessionFields(coach_session, body['sessions'][index])
                coach_sessions.append(coach_session)
        # add sessions to tempalte.sessions
        coach_template.sessions = coach_sessions
                
    try:
        db.session.commit()
        db.session.refresh(coach_template)
    except Exception as e:
        print(e)
        return {
            "error": "Internal Server Error"
        }, 500
        raise

    return coach_template_schema.dump(coach_template)


@app.route("/coach/session", methods=['PUT'])
@http_guard(renew=True, nullable=False)
def updateSession(token_claims):
    if token_claims['role'] != Role.COACH.name:
        return {
            "error": "Expected role of COACH"
        }, 401

    body = request.get_json(force=True)

    if 'id' not in body:
        return {
            "error": "No parameter id found in request body"
        }, 400
    
    # grab the session being updated
    coach_session = CoachSession.query.get(body['id'])
    
    if coach_session == None:
        return {
            "error": "No coach session found with supplied id"
        }, 404

    # Update the session metadata that the request has asked for, handle updating client_exercises separately
    setNonNullCoachSessionFields(coach_session, body)

    # Update the client_exercises by replacing the ones in client_session with the ones passed in the request
    if 'coach_exercises' in body:
        coach_exercises = []
        for coach_exercise in body['coach_exercises']:
            coach_exercises.append(
                CoachExercise(
                    exercise_id=coach_exercise['exercise_id'], coach_session_id=coach_exercise['coach_session_id'], order=coach_exercise['order']
                )
            )
        coach_session.coach_exercises = coach_exercises

    try:
        db.session.commit()
        db.session.refresh(coach_session)
    except Exception as e:
        print(e)
        return {
            "error": "Internal Server Error"
        }, 500
        raise

    return coach_session_schema.dump(coach_session)
