# Install

## Community-first suite

1. Add the repository's addon paths to Odoo:
   - `addons/product`
   - `addons/distributions`
2. Install `student_consultancy_meta`.
3. Optionally install `student_consultancy_180dc_escp` for the ESCP defaults.

## Required Odoo apps

The current Community-first suite expects:

- Contacts
- CRM
- Website

The suite does not use `hr.employee` or payroll contracts as canonical people models. Instead it installs custom `student.consultancy.*` records on top of `res.partner`.
