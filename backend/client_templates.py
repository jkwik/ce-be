from backend import db, app
from backend.middleware.middleware import http_guard
from backend.models.client_templates import ClientTemplate, client_template_schema, ClientSession, client_session_schema
from flask import request
from sqlalchemy.orm import load_only, Load, subqueryload

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

    return templateResult

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

    return sessionResult
