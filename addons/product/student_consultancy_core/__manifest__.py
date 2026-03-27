{
    "name": "Student Consultancy Core",
    "summary": "Technical foundation and curated operating mode for student consultancy instances",
    "version": "18.0.1.0.0",
    "category": "Services",
    "author": "180 Degrees Consulting ESCP",
    "website": "https://github.com/180dc-escp/odoo-student-consultancy",
    "license": "LGPL-3",
    "depends": ["base_setup"],
    "data": [
        "security/student_consultancy_security.xml",
        "views/student_consultancy_core_menus.xml",
        "views/res_config_settings_views.xml",
    ],
    "post_init_hook": "post_init_hook",
    "installable": True,
    "application": False,
}
