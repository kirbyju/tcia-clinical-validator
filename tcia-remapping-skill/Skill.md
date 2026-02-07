# TCIA Remapping Skill

## Metadata
name: TCIA Remapping Skill
description: Guide users through remapping their data to the TCIA imaging submission data model and generating standardized TSVs using ontologies and a tiered conversational flow.

## Overview
This Skill assists users in transforming their original clinical and imaging research data into the standardized TCIA (The Cancer Imaging Archive) data model. It leverages medical ontologies (NCIt, UBERON, SNOMED) and a structured conversational flow to ensure high-quality data mapping and standardization.

## Target Data Model
The skill target consists of 12 potential TSV files defined in the `resources/schema.json` file:
- Program, Dataset, Subject, Procedure, File, Diagnosis, Investigator, Related_Work, Radiology, Histopathology, Multiplex_Imaging, Multiplex_Channels.

## Conversational Workflow
To minimize user effort, the skill follows a tiered approach:

### Phase 1: Structure Mapping & Organization
1. **Initiation**: Ask the user to upload their source data files.
2. **Analysis**: Identify existing columns and how they relate to the target entities.
3. **Summary Recommendation**: Provide a concise summary of the proposed mapping (e.g., "Source 'PtID' -> Target 'subject_id'").
4. **Quick Approval**: Allow the user to approve the entire structure mapping at once (e.g., "Everything looks good!") or flag specific items for discussion (e.g., "Discuss items 2 and 5").

### Phase 2: Value Standardization (Permissible Values)
Once the structure is confirmed, address data content one TSV/column at a time:
1. **Batch Validation**: For each confirmed column, identify values that do not match the permissible lists in `resources/permissible_values.json`.
2. **Ontology-Enhanced Matching**: Use both fuzzy matching and knowledge of medical ontologies (NCIt, SNOMED, UBERON) to suggest corrections.
3. **Focussed Discussion**: Present a summary of auto-corrected values for quick approval, and list only the "hard" cases that need manual user intervention.
4. **Handling "NOS"**: If a value is "NOS" (Not Otherwise Specified), suggest the most appropriate standard term from the ontology.

## Key Rules
- **Ontology Integration**: When a direct match is missing, use NCIt or UBERON codes (found in `permissible_values.json`) to verify if a user's term is a synonym of a standard term.
- **Tiered Interaction**: Always provide a summary first. Don't ask about 100 values one by one; group them.
- **Required Fields**: Prioritize fields marked "R" in `schema.json`.

## Examples
### Example: Tiered Approval
Claude: "I've mapped your 15 columns to the Subject and Diagnosis TSVs. Here is the summary: [Table]. Does this look good, or should we adjust specific mappings?"
User: "Looks good, proceed to values."
Claude: "Great. In 'primary_site', I've auto-matched 90% of your values. I have 3 values that need your attention: 'Lung, NOS', 'Chest wall', and 'Unknown'. Recommendations: [List]. How should we handle these?"

## Resources
- `resources/schema.json`: Complete property definitions.
- `resources/permissible_values.json`: Valid values with ontology metadata (NCIt, UBERON).
- `remap_helper.py`: Utility script for fuzzy matching and data splitting.
