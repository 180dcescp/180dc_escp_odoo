from odoo import api, fields, models


class ResPartner(models.Model):
    _inherit = "res.partner"

    sc_contact_kind = fields.Selection(
        [("person", "Person"), ("organization", "Organization")],
        string="Consultancy Contact Kind",
        compute="_compute_sc_contact_kind",
        store=True,
    )
    sc_is_member_contact = fields.Boolean(string="Member Contact", default=False)
    sc_is_alumni_contact = fields.Boolean(string="Alumni Contact", default=False)
    sc_is_applicant_contact = fields.Boolean(string="Applicant Contact", default=False)
    sc_is_client_contact = fields.Boolean(string="Client Contact", default=False)
    sc_preferred_pronouns = fields.Char(string="Preferred Pronouns")
    sc_study_program = fields.Char(string="Study Program")
    sc_graduation_year = fields.Integer(string="Graduation Year")
    sc_public_bio = fields.Text(string="Public Bio")

    @api.depends("company_type", "is_company")
    def _compute_sc_contact_kind(self):
        for partner in self:
            partner.sc_contact_kind = "organization" if partner.company_type == "company" or partner.is_company else "person"

    def student_consultancy_mark_contact(
        self,
        *,
        is_member=None,
        is_alumni=None,
        is_applicant=None,
        is_client=None,
    ):
        values = {}
        if is_member is not None:
            values["sc_is_member_contact"] = is_member
        if is_alumni is not None:
            values["sc_is_alumni_contact"] = is_alumni
        if is_applicant is not None:
            values["sc_is_applicant_contact"] = is_applicant
        if is_client is not None:
            values["sc_is_client_contact"] = is_client
        if values:
            self.write(values)
        return True
