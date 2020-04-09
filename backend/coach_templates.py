from backend import app, db
from backend.middleware.middleware import http_guard
from flask import request, session
from sqlalchemy.exc import IntegrityError
# from sqlalchemy.orm import defer, joinedload, load_only, subqueryload
from backend.models.user import Role
from backend.models.coach_templates import CoachTemplate, coach_template_schema, coach_template_schemas, coach_session_schema, coach_session_schemas, Exercise, coach_exercise_schema, CoachSession, coach_exercise_schemas, CoachExercise, Exercise

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
        "result": result
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
    
    session = CoachSession.query.filter_by(id=id).first()
    # exercises = CoachExercise.query.join(Exercise, CoachExercise.exercise_id==Exercise.id)

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

    exercise = CoachExercise.query.filter_by(id=id).first()

    if exercise == None:
        return {
            "error": "Coach_exercise not found with given id: " + id
        }, 404

    result = coach_exercise_schema.dump(exercise)

    return result



# # Coach_exercises to coach_sessions (DOES NOT WORK  COMPLETELY)
# @app.route("/ce_to_cs", methods=['GET'])
# def ce_to_cs():
#     # retrieve exercises belonging to the session with the passed in session id
#     coach_session = CoachSession()
#     coach_session = CoachSession.query.filter_by(id='1').first()
#     # retrieve using foreign key "coach_exercises"
#     exercises = coach_session.coach_exercises

#     if exercises == None:
#         return {
#             "error": "Invalid session id"
#         }, 404

#     result = coach_exercise_schemas.dump(exercises)

#     return {
#         "Coach_exercises ": result
#     }
