# Architecture

## Product Layers

- `addons/product/`: reusable Community-first student consultancy addons
- `addons/distributions/`: organization-specific overlays and defaults
- `ops/`: validation, deployment, local runtime, and packaging tooling

## Product Addons

- `student_consultancy_core`: technical foundation, curated mode, and shared navigation
- `student_consultancy_contacts`: consultancy-specific partner semantics
- `student_consultancy_cycles`: reusable semester, trimester, and quarter cycle engine
- `student_consultancy_hr`: canonical member, membership, department, and role domain
- `student_consultancy_recruitment`: openings, applications, and applicant conversion
- `student_consultancy_projects`: project records, staffing assignments, and CRM handoff
- `student_consultancy_reviews`: templates and review assignments
- `student_consultancy_website`: public API contract, intake endpoint, and website settings
- `student_consultancy_meta`: one-shot installer for the Community-first suite

## Distribution Addons

- `student_consultancy_180dc_escp`: ESCP branding, website defaults, and semester schema overlay
