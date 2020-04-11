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

    # check if template name is available, no duplicates allowed
    check_duplicate = CoachSession.query.filter_by(name=body['name'], coach_template_id=body['coach_template_id']).first()

    if check_duplicate:
        return {
            "error": "Session name already exists for this template"
        }, 400
    
    # find current max order value for sessions belonging to the passed in coach_template_id
    max_order = db.session.query(func.max(CoachSession.order)).filter_by(coach_template_id=body['coach_template_id']).scalar()
    # 
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
    session = CoachSession.query.filter_by(name=body['name']).first()

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
    
    # find current max order value for sexercise belonging to the passed in coach_session_id
    max_order = db.session.query(func.max(CoachExercise.order)).filter_by(coach_session_id=body['coach_session_id']).scalar()
    # 
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
    exercise = Exercise.query.filter_by(name=body['name'], category=body['category']).first()

    result = exercise_schema.dump(exercise)
    
    return result