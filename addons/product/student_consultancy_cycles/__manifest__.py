{
    "name": "Student Consultancy Cycles",
    "summary": "Reusable cycle engine for semester, trimester, and quarter-based operations",
    "version": "18.0.1.0.0",
    "category": "Services",
    "author": "180 Degrees Consulting ESCP",
    "website": "https://github.com/180dc-escp/odoo-student-consultancy",
    "license": "LGPL-3",
    "depends": ["student_consultancy_core"],
    "data": [
        "security/ir.model.access.csv",
        "views/student_consultancy_cycle_views.xml",
    ],
    "installable": True,
    "application": False,
}
