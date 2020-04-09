from backend import db, app
from backend.middleware.middleware import http_guard
from backend.models.client_templates import ClientTemplate, client_template_schema, client_template_schemas, ClientSession, client_session_schema
from flask import request
from sqlalchemy.orm import load_only, Load, subqueryload

@app.route("/client/templates", methods=["GET"])
@http_guard(renew=True, nullable=False)
def getCoachTemplates(token_claims):
    user_id = request.args.get('user_id')
    if user_id == None:
        return {
            "error": "No query parameter user_id found in request"
        }, 400

    templates = db.session.query(
        ClientTemplate.id, ClientTemplate.name, ClientTemplate.start_date, ClientTemplate.end_date,
        ClientTemplate.user_id, ClientTemplate.completed
    ).filter(ClientTemplate.user_id == user_id)

    result = client_template_schemas.dump(templates)

    return {
        "templates": result
    }

@app.route("/client/template", methods=["GET"])
@http_guard(renew=True, nullable=False)
def getCoachTemplate(token_claims):
    # Any logged in user should be able to access this method
    id = request.args.get('id')
    if id == None:
        return {
            "error": "No query parameter id found in request"
        }, 400
    
    template = ClientTemplate.query.filter_by(id=id).first()

    templateResult = client_template_schema.dump(template)

    return {
        "template": templateResult
    }

@app.route("/client/template", methods=["POST"])
@http_guard(renew=True, nullable=False)
def createCoachTemplate(token_claims):
    return {
        "error": "Not implemented"
    }

@app.route("/client/session", methods=["GET"])
@http_guard(renew=True, nullable=False)
def getCoachSession(token_claims):
    # Any logged in user should be able to access this method
    template_id = request.args.get('template_id')
    session_id = request.args.get('session_id')
    if template_id == None:
        return {
            "error": "No query parameter template_id found in request"
        }, 400
    if session_id == None:
        return {
            "error": "No query parameter session_id found in request"
        }, 400
    
    session = ClientSession.query.filter_by(id=session_id, client_template_id=template_id).first()
    if session == None:
        return {
            "error": "No session found with template_id: " + template_id + " and session_id: " + session_id
        }, 404

    sessionResult = client_session_schema.dump(session)

    return {
        "session": sessionResult
    }
