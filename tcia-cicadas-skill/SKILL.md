---
name: TCIA CICADAS Skill
description: Guide users through creating comprehensive dataset descriptions using the Cancer Imaging Checklist for DAta Sharing (CICADAS).
---

# TCIA CICADAS Skill

## Overview
This Skill helps users draft high-quality dataset abstracts and descriptions for TCIA submissions. Following the CICADAS guidelines ensures that datasets are comprehensive, informative, and optimally discoverable.

## Documentation Structure
The skill guides the user through the following sections as defined at [cancerimagingarchive.net/cicadas](https://cancerimagingarchive.net/cicadas):

### 1. Title
- **Full Title**: Clear and concise (recommended <= 110 characters).
- **Short Title (Nickname)**: Brief identifier (< 30 characters), alphanumeric and dashes only.

### 2. Abstract (Maximum 1,000 Characters)
A brief overview including:
- Number of subjects.
- Types of imaging data.
- Types of non-imaging supporting data.
- Potential research applications.

### 3. Introduction
- Background, purpose, and uniqueness of the dataset.

### 4. Methods
Collect detailed information across these subsections:
- **Subject Inclusion and Exclusion Criteria**: Date ranges, demographics, clinical characteristics, and potential study bias.
- **Data Acquisition**:
    - **Radiology**: Scanner details (vendor, model), parameters (kVp, mA, dose), sequence details (TR, TE, TI, FOV), contrast agents, etc.
    - **Histopathology**: Fixation, staining, scanner info, resolution, and file formats.
    - **Clinical**: Capture process, standards used.
    - **Other/Missing Data**: Genomic/proteomic data and any gaps in completeness.
- **Data Analysis**:
    - **File Format Conversions**: Software/scripts used (e.g., DICOM to NIfTI).
    - **Image Preprocessing**: Normalization, registration, motion correction.
    - **Annotation/Segmentation Protocols**: Software, guidelines, and observer variability.
    - **Quality Control**: Automated or manual validation steps.
    - **Automated Analyses**: Radiomics, pipelines, and thresholds.
    - **Scripts, Code, and Software**: Specific versions and repository links.

### 5. Usage Notes
- Data organization and naming conventions.
- Training/test groupings or subsets.
- Instructions for specific file formats.
- Recommended software for viewing data.
- Known sources of error.

### 6. External Resources
- Links to related datasets, source code (GitHub), or tools stored outside of TCIA.

## Conversational Strategy
1. **Sectional Interview**: Don't overwhelm the user. Tackle one section at a time.
2. **Technical Probing**: For the Methods section, ask specific technical questions (e.g., "What was the magnetic field strength for the MRI scans?") based on the acquisition type.
3. **Refining**: Help the user refine their responses into professional, scientific prose.
4. **Validation**: Ensure the Abstract remains under the 1,000-character limit.
