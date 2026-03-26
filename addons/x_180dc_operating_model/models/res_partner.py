from odoo import api, fields, models


class MailingList(models.Model):
    _inherit = "mailing.list"

    x_180dc_key = fields.Char(index=True)


class MailingContact(models.Model):
    _inherit = "mailing.contact"

    x_partner_id = fields.Many2one("res.partner", ondelete="cascade", index=True)


class ResPartner(models.Model):
    _inherit = "res.partner"

    x_mailing_opt_out = fields.Boolean(string="Email Marketing Opt Out")
    x_mailing_list_ids = fields.Many2many(
        "mailing.list",
        "x_180dc_partner_mailing_list_rel",
        "partner_id",
        "list_id",
        string="Email Marketing Lists",
    )
    x_derived_mailing_list_ids = fields.Many2many(
        "mailing.list",
        compute="_compute_x_derived_mailing_list_ids",
        string="Derived Email Marketing Lists",
    )

    @api.depends("category_id", "parent_id", "email", "is_company", "active", "x_mailing_list_ids")
    def _compute_x_derived_mailing_list_ids(self):
        derived_map = self._x_180dc_partner_list_map()
        for partner in self:
            partner.x_derived_mailing_list_ids = [(6, 0, list(derived_map.get(partner.id, set())))]

    @api.model
    def _x_180dc_ensure_default_mailing_lists(self):
        specs = [
            ("members", "Members"),
            ("alumni", "Alumni"),
            ("clients", "Clients"),
            ("talent_pool", "Talent Pool"),
        ]
        MailingList = self.env["mailing.list"].sudo()
        result = self.env["mailing.list"]
        for key, name in specs:
            mailing_list = MailingList.search([("x_180dc_key", "=", key)], limit=1)
            if not mailing_list:
                mailing_list = MailingList.search([("name", "=", name)], limit=1)
            if mailing_list:
                mailing_list.write({"name": name, "x_180dc_key": key})
            else:
                mailing_list = MailingList.create({"name": name, "x_180dc_key": key})
            result |= mailing_list
        return result

    def _x_180dc_derived_list_ids(self):
        self.ensure_one()
        return self._x_180dc_partner_list_map().get(self.id, set())

    def _x_180dc_partner_list_map(self):
        keyed_lists = self.env["mailing.list"].sudo().search([("x_180dc_key", "!=", False)])
        keyed_by_key = {mailing_list.x_180dc_key: mailing_list for mailing_list in keyed_lists}
        active_member_emails = {
            email.lower()
            for email in self.env["hr.employee"].sudo().search([("active", "=", True)]).mapped("work_email")
            if email
        }
        alumni_emails = {
            email.lower()
            for email in self.env["hr.employee"].sudo().search([("active", "=", False)]).mapped("work_email")
            if email
        }
        talent_pool_emails = set()
        for candidate in self.env["hr.candidate"].sudo().search([]):
            email = candidate.partner_id.email_normalized or (candidate.email_from or "").lower()
            if email:
                talent_pool_emails.add(email)

        mapping = {}
        for partner in self:
            derived_ids = set()
            partner_email = (partner.email_normalized or "").lower()
            if partner_email in active_member_emails and keyed_by_key.get("members"):
                derived_ids.add(keyed_by_key["members"].id)
            if partner_email in alumni_emails and keyed_by_key.get("alumni"):
                derived_ids.add(keyed_by_key["alumni"].id)
            if partner_email in talent_pool_emails and partner_email not in active_member_emails | alumni_emails:
                if keyed_by_key.get("talent_pool"):
                    derived_ids.add(keyed_by_key["talent_pool"].id)
            if any((category.name or "").startswith("Client") for category in partner.commercial_partner_id.category_id):
                if keyed_by_key.get("clients"):
                    derived_ids.add(keyed_by_key["clients"].id)
            mapping[partner.id] = derived_ids
        return mapping

    def _x_180dc_is_mailing_partner(self):
        return self.filtered(lambda partner: not partner.is_company and partner.email_normalized)

    def _x_180dc_sync_blacklist(self):
        Blacklist = self.env["mail.blacklist"].sudo()
        for partner in self._x_180dc_is_mailing_partner():
            entry = Blacklist.search([("email", "=", partner.email_normalized)], limit=1)
            if partner.x_mailing_opt_out:
                if entry:
                    entry.active = True
                else:
                    Blacklist.create({"email": partner.email_normalized})
            elif entry:
                entry.active = False

    def _x_180dc_sync_mailing_contacts(self):
        MailingContact = self.env["mailing.contact"].sudo()
        MailingSubscription = self.env["mailing.subscription"].sudo()
        eligible_partners = self._x_180dc_is_mailing_partner()
        ineligible_partners = self - eligible_partners
        derived_map = eligible_partners._x_180dc_partner_list_map()

        stale_contacts = MailingContact.search([("x_partner_id", "in", ineligible_partners.ids)])
        if stale_contacts:
            stale_contacts.subscription_ids.unlink()
            stale_contacts.unlink()

        for partner in eligible_partners:
            contact = MailingContact.search([("x_partner_id", "=", partner.id)], limit=1)
            if not contact:
                contact = MailingContact.search([("email_normalized", "=", partner.email_normalized)], limit=1)
            vals = {
                "name": partner.name,
                "email": partner.email,
                "company_name": partner.parent_id.name or partner.company_name,
                "country_id": partner.country_id.id,
                "tag_ids": [(6, 0, partner.category_id.ids)],
                "x_partner_id": partner.id,
            }
            if contact:
                contact.write(vals)
            else:
                contact = MailingContact.create(vals)

            desired_list_ids = set(partner.x_mailing_list_ids.ids) | derived_map.get(partner.id, set())
            current_subscriptions = {sub.list_id.id: sub for sub in contact.subscription_ids}
            for list_id in desired_list_ids - set(current_subscriptions):
                MailingSubscription.create(
                    {
                        "contact_id": contact.id,
                        "list_id": list_id,
                        "opt_out": partner.x_mailing_opt_out,
                    }
                )
            for list_id, subscription in current_subscriptions.items():
                if list_id not in desired_list_ids:
                    subscription.unlink()
                else:
                    subscription.write({"opt_out": partner.x_mailing_opt_out})

        self._x_180dc_sync_blacklist()

    @api.model_create_multi
    def create(self, vals_list):
        partners = super().create(vals_list)
        partners._x_180dc_sync_mailing_contacts()
        return partners

    def write(self, vals):
        mailing_sync_fields = {
            "name",
            "email",
            "company_name",
            "parent_id",
            "country_id",
            "category_id",
            "x_mailing_opt_out",
            "x_mailing_list_ids",
            "is_company",
            "active",
        }
        res = super().write(vals)
        if mailing_sync_fields & set(vals):
            self._x_180dc_sync_mailing_contacts()
        return res

    @api.model
    def _x_180dc_cron_sync_mailing_contacts(self):
        self._x_180dc_ensure_default_mailing_lists()
        self.search([])._x_180dc_sync_mailing_contacts()
