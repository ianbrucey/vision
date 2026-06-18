# Technical Narrative Templates

## Purpose
Generate the custom, persuasive technical proposal narrative (Volume 2) that answers the Statement of Work, demonstrates understanding, showcases capabilities, and convinces the government evaluators that TalentNyk is the best choice. This is where AI-generated content meets human review to produce winning proposals.

## Inputs
- Solicitation SOW (from [[../04-solicitation-pipeline/sow-extraction]])
- Section L instructions (volume structure, page limits)
- Section M evaluation criteria (what the government values most)
- Selected vendor profiles and past performance snippets
- Selected Key Personnel resumes
- TalentNyk's management approach and capabilities

## Outputs
- Complete technical proposal narrative
- Section-by-section formatted content
- Page-limit-compliant output
- Customized to the specific solicitation (NOT generic boilerplate)

## Narrative Sections (Typical RFP Structure)

### 1. Executive Summary (1-2 pages)
- Understanding of the government's need
- Overview of the proposed solution
- Why TalentNyk + selected vendor = best value
- Key differentiators

### 2. Technical Approach (core section)
- Detailed response to each SOW work element
- Methodology, process, quality control
- Innovation and efficiency improvements
- Risk mitigation strategies
- Each work element response → maps to evaluation subfactors if possible

### 3. Management & Staffing Plan
- Organizational structure for the contract
- Key Personnel profiles (resumes + qualifications summary)
- Staffing levels, labor categories, and hours
- Subcontractor management approach
- Transition plan (if taking over from incumbent)

### 4. Past Performance (may be separate volume)
- Selected past performance references
- Relevance narrative for each reference
- CPARS/performance quality summary
- "Why this past performance proves we can do this job"

### 5. Quality Control Plan
- QC processes, inspections, acceptance criteria
- Corrective action procedures
- Performance metrics and reporting

### 6. Safety Plan (if applicable)
- OSHA compliance
- Site-specific safety protocols
- Safety record and statistics

## Generation Approach

### LLM-Powered Drafting
1. Feed: SOW + Section M + vendor profiles + past performance + TalentNyk boilerplate
2. Prompt engineered per section type
3. LLM drafts section-by-section within page limits
4. Content is anchored to specific SOW requirements (not generic)

### Page Limit Enforcement
- System tracks total pages per volume
- Flags when content exceeds limits
- Suggests cuts or condensing

### Evaluation Criteria Alignment
- Section M parsed criteria → narrative sections tagged with which evaluation factor they address
- Ensures every evaluation factor is explicitly answered

## Template System

### Reusable Components
- **Management approach boilerplate:** Standardized sections about TalentNyk's management methodology
- **Quality control boilerplate:** Standard QC processes
- **Corporate overview:** TalentNyk's capabilities and credentials
- These are starting points, not final text — LLM customizes per solicitation

### Solicitation-Specific Customization
- All technical content is drafted fresh against the specific SOW
- Past performance snippets selected specifically for this solicitation
- Key Personnel highlights tailored to evaluation criteria

## Human-in-the-Loop

- AI drafts the narrative
- Proposal Manager reviews, edits, and approves
- AI does NOT auto-submit without human approval
- Final narrative is a collaboration between AI speed and human judgment

## Dependencies
- [[../04-solicitation-pipeline/sow-extraction]]
- [[../04-solicitation-pipeline/section-l-parser]]
- [[../04-solicitation-pipeline/section-m-parser]]
- [[../05-matching-engine/vendor-matching-algorithm]]
- [[past-performance-compiler]]
- [[multi-volume-assembler]]

## Key Rules & Compliance
- FAR 15.305: Evaluation of proposals — evaluators score against stated criteria
- Generic boilerplate scores poorly; specific, SOW-anchored responses score well
- Page limits are hard limits — exceeding them risks pages not being evaluated
- All claims must be true and verifiable — false claims = False Claims Act

## Open Questions
- Should the system maintain a "winning proposals" library for few-shot LLM prompting?
- How much of the narrative should be AI-generated vs. human-written?
- Should the system generate a "red team" critique of the narrative before submission?
