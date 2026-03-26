import os
import json
import logging

import requests
import werkzeug.urls

from odoo import SUPERUSER_ID, _, http
from odoo.addons.auth_oauth.controllers.main import OAuthController, OAuthLogin
from odoo.addons.web.controllers.utils import _get_login_redirect_url, ensure_db
from odoo.exceptions import AccessDenied
from odoo.http import request
from odoo.tools.misc import clean_context


_logger = logging.getLogger(__name__)


def _authentik_bridge_disabled():
    value = os.getenv("AUTHENTIK_OAUTH_BRIDGE_DISABLED", "")
    return value.strip().lower() in {"1", "true", "yes", "on"}


class AuthentikOAuthLogin(OAuthLogin):
    def _bridge_is_authentik_provider(self, provider):
        if _authentik_bridge_disabled():
            return False
        endpoint = (provider.get("auth_endpoint") or "").lower()
        return "login.180dc-escp.org" in endpoint and "/application/o/authorize" in endpoint

    def _bridge_code_auth_link(self, provider):
        return_url = request.httprequest.url_root + "auth_oauth/signin"
        state = self.get_state(provider)
        params = {
            "response_type": "code",
            "client_id": provider["client_id"],
            "redirect_uri": return_url,
            "scope": provider["scope"],
            "state": json.dumps(state),
        }
        return "%s?%s" % (provider["auth_endpoint"], werkzeug.urls.url_encode(params))

    def list_providers(self):
        providers = super().list_providers()
        for provider in providers:
            if self._bridge_is_authentik_provider(provider):
                provider["auth_link"] = self._bridge_code_auth_link(provider)
        return providers


class AuthentikOAuthController(OAuthController):
    def _bridge_oauth_provider(self, provider_id):
        return request.env["auth.oauth.provider"].sudo().browse(provider_id)

    def _bridge_is_authentik_provider(self, oauth_provider):
        if _authentik_bridge_disabled():
            return False
        endpoint = (oauth_provider.auth_endpoint or "").lower()
        return "login.180dc-escp.org" in endpoint and "/application/o/authorize" in endpoint

    def _bridge_token_endpoint(self, oauth_provider):
        auth_endpoint = oauth_provider.auth_endpoint or ""
        if auth_endpoint.endswith("/authorize/"):
            return auth_endpoint[:-len("/authorize/")] + "/token/"
        if auth_endpoint.endswith("/authorize"):
            return auth_endpoint[:-len("/authorize")] + "/token/"
        return auth_endpoint.replace("/authorize", "/token")

    def _bridge_client_secret(self, oauth_provider):
        key = "authentik_oauth_member_bridge.client_secret.%s" % oauth_provider.id
        return request.env["ir.config_parameter"].sudo().get_param(key, "")

    def _bridge_exchange_code(self, oauth_provider, code):
        client_secret = self._bridge_client_secret(oauth_provider)
        if not client_secret:
            raise AccessDenied(_("Missing Authentik OAuth client secret."))

        token_response = requests.post(
            self._bridge_token_endpoint(oauth_provider),
            data={
                "grant_type": "authorization_code",
                "client_id": oauth_provider.client_id,
                "client_secret": client_secret,
                "redirect_uri": request.httprequest.url_root + "auth_oauth/signin",
                "code": code,
            },
            timeout=10,
        )
        token_response.raise_for_status()
        payload = token_response.json()
        access_token = payload.get("access_token")
        if not access_token:
            raise AccessDenied(_("Missing access token in Authentik response."))
        return access_token

    def _bridge_fetch_userinfo(self, oauth_provider, access_token):
        response = requests.get(
            oauth_provider.validation_endpoint,
            headers={"Authorization": "Bearer %s" % access_token},
            timeout=10,
        )
        response.raise_for_status()
        validation = response.json()

        subject = next(
            filter(
                None,
                [
                    validation.get("sub"),
                    validation.get("id"),
                    validation.get("user_id"),
                ],
            ),
            None,
        )
        if not subject:
            raise AccessDenied(_("Missing subject identity from Authentik userinfo."))
        validation["user_id"] = subject
        return validation

    @http.route("/auth_oauth/signin", type="http", auth="none", readonly=False)
    def signin(self, **kw):
        code = kw.get("code")
        state_raw = kw.get("state")
        if not code or not state_raw:
            return super().signin(**kw)

        try:
            state = json.loads(state_raw)
        except Exception:
            return super().signin(**kw)

        provider_id = state.get("p")
        oauth_provider = self._bridge_oauth_provider(provider_id)
        if not oauth_provider or not self._bridge_is_authentik_provider(oauth_provider):
            return super().signin(**kw)

        dbname = state["d"]
        if not http.db_filter([dbname]):
            return super().signin(**kw)
        ensure_db(db=dbname)
        request.update_context(**clean_context(state.get("c", {})))

        try:
            params = dict(kw)
            access_token = self._bridge_exchange_code(oauth_provider, code)
            params["access_token"] = access_token
            validation = self._bridge_fetch_userinfo(oauth_provider, access_token)
            login = (
                request.env["res.users"]
                .with_user(SUPERUSER_ID)
                ._auth_oauth_signin(provider_id, validation, params)
            )
            if not login:
                raise AccessDenied()
            key = access_token
            request.env.cr.commit()

            action = state.get("a")
            menu = state.get("m")
            redirect = werkzeug.urls.url_unquote_plus(state["r"]) if state.get("r") else False
            url = "/odoo"
            if redirect:
                url = redirect
            elif action:
                url = "/odoo/action-%s" % action
            elif menu:
                url = "/odoo?menu_id=%s" % menu

            credential = {"login": login, "token": key, "type": "oauth_token"}
            auth_info = request.session.authenticate(dbname, credential)
            resp = request.redirect(_get_login_redirect_url(auth_info["uid"], url), 303)
            resp.autocorrect_location_header = False
            if werkzeug.urls.url_parse(resp.location).path == "/web" and not request.env.user._is_internal():
                resp.location = "/"
            return resp
        except AccessDenied:
            _logger.info(
                "Authentik OAuth bridge denied access for provider %s", oauth_provider.id
            )
            url = "/web/login?oauth_error=3"
        except Exception:
            _logger.exception("Authentik OAuth code flow failed")
            url = "/web/login?oauth_error=2"

        redirect = request.redirect(url, 303)
        redirect.autocorrect_location_header = False
        return redirect
