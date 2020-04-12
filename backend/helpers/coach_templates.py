from backend import db
from sqlalchemy import func
from backend.models.coach_templates import CoachSession

def findNextSessionOrder(coach_template_id):
    """
    Finds the next order in a client templates session
    """
    next_order = db.session.query(func.max(CoachSession.order)).filter_by(coach_template_id=coach_template_id).scalar()
    
    if next_order == None:
        return 1

    return next_order + 1


def setNonNullCoachSessionFields(coach_session, fields):
    """
    Sets the metadata values in a coach_session based on a supplied dictionary of fields. It ignores exercises as that should be handled
    through a separate endpoint
        - fields:
            {
                "name": "Heavy Chest Day",
                "order": 1,
                "coach_template_id": 2
            }
    """
    if 'name' in fields:
        coach_session.name = fields['name']
    if 'order' in fields:
        coach_session.order = fields['order']
    if 'coach_template_id' in fields:
        coach_session.coach_template_id = fields['coach_template_id']

def isSessionPresent(coach_session, sessions):
    """
    Finds if a coach_session model is present in a json array of sessions.
        - returns
            1. true or false
            2. index in sessions
    """
    for i in range(len(sessions)):
        if coach_session.id == sessions[i]['id']:
            return True, i
    
    return False, -1
