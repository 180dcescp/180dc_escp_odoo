import json

from odoo import http
from odoo.http import request


class StudentConsultancyWebsiteController(http.Controller):
    @staticmethod
    def _bad_request(message, status=400):
        return request.make_json_response({"ok": False, "error": message}, status=status)

    @http.route("/student_consultancy/v1/public", type="http", auth="public", methods=["GET"], csrf=False)
    def public_payload(self, **kwargs):
        payload = request.env["student.consultancy.public_api"].sudo().public_payload()
        return request.make_json_response(payload, status=200)

    @http.route(
        ["/student_consultancy/v1/applications", "/student_consultancy/v1/apply"],
        type="http",
        auth="public",
        methods=["POST"],
        csrf=False,
    )
    def apply(self, **kwargs):
        raw = request.httprequest.data or b"{}"
        try:
            payload = json.loads(raw.decode("utf-8"))
        except json.JSONDecodeError:
            return self._bad_request("Invalid JSON payload.")

        try:
            application = request.env["student.consultancy.public_api"].sudo().create_application_from_payload(payload)
        except ValueError as error:
            return self._bad_request(str(error))

        return request.make_json_response({"ok": True, "applicationId": application.id}, status=200)
