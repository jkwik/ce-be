from backend import app
from backend.models.coach_templates import CoachTemplate, coach_session_schemas, Exercise, coach_exercise_schema, CoachSession, coach_exercise_schemas

# Iteration 2 -- RELATIONSHIP TESTS

# Coach_sessions test (DOES NOT WORK  COMPLETELY)
@app.route("/coachSession", methods=['GET'])
def coachSession():
    # retrieve sessions belonging to the template with the passed in template id
    coach_template = CoachTemplate()
    coach_template = CoachTemplate.query.filter_by(id='1').first()
    # retrieve using foreign key "coach_sessions"
    sessions = coach_template.coach_sessions

    if sessions == None:
        return {
            "error": "Invalid session id"
        }, 404

    result = coach_session_schemas.dump(sessions)

    return {
        "coach sessions": result
    }


# Coach_exercises test (DOES NOT WORK  COMPLETELY)
@app.route("/coachExercise", methods=['GET'])
def coachExercise():
    # retrieve coach_exercise belonging to the exercise with the passed in exercise id
    exercise = Exercise()
    exercise = Exercise.query.filter_by(id='1').first()
    # retrieve using foreign key "coach_exercises"
    coach_exercise = exercise.coach_exercises

    if coach_exercise == None:
        return {
            "error": "Invalid session id"
        }, 404

    result = coach_exercise_schema.dump(coach_exercise)

    return {
        "coach_exercise": result
    }

# Coach_exercises to coach_sessions (DOES NOT WORK  COMPLETELY)
@app.route("/ce_to_cs", methods=['GET'])
def ce_to_cs():
    # retrieve exercises belonging to the session with the passed in session id
    coach_session = CoachSession()
    coach_session = CoachSession.query.filter_by(id='1').first()
    # retrieve using foreign key "coach_exercises"
    exercises = coach_session.coach_exercises

    if exercises == None:
        return {
            "error": "Invalid session id"
        }, 404

    result = coach_exercise_schemas.dump(exercises)

    return {
        "Coach_exercises ": result
    }
