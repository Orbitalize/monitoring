import flask
from implicitdict import ImplicitDict
from uas_standards.astm.f3411.v22a.api import (
    OperationID,
    OPERATIONS,
    PutIdentificationServiceAreaNotificationParameters,
)
from uas_standards.astm.f3411.v22a.constants import (
    Scope,
)

from monitoring.mock_uss import webapp
from monitoring.mock_uss.auth import requires_scope


def rid_v22a_operation(op_id: OperationID):
    op = OPERATIONS[op_id]
    path = op.path.replace("{", "<").replace("}", ">")
    return webapp.route('/v2/uss/' + path, methods=[op.verb])


@rid_v22a_operation(OperationID.PostIdentificationServiceArea)
@requires_scope(Scope.ServiceProvider)
def ridsp_notify_isa_v22a(id: str):
    try:
        json = flask.request.json
        if json is None:
            raise ValueError("Request did not contain a JSON payload")
        ImplicitDict.parse(json, PutIdentificationServiceAreaNotificationParameters)
    except ValueError as e:
        msg = "Unable to parse PutIdentificationServiceAreaNotificationParameters JSON request: {}".format(
            e
        )
        return msg, 400

    return (
        flask.jsonify(None),
        204,
    )
