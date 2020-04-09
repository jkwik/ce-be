from backend import db, app
from backend.middleware.middleware import http_guard
from backend.models.client_templates import ClientTemplate, client_template_schema, ClientSession, client_session_schemas
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

    return {
        "template": templateResult
    }
