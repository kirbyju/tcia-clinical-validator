# Suggestions for Aligning TCIA Apps with NCI Imaging Submission Model

Based on the recent updates to the NCI Imaging Submission Model (MDF format) and the review of the current Streamlit applications, here are suggestions for further alignment and improvements:

## 1. MDF-Driven Proposal Form
Currently, `tcia-dataset-proposal.py` uses hardcoded labels and selection lists (e.g., `image_types`, `supporting_data`, `why_tcia`).
- **Suggestion**: Work with model maintainers to incorporate these fields into the MDF model's `Nodes` and `PropDefinitions`.
- **Benefit**: This would allow the Proposal app to be fully data-driven. Changes to the proposal questions or permissible values would only require updating the MDF YAML files, not the application code.

## 2. Automated Resource Synchronization
The apps rely on local copies of the MDF YAML files.
- **Suggestion**: Implement a "Check for Updates" feature or a CLI utility that fetches the latest files from the [CBIIT GitHub repository](https://github.com/CBIIT/nci-imaging-submission-model).
- **Benefit**: Ensures that users are always working with the most up-to-date version of the submission model without requiring manual file replacement.

## 3. Enhanced Relationship-Based Validation
The new model version (0.0.2) introduced standardized relationships (e.g., `of_Subject`, `of_Dataset`).
- **Suggestion**: Extend the validator to perform cross-entity referential integrity checks.
- **Example**: If a `File` record references `subject.subject_id = 'S001'`, the validator should check if 'S001' exists in the `Subject` entity data.
- **Benefit**: Catches linking errors early in the remapping process, reducing the need for manual cleanup later.

## 4. Integration of DOI and ORCID Metadata into MDF
The apps currently use Crossref and ORCID APIs to fetch metadata.
- **Suggestion**: The MDF `Terms` section could be expanded to include mappings to these external metadata standards.
- **Benefit**: Standardizes how external metadata is mapped to internal properties across different tools using the MDF.

## 5. Metadata Conflict Resolution
The current conflict detection flags differences between Phase 0 metadata and uploaded data.
- **Suggestion**: Provide a UI-driven way to resolve these conflicts (e.g., "Use uploaded value" vs "Keep initial value") and update the metadata dynamically.
- **Benefit**: Improves the user experience when source data files contain more accurate or updated information than the initial proposal.
