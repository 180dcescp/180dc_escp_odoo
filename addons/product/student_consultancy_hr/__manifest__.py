{
    "name": "Student Consultancy HR",
    "summary": "Member lifecycle, departments, roles, and chapter role permissions",
    "version": "18.0.1.0.0",
    "category": "Services",
    "author": "180 Degrees Consulting ESCP",
    "website": "https://github.com/180dc-escp/odoo-student-consultancy",
    "license": "LGPL-3",
    "depends": [
        "student_consultancy_core",
        "student_consultancy_cycles",
        "student_consultancy_contacts",
    ],
    "data": [
        "security/ir.model.access.csv",
        "views/student_consultancy_hr_views.xml",
    ],
    "installable": True,
    "application": False,
}
