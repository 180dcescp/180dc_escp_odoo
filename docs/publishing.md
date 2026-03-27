# Publishing

## Release channels

- GitHub releases are a first-class distribution channel
- Odoo Apps packaging is kept compatible from the same source tree

## Packaging rules enforced in this repo

- every `student_consultancy_*` addon has a manifest
- every `student_consultancy_*` addon has `README.rst`
- every `student_consultancy_*` addon has `static/description/index.html`
- every non-meta `student_consultancy_*` addon has tests

## Release policy

- Odoo 18 only
- Community Edition only
- one consultancy per Odoo instance
- core stays technical and small
- organization-specific behavior belongs in distribution addons, not reusable product modules
