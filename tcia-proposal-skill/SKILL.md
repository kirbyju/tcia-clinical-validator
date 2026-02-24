---
name: TCIA Dataset Proposal Skill
description: Guide users through proposing a new dataset or analysis results for TCIA, collecting all necessary metadata, and generating a standardized proposal package.
---

# TCIA Dataset Proposal Skill

## Overview
This Skill assists users in preparing a formal proposal for publishing a new dataset or analysis results on The Cancer Imaging Archive (TCIA). It mirrors the logic and requirements of the `tcia-dataset-proposal.py` application.

## Workflow

### 1. Proposal Type Selection
Determine the type of submission:
- **New Collection Proposal**: For contributing original imaging data not previously on TCIA.
- **Analysis Results Proposal**: For contributing derived data (segmentations, annotations, radiomics) based on existing TCIA collections.

### 2. Contact Information
Collect Name and Email for three mandatory Points of Contact (POC):
- **Scientific POC**: Primary contact for proposal and data collection.
- **Technical POC**: Person responsible for data transfer.
- **Legal POC**: Authorized signatory for the Data Submission Agreement (should not be the PI).

### 3. Dataset Publication Details
- **Title**: Descriptive title for the dataset.
- **Nickname**: Short identifier (< 30 characters, alphanumeric and dashes only).
- **Authors**: List of authors. **Action**: Encourage providing ORCIDs. Use `orcid_helper.py` logic to validate and fetch profile details.
- **Abstract**: Brief overview of the dataset (Max 1,000 characters). **Steering**: Refer to `tcia-cicadas-skill` for high-quality abstract generation.

### 4. Data Collection Details
- **Published Elsewhere**: Has the data been published? If so, why TCIA?
- **Adaptive Fields (New Collection)**:
    - Primary disease site/location (from `permissible_values.json`).
    - Histologic diagnosis (from `permissible_values.json`).
    - Image types (MR, CT, PET, etc.).
    - Supporting data (Clinical, Genomics, Radiation Therapy Plans/Structures, etc.).
    - Software/Related Resources:Standalone question about source code, Jupyter notebooks, web sites or other software.
    - File formats.
    - Modifications prior to submission.
    - Presence of patient faces.
- **Adaptive Fields (Analysis Results)**:
    - TCIA collection(s) analyzed.
    - Types of derived data.
    - Specificity of image records.
    - File formats.

### 5. Additional Metadata
- **Disk Space**: Approximate size.
- **Time Constraints**: Any deadlines for sharing.
- **Publications**: Related dataset descriptors or derived publications.
- **Acknowledgements**: Funding or support statements.
- **Why TCIA**: Motivation for using TCIA.

## Output Generation
The goal is to generate a ZIP package containing:

1. **Proposal Summary TSV**: `{nickname}_proposal_summary_{date}.tsv`
   - A single-row TSV containing all responses mapped to the labels in `tcia-dataset-proposal.py`.
2. **Investigators TSV**: `{nickname}_investigators_{date}.tsv`
   - A TSV containing investigator metadata (first_name, last_name, person_orcid, organization_name, email).
3. **Proposal Summary DOCX**: `{nickname}_proposal_summary_{date}.docx`
   - A formatted document using full-text question labels as headers.
4. **Updated PDF Agreement**: `{nickname}_agreement_updated_{date}.pdf`
   - A copy of the TCIA Data Submission Agreement with "Exhibit A" (Page 6) replaced by the dataset abstract.

## Logic Reference
For specific implementation details on file generation and validation, refer to:
- `tcia-dataset-proposal.py`: Main application logic and file generation.
- `tcia-remapping-skill/orcid_helper.py`: ORCID validation and lookup.
- `tcia-remapping-skill/resources/agreement_template.pdf`: PDF template.
- `tcia-remapping-skill/resources/permissible_values.json`: Controlled vocabularies for sites and diagnoses.
