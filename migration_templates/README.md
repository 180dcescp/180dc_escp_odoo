# 180DC ESCP Migration Templates (Native-First Structure)

## Import order
1. `contacts_companies_template.csv` -> `res.partner` (companies)
2. `contacts_people_template.csv` -> `res.partner` (people, linked to parent company)
3. `recruitment_candidates_template.csv` -> `hr.candidate`
4. `applicants_import_template.csv` -> `hr.applicant`
5. `members_import_template.csv` -> `hr.employee`
6. `crm_opportunities_template.csv` -> `crm.lead` (type=opportunity)
7. `project_shells_template.csv` -> `project.project`

## Controlled vocabularies
- Departments: Presidency, Business Development, People & Organisation, Marketing, Finance, Operations, Consulting, Consultants
- Positions: President, Vice-President, Head of, Associate Director, Project Leader, Senior Consultant, Consultant
- Campuses (`escp_campus`): berlin, gap_exchange, london, madrid, paris, turin
- Programs (`escp_program`): specialized_master, mim, bim, mba
- Employee status (`escp_member_status`): active, internal_move, alumni, left
- Applicant status (`escp_applicant_status`): applicant, internal_recruitment, accepted, rejected

## Stages
Recruitment (`hr.recruitment.stage`):
- Application Form
- Screening (CV + Essay)
- Interview (Case)
- Decision
- Accepted
- Rejected

CRM (`crm.stage`):
- OPEN - Uncontacted
- OPEN - Contacted
- Negotiation
- Won
- Lost

## Notes
- This structure is automation-free by design.
- Candidate creation is explicit and imported first.
- Projects are shell records (metadata, contract/scoping status, links to Drive/Slack), not task-workspace replacements.
