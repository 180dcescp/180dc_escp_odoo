import os
import json

import werkzeug.urls

from odoo import http
from odoo.addons.auth_oauth.controllers.main import OAuthLogin
from odoo.exceptions import AccessDenied
from odoo.addons.web.controllers.home import Home
from odoo.addons.web.controllers.session import Session
from odoo.addons.web.controllers.utils import ensure_db
from odoo.http import request


def _authentik_bridge_disabled():
    value = os.getenv("AUTHENTIK_OAUTH_BRIDGE_DISABLED", "")
    return value.strip().lower() in {"1", "true", "yes", "on"}


class AuthentikOnlyHome(Home):
    @staticmethod
    def _local_autologin_login():
        return os.getenv("LOCAL_AUTOLOGIN_LOGIN", "escp@180dc.org").strip() or "escp@180dc.org"

    @staticmethod
    def _local_autologin_password():
        return os.getenv("ODOO_ADMIN_PASSWORD", "")

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

    def _local_autologin_response(self, redirect=None):
        ensure_db()
        if request.session.uid:
            response = request.redirect(redirect or "/odoo", 303)
            response.autocorrect_location_header = False
            return response
        password = self._local_autologin_password()
        if not password:
            return request.make_response("Missing local autologin password.", status=503)
        credential = {
            "login": self._local_autologin_login(),
            "password": password,
            "type": "password",
        }
        request.session.authenticate(request.db, credential)
        response = request.redirect(redirect or "/odoo", 303)
        response.autocorrect_location_header = False
        return response

    @http.route("/", type="http", auth="none", readonly=False)
    def index(self, **kw):
        if _authentik_bridge_disabled():
            return self._local_autologin_response("/odoo")
        if request.session.uid:
            response = request.redirect("/odoo", 303)
        else:
            response = request.redirect("/web/login?redirect=%2Fodoo%3F", 303)
        response.autocorrect_location_header = False
        return response

    @http.route("/web/login", type="http", auth="none", readonly=False)
    def web_login(self, redirect=None, **kw):
        if _authentik_bridge_disabled():
            return self._local_autologin_response(redirect or "/odoo")
        ensure_db()
        if request.session.uid:
            response = request.redirect("/odoo", 303)
            response.autocorrect_location_header = False
            return response
        if request.httprequest.method == "POST":
            return request.make_response(
                "Password login is disabled; use Authentik SSO.",
                status=403,
            )
        provider = self._authentik_provider()
        if not provider:
            return request.make_response("Authentik SSO is not configured.", status=503)
        auth_link = self._authentik_auth_link(provider)
        response = request.make_response("", headers=[("Location", auth_link)], status=303)
        return response


class AuthentikOnlySession(Session):
    @http.route("/web/session/authenticate", type="json", auth="none")
    def authenticate(self, db, login, password, base_location=None):
        if _authentik_bridge_disabled():
            return super().authenticate(db, login, password, base_location=base_location)
        raise AccessDenied("Password login is disabled; use Authentik SSO.")
