from backend import db
from sqlalchemy import func
from backend.models.client_templates import ClientSession, ClientExercise, TrainingEntry
from datetime import datetime as dt
from datetime import date, timedelta
DATE_FORMAT = '%Y-%m-%d'

def findNextSessionOrder(client_template_id):
    """
    Finds the next order in a client templates session
    """
    next_order = db.session.query(func.max(ClientSession.order)).filter_by(client_template_id=client_template_id).scalar()
    
    if next_order == None:
        return 1

    return next_order + 1

def setNonNullClientTemplateFields(client_template, fields):
    """
    Sets the metadata values in a client_template based on a supplied dictionary of fields. It ignores sessions as that should be handled
    with a separate algorithm
        - fields:
            {
                "name": "Swoldier Program"
                "user_id": 10,
                "start_date": "01/01/2020",
                "end_date": "01/01/2021",
                "completed": false
            }
    """
    if 'name' in fields:
        client_template.name = fields['name']
    if 'user_id' in fields:
        client_template.user_id = fields['user_id']
    if 'start_date' in fields:
        client_template.start_date = fields['start_date']
    if 'end_date' in fields:
        client_template.end_date = fields['end_date']
    if 'completed' in fields:
        client_template.completed = fields['completed']

def setNonNullClientSessionFields(client_session, fields):
    """
    Sets the metadata values in a client_session based on a supplied dictionary of fields. It ignores exercises and training_entries as that should be handled
    through a separate endpoint.
        - fields:
            {
                "client_weight": 150
                "comment": "Slow start, great finish",
                "name": "Heavy Chest Day",
                "order": 1,
                "completed": true,
                "client_template_id": 2
            }
    """
    if 'client_weight' in fields:
        client_session.client_weight = fields['client_weight']
    if 'comment' in fields:
        client_session.comment = fields['comment']
    if 'name' in fields:
        client_session.name = fields['name']
    if 'order' in fields:
        client_session.order = fields['order']
    if 'completed' in fields:
        client_session.completed = fields['completed']
    if 'client_template_id' in fields:
        client_session.client_template_id = fields['client_template_id']
    if 'completed_date' in fields:
        client_session.completed_date = fields['completed_date']

def isSessionPresent(client_session, sessions):
    """
    Finds if a client_session model is present in a json array of sessions.
        - returns
            1. true or false
            2. index in sessions
    """
    for i in range(len(sessions)):
        if client_session.id == sessions[i]['id']:
            return True, i
    
    return False, -1

def setNonNullCheckinFields(checkin, fields):
    """
    Sets the metadata values in a checkin based on a supplied dictionary of fields. 
        - fields:
            {
                "start_date": "10/20/2020",
		        "end_date": "10/25/2020",
		        "coach_comment": "Coach comment",
		        "client_comment": "Client comment",
		        "client_template_id": 1,
		        "completed": false
            }
    """
    if 'start_date' in fields:
        checkin.start_date = fields['start_date']
    if 'end_date' in fields:
        checkin.end_date = fields['end_date']
    if 'coach_comment' in fields:
        checkin.coach_comment = fields['coach_comment']
    if 'client_comment' in fields:
        checkin.client_comment = fields['client_comment']
    if 'client_template_id' in fields:
        checkin.client_template_id = fields['client_template_id']
    if 'completed' in fields:
        checkin.completed = fields['completed']

def setUpdateSessionFields(client_template, client_session, body):
    # If they are completing a session (completed=True), then set the completed date to template start_date + session order (in days)
    if 'completed' in body:
        if body['completed'] == True:
            client_session.completed_date = (dt.strptime(str(client_template.start_date), DATE_FORMAT) + timedelta(days=client_session.order)).strftime(DATE_FORMAT)
    
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
    
    return client_session