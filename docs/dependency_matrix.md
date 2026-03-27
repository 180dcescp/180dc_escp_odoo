# Dependency Matrix

## Product suite

### Community-safe product addons

- `student_consultancy_core`
- `student_consultancy_contacts`
- `student_consultancy_cycles`
- `student_consultancy_hr`
- `student_consultancy_recruitment`
- `student_consultancy_projects`
- `student_consultancy_reviews`
- `student_consultancy_website`
- `student_consultancy_meta`

### Distribution addon

- `student_consultancy_180dc_escp`

## Recommended graph

- `student_consultancy_cycles` -> `student_consultancy_core`
- `student_consultancy_contacts` -> `student_consultancy_core`
- `student_consultancy_hr` -> `student_consultancy_core`, `student_consultancy_cycles`, `student_consultancy_contacts`
- `student_consultancy_recruitment` -> `student_consultancy_core`, `student_consultancy_cycles`, `student_consultancy_contacts`, `student_consultancy_hr`
- `student_consultancy_projects` -> `student_consultancy_core`, `student_consultancy_cycles`, `student_consultancy_contacts`, `student_consultancy_hr`, `crm`
- `student_consultancy_reviews` -> `student_consultancy_core`, `student_consultancy_cycles`, `student_consultancy_hr`, `student_consultancy_projects`
- `student_consultancy_website` -> `student_consultancy_core`, `student_consultancy_contacts`, `student_consultancy_hr`, `student_consultancy_recruitment`, `student_consultancy_projects`, `website`
