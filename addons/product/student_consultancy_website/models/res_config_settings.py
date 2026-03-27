from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    sc_organization_name = fields.Char(
        string="Organization Name",
        config_parameter="student_consultancy.website.organization_name",
        default="Student Consultancy",
    )
    sc_contact_email = fields.Char(
        string="Public Contact Email",
        config_parameter="student_consultancy.website.contact_email",
        default="contact@example.org",
    )
    sc_website_url = fields.Char(
        string="Public Website URL",
        config_parameter="student_consultancy.website.url",
        default="https://example.org",
    )
    sc_website_tagline = fields.Text(
        string="Website Tagline",
        config_parameter="student_consultancy.website.tagline",
        default="Student-led strategic consulting for mission-driven organizations.",
    )
    sc_chapter_profile = fields.Text(
        string="Chapter Profile",
        config_parameter="student_consultancy.website.chapter_profile",
        default="A community-first student consultancy chapter.",
    )
