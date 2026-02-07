# TCIA Remapping Skill

## Metadata
name: TCIA Remapping Skill
description: Guide users through remapping their data to the TCIA imaging submission data model and generating standardized TSVs.

## Overview
This Skill assists users in transforming their original clinical and imaging research data into the standardized TCIA (The Cancer Imaging Archive) data model. It facilitates the mapping of source columns to target properties across multiple entities (e.g., Subject, Diagnosis, Radiology) and ensures compliance with permissible values for key fields.

## Target Data Model
The skill target consists of 12 potential TSV files defined in the `resources/schema.json` file:
- Program
- Dataset
- Subject
- Procedure
- File
- Diagnosis
- Investigator
- Related_Work
- Radiology
- Histopathology
- Multiplex_Imaging
- Multiplex_Channels

## How to use this Skill
1. **Initiation**: Ask the user to upload their source data files (CSV, XLSX, or TSV).
2. **Analysis**: Analyze the uploaded files to understand the existing columns and data structure.
3. **Column Mapping**: Propose a mapping between the source columns and the properties defined in `resources/schema.json`. Ask the user to confirm or adjust the mapping.
4. **Value Standardization**:
    - For `race`, `ethnicity`, and `sex_at_birth`, ensure values match the permissible lists in `resources/permissible_values.json`.
    - For `primary_diagnosis` and `primary_site`, perform fuzzy matching against the lists in `resources/permissible_values.json` and ask the user to confirm corrections.
    - Handle "NOS" (Not Otherwise Specified) by suggesting the most appropriate standard term if a direct match isn't found.
5. **Transformation**: Apply any necessary transformations (e.g., ensuring numeric fields are valid, formatting dates).
6. **Output Generation**: Once remapping is confirmed, generate and provide the standardized TSV files for the user to download.

## Key Rules
- Always refer to `resources/schema.json` for the authoritative property names and requirements.
- Prioritize required fields (marked "R" in the schema).
- If a value doesn't match a permissible list, suggest the closest match and ask for confirmation.
- If multiple source files are provided, identify how they relate to the different target TSVs.

## Examples
### Example 1: Mapping Race
Source data has "Caucasian".
Claude: "I see 'Caucasian' in your Race column. The standard TCIA value is 'White'. Should I remap this for you?"

### Example 2: Mapping Primary Diagnosis
Source data has "Glioblastoma Multiforme".
Claude: "I found 'Glioblastoma Multiforme' in your diagnosis column. The standard value in our model is 'Glioblastoma'. Should I use that?"

## Resources
- `resources/schema.json`: The complete property definitions for all target TSVs.
- `resources/permissible_values.json`: The lists of valid values for key categorical fields.
- `remap_helper.py`: A Python script providing utility functions for fuzzy matching, validation, and splitting data according to the schema.
