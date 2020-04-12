from backend import db
from sqlalchemy import func
from backend.models.client_templates import ClientSession

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
    through a separate endpoint
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
