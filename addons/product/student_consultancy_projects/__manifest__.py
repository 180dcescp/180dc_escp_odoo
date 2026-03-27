{
    "name": "Student Consultancy Projects",
    "summary": "Project records, staffing assignments, visibility rules, and CRM handoff",
    "version": "18.0.1.0.0",
    "category": "Services",
    "author": "180 Degrees Consulting ESCP",
    "website": "https://github.com/180dc-escp/odoo-student-consultancy",
    "license": "LGPL-3",
    "depends": [
        "student_consultancy_core",
        "student_consultancy_cycles",
        "student_consultancy_contacts",
        "student_consultancy_hr",
        "crm",
    ],
    "data": [
        "security/ir.model.access.csv",
        "views/student_consultancy_project_views.xml",
    ],
    "installable": True,
    "application": False,
}
