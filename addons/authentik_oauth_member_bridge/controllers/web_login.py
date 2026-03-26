import json

import werkzeug.urls

from odoo import http
from odoo.addons.auth_oauth.controllers.main import OAuthLogin
from odoo.exceptions import AccessDenied
from odoo.addons.web.controllers.home import Home
from odoo.addons.web.controllers.session import Session
from odoo.addons.web.controllers.utils import ensure_db
from odoo.http import request


class AuthentikOnlyHome(Home):
    @staticmethod
    def _authentik_provider():
        providers = request.env["auth.oauth.provider"].sudo().search([("enabled", "=", True)])
        for provider in providers:
            endpoint = (provider.auth_endpoint or "").lower()
            if "login.180dc-escp.org" in endpoint and "/application/o/authorize" in endpoint:
                return provider
        return False

    def _authentik_auth_link(self, provider):
        provider_dict = {
            "auth_endpoint": provider.auth_endpoint,
            "client_id": provider.client_id,
            "scope": provider.scope,
            "id": provider.id,
        }
        state = OAuthLogin().get_state(provider_dict)
        params = {
            "response_type": "code",
            "client_id": provider.client_id,
            "redirect_uri": request.httprequest.url_root + "auth_oauth/signin",
            "scope": provider.scope,
            "state": json.dumps(state),
        }
        return "%s?%s" % (provider.auth_endpoint, werkzeug.urls.url_encode(params))

    @http.route("/web/login", type="http", auth="none", readonly=False)
    def web_login(self, redirect=None, **kw):
        ensure_db()
        if request.httprequest.method == "POST":
            return request.make_response(
                "Password login is disabled; use Authentik SSO.",
                status=403,
            )
        provider = self._authentik_provider()
        if not provider:
            return request.make_response("Authentik SSO is not configured.", status=503)
        auth_link = self._authentik_auth_link(provider)
        body = (
            "<html><body>"
            "<h1>180DC Login</h1>"
            "<p>Password login is disabled.</p>"
            f'<p><a href="{auth_link}">Continue with Authentik SSO</a></p>'
            "</body></html>"
        )
        return request.make_response(body, headers=[("Content-Type", "text/html; charset=utf-8")])


class AuthentikOnlySession(Session):
    @http.route("/web/session/authenticate", type="json", auth="none")
    def authenticate(self, db, login, password, base_location=None):
        raise AccessDenied("Password login is disabled; use Authentik SSO.")
