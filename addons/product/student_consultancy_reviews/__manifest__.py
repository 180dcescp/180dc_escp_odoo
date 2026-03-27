{
    "name": "Student Consultancy Reviews",
    "summary": "Review templates, assignments, and project-aware appraisal workflows",
    "version": "18.0.1.0.0",
    "category": "Services",
    "author": "180 Degrees Consulting ESCP",
    "website": "https://github.com/180dc-escp/odoo-student-consultancy",
    "license": "LGPL-3",
    "depends": [
        "student_consultancy_core",
        "student_consultancy_cycles",
        "student_consultancy_hr",
        "student_consultancy_projects",
    ],
    "data": [
        "security/ir.model.access.csv",
        "views/student_consultancy_review_views.xml",
    ],
    "installable": True,
    "application": False,
}
