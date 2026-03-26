import logging

import pytz

from odoo import SUPERUSER_ID, api, models
from odoo.exceptions import AccessDenied
from odoo.http import request


_logger = logging.getLogger(__name__)


class ResUsers(models.Model):
    _inherit = "res.users"

    @staticmethod
    def _oauth_bridge_normalize_email(raw):
        return (raw or "").strip().lower()

    def _oauth_bridge_identity_email(self, validation):
        email = self._oauth_bridge_normalize_email(validation.get("email"))
        if email:
            return email

        for key in ("preferred_username", "username", "upn"):
            candidate = self._oauth_bridge_normalize_email(validation.get(key))
            if "@" in candidate:
                return candidate
        return ""

    def _oauth_bridge_member_employee(self, email):
        if not email.endswith("@180dc.org"):
            return self.env["hr.employee"]
        return (
            self.env["hr.employee"]
            .with_user(SUPERUSER_ID)
            .sudo()
            .search([("active", "=", True), ("work_email", "=", email)], limit=1)
        )

    def _oauth_bridge_existing_user(self, email, provider, oauth_uid):
        Users = self.with_user(SUPERUSER_ID).sudo()

        if oauth_uid:
            oauth_user = Users.search(
                [("oauth_provider_id", "=", provider), ("oauth_uid", "=", oauth_uid)],
                limit=1,
            )
            if oauth_user:
                return oauth_user

        if not email:
            return Users

        return Users.search([("login", "=", email)], limit=1)

    def _oauth_bridge_sync_user(self, user, provider, oauth_uid, access_token, email, display_name):
        vals = {
            "oauth_provider_id": provider,
            "oauth_uid": oauth_uid,
            "oauth_access_token": access_token,
            "share": False,
        }
        if user.id != SUPERUSER_ID:
            vals["active"] = True
        if email and user.login != email:
            vals["login"] = email
        if email and user.email != email:
            vals["email"] = email
        if display_name and user.name != display_name:
            vals["name"] = display_name
        user.write(vals)

    def _oauth_bridge_sync_employee_link(self, employee, user):
        if employee and (not employee.user_id or employee.user_id != user):
            employee.write({"user_id": user.id})

    def _oauth_bridge_allow_existing_admin_without_employee(self, user):
        return bool(user and user.has_group("base.group_system"))

    def _oauth_bridge_match_oauth_session_user(self, credential):
        token = credential.get("token")
        login = self._oauth_bridge_normalize_email(credential.get("login"))
        if credential.get("type") != "oauth_token" or not token:
            return self.env["res.users"]

        Users = self.with_user(SUPERUSER_ID).sudo()
        domain = [("oauth_access_token", "=", token), ("active", "=", True)]
        if login:
            domain.append(("login", "=", login))
        elif self and len(self) == 1:
            domain.append(("id", "=", self.id))
        else:
            domain.append(("id", "=", self.env.uid))
        return Users.search(domain, limit=1)

    @classmethod
    def _login(cls, db, credential, user_agent_env):
        if credential.get("type") == "oauth_token" and credential.get("login") and credential.get("token"):
            login = credential["login"]
            ip = request.httprequest.environ["REMOTE_ADDR"] if request else "n/a"
            try:
                with cls.pool.cursor() as cr:
                    self = api.Environment(cr, SUPERUSER_ID, {})[cls._name]
                    with self._assert_can_auth(user=login):
                        user = self.with_user(SUPERUSER_ID).sudo().search(
                            [
                                ("login", "=", login),
                                ("active", "=", True),
                                ("oauth_access_token", "=", credential["token"]),
                            ],
                            limit=1,
                        )
                        if not user:
                            raise AccessDenied()
                        user = user.with_user(user)
                        tz = request.cookies.get("tz") if request else None
                        if tz in pytz.all_timezones and (not user.tz or not user.login_date):
                            user.tz = tz
                        user._update_last_login()
                        return {
                            "uid": user.id,
                            "auth_method": "oauth",
                            "mfa": "default",
                        }
            except AccessDenied:
                _logger.info("Login failed for db:%s login:%s from %s", db, login, ip)
                raise
        return super()._login(db, credential, user_agent_env)

    @api.model
    def _auth_oauth_signin(self, provider, validation, params):
        oauth_uid = validation["user_id"]
        email = self._oauth_bridge_identity_email(validation)
        user = self._oauth_bridge_existing_user(email, provider, oauth_uid)
        employee = self._oauth_bridge_member_employee(email)
        if not employee:
            if self._oauth_bridge_allow_existing_admin_without_employee(user):
                display_name = validation.get("name") or user.name or email
                self._oauth_bridge_sync_user(
                    user,
                    provider,
                    oauth_uid,
                    params["access_token"],
                    email,
                    display_name,
                )
                return user.login
            raise AccessDenied()

        display_name = validation.get("name") or employee.name or email
        if not user:
            user = (
                self.with_user(SUPERUSER_ID)
                .sudo()
                .with_context(
                    no_reset_password=True,
                    x_180dc_allow_user_create=True,
                )
                .create(
                    {
                        "name": display_name,
                        "login": email,
                        "email": email,
                        "groups_id": [(6, 0, [self.env.ref("base.group_user").id])],
                        "active": True,
                        "share": False,
                    }
                )
            )

        self._oauth_bridge_sync_user(
            user,
            provider,
            oauth_uid,
            params["access_token"],
            email,
            display_name,
        )
        self._oauth_bridge_sync_employee_link(employee, user)
        return user.login

    def _check_credentials(self, credential, env):
        matched_user = self._oauth_bridge_match_oauth_session_user(credential)
        if matched_user:
            return {
                "uid": matched_user.id,
                "auth_method": "oauth",
                "mfa": "default",
            }
        return super()._check_credentials(credential, env)
