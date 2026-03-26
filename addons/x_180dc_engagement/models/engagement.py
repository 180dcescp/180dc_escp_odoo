from datetime import date

from odoo import api, fields, models
from odoo.exceptions import ValidationError


class X180DCEngagementProjectType(models.Model):
    _name = "x_180dc.engagement.project_type"
    _description = "180DC Engagement Project Type"
    _order = "name, id"

    name = fields.Char(required=True)
    active = fields.Boolean(default=True)
    x_short_description = fields.Text()
    x_long_description = fields.Html()
    engagement_ids = fields.Many2many(
        "x_180dc.engagement",
        "x_180dc_engagement_project_type_rel",
        "project_type_id",
        "engagement_id",
        string="Engagements",
    )

    _sql_constraints = [
        ("x_180dc_engagement_project_type_name_uniq", "unique(name)", "Project type already exists."),
    ]


class X180DCEngagementConsultingTechnique(models.Model):
    _name = "x_180dc.engagement.consulting_technique"
    _description = "180DC Engagement Consulting Technique"
    _order = "name, id"

    name = fields.Char(required=True)
    active = fields.Boolean(default=True)
    x_short_description = fields.Text()
    x_long_description = fields.Html()
    engagement_ids = fields.Many2many(
        "x_180dc.engagement",
        "x_180dc_engagement_consulting_technique_rel",
        "technique_id",
        "engagement_id",
        string="Engagements",
    )

    _sql_constraints = [
        (
            "x_180dc_engagement_consulting_technique_name_uniq",
            "unique(name)",
            "Consulting technique already exists.",
        ),
    ]


class X180DCEngagement(models.Model):
    _name = "x_180dc.engagement"
    _description = "180DC Engagement"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = "cycle_year desc, cycle_id, id desc"

    name = fields.Char(required=True, tracking=True)
    active = fields.Boolean(default=True)

    client_company_id = fields.Many2one(
        "res.partner",
        string="Client Company",
        domain="[('is_company', '=', True)]",
        tracking=True,
    )
    client_contact_ids = fields.Many2many(
        "res.partner",
        "x_180dc_engagement_client_contact_rel",
        "engagement_id",
        "partner_id",
        string="Client Contacts",
        domain="[('is_company', '=', False), ('commercial_partner_id', '=', client_company_id)]",
        tracking=True,
    )
    lead_id = fields.Many2one(
        "crm.lead",
        string="CRM Lead/Opportunity",
        tracking=True,
    )

    # User-facing canonical period. Dates stay derived from cycle/year for downstream integrations.
    cycle_id = fields.Many2one(
        "x_180dc.engagement.cycle",
        string="Cycle",
        required=True,
        tracking=True,
        default=lambda self: self._default_cycle_id(),
        ondelete="restrict",
    )
    cycle = fields.Char(
        string="Cycle Code",
        required=True,
        tracking=True,
        index=True,
        compute="_compute_cycle_code",
        inverse="_inverse_cycle_code",
        store=True,
    )
    cycle_year = fields.Integer(
        required=True,
        tracking=True,
        default=lambda self: fields.Date.today().year,
    )
    date_start = fields.Date(required=True, tracking=True)
    date_end = fields.Date(required=True, tracking=True)
    period_label = fields.Char(string="Period", compute="_compute_period_label")

    member_ids = fields.Many2many(
        "hr.employee",
        "x_180dc_engagement_hr_employee_rel",
        "engagement_id",
        "employee_id",
        string="Members",
    )

    project_type_ids = fields.Many2many(
        "x_180dc.engagement.project_type",
        "x_180dc_engagement_project_type_rel",
        "engagement_id",
        "project_type_id",
        string="Project Types",
    )
    consulting_technique_ids = fields.Many2many(
        "x_180dc.engagement.consulting_technique",
        "x_180dc_engagement_consulting_technique_rel",
        "engagement_id",
        "technique_id",
        string="Consulting Techniques",
    )

    summary = fields.Html(string="Summary")

    contract_drive_link = fields.Char(string="Client Contract Drive Link")

    scoping_drive_link = fields.Char(string="Scoping Drive Link")

    final_presentation_drive_link = fields.Char(string="Final Presentation Drive Link")

    other_drive_link = fields.Char(string="Other Drive Link")

    invoice_ids = fields.One2many(
        "account.move",
        "x_engagement_id",
        string="Invoices",
        domain=[("move_type", "in", ["out_invoice", "out_refund"])],
    )
    invoice_count = fields.Integer(compute="_compute_invoice_count")

    _sql_constraints = [
        (
            "x_180dc_engagement_name_cycle_year_uniq",
            "unique(name, cycle_id, cycle_year)",
            "An engagement with the same name, cycle, and year already exists.",
        ),
    ]

    @api.depends("cycle_id.code")
    def _compute_cycle_code(self):
        for engagement in self:
            engagement.cycle = engagement.cycle_id.code if engagement.cycle_id else False

    def _inverse_cycle_code(self):
        Cycle = self.env["x_180dc.engagement.cycle"].sudo()
        for engagement in self:
            cycle = Cycle.search([("code", "=", engagement.cycle)], limit=1)
            if cycle:
                engagement.cycle_id = cycle

    @api.model
    def _default_cycle_id(self):
        return self.env["x_180dc.engagement.cycle"].sudo()._x_180dc_current_cycle().id

    @api.model
    def _x_180dc_cycle_code_for_date(self, target_date):
        cycle = self.env["x_180dc.engagement.cycle"].sudo()._x_180dc_cycle_for_date(target_date)
        return cycle.code if cycle else False

    @staticmethod
    def _cycle_bounds(cycle_record, year):
        if not cycle_record or not year:
            return False, False
        return cycle_record._x_180dc_bounds_for_year(year)

    @staticmethod
    def _extract_removed_m2m_ids(commands, current_ids):
        removed = set()
        current_set = set(current_ids)
        for command in commands or []:
            if not isinstance(command, (list, tuple)) or not command:
                continue
            op = command[0]
            if op == 5:
                removed |= current_set
            elif op in (2, 3):
                if len(command) > 1 and command[1]:
                    removed.add(command[1])
            elif op == 6:
                new_ids = set(command[2] or []) if len(command) > 2 else set()
                removed |= (current_set - new_ids)
        return removed

    @staticmethod
    def _cleanup_unused_tags(tag_model, candidate_ids):
        if not candidate_ids:
            return
        tags = tag_model.browse(list(candidate_ids)).exists()
        for tag in tags:
            if not tag.engagement_ids:
                tag.unlink()

    def _apply_cycle_defaults_on_vals(self, vals, current_cycle=None, current_year=None):
        cycle_code = vals.get("cycle", current_cycle)
        cycle_id = vals.get("cycle_id")
        year = vals.get("cycle_year", current_year)
        cycle_record = False
        if cycle_id:
            cycle_record = self.env["x_180dc.engagement.cycle"].browse(cycle_id)
        elif cycle_code:
            cycle_record = self.env["x_180dc.engagement.cycle"].sudo().search([("code", "=", cycle_code)], limit=1)
        if cycle_record and year:
            start, end = self._cycle_bounds(cycle_record, year)
            if start and end:
                vals["cycle_id"] = cycle_record.id
                vals["cycle"] = cycle_record.code
                vals["date_start"] = start
                vals["date_end"] = end

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            self._apply_cycle_defaults_on_vals(vals)
        return super().create(vals_list)

    def write(self, vals):
        removed_project_type_ids = set()
        removed_technique_ids = set()

        if "project_type_ids" in vals:
            for rec in self:
                removed_project_type_ids |= self._extract_removed_m2m_ids(vals["project_type_ids"], rec.project_type_ids.ids)

        if "consulting_technique_ids" in vals:
            for rec in self:
                removed_technique_ids |= self._extract_removed_m2m_ids(
                    vals["consulting_technique_ids"], rec.consulting_technique_ids.ids
                )

        if {"cycle", "cycle_id", "cycle_year"} & set(vals):
            for rec in self:
                rec_vals = dict(vals)
                rec._apply_cycle_defaults_on_vals(rec_vals, rec.cycle, rec.cycle_year)
                super(X180DCEngagement, rec).write(rec_vals)
            res = True
        else:
            res = super().write(vals)

        self._cleanup_unused_tags(self.env["x_180dc.engagement.project_type"], removed_project_type_ids)
        self._cleanup_unused_tags(self.env["x_180dc.engagement.consulting_technique"], removed_technique_ids)

        return res

    def unlink(self):
        removed_project_type_ids = set(self.mapped("project_type_ids").ids)
        removed_technique_ids = set(self.mapped("consulting_technique_ids").ids)
        res = super().unlink()
        self._cleanup_unused_tags(self.env["x_180dc.engagement.project_type"], removed_project_type_ids)
        self._cleanup_unused_tags(self.env["x_180dc.engagement.consulting_technique"], removed_technique_ids)
        return res

    @api.depends("cycle_id.name", "cycle_year")
    def _compute_period_label(self):
        for rec in self:
            if rec.cycle_id and rec.cycle_year:
                rec.period_label = f"{rec.cycle_id.name} {rec.cycle_year}"
            else:
                rec.period_label = False

    @api.model
    def _x_180dc_backfill_cycle_ids(self):
        Cycle = self.env["x_180dc.engagement.cycle"].sudo()
        for engagement in self.sudo().search([]):
            if engagement.cycle_id:
                continue
            cycle = Cycle.search([("code", "=", engagement.cycle)], limit=1)
            if cycle:
                engagement.sudo().write({"cycle_id": cycle.id})

    @api.depends("invoice_ids")
    def _compute_invoice_count(self):
        for rec in self:
            rec.invoice_count = len(rec.invoice_ids)

    @api.constrains("client_company_id", "client_contact_ids")
    def _check_client_partners(self):
        for rec in self:
            if rec.client_company_id and not rec.client_company_id.is_company:
                raise ValidationError("Client company must be a company contact.")
            for contact in rec.client_contact_ids:
                if contact.is_company:
                    raise ValidationError("Client contacts must be person contacts.")
                if rec.client_company_id and contact.commercial_partner_id != rec.client_company_id:
                    raise ValidationError("Each client contact must belong to the selected client company.")

    @api.constrains("date_start", "date_end")
    def _check_date_range(self):
        for rec in self:
            if rec.date_end and rec.date_start and rec.date_end < rec.date_start:
                raise ValidationError("End date must be on or after start date.")

    def action_view_invoices(self):
        self.ensure_one()
        action = self.env.ref("account.action_move_out_invoice_type").read()[0]
        action["domain"] = [("x_engagement_id", "=", self.id)]
        action["context"] = {
            "default_move_type": "out_invoice",
            "default_x_engagement_id": self.id,
            "default_partner_id": self.client_company_id.id,
        }
        return action
