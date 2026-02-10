# TCIA Dataset Remapper

The TCIA Dataset Remapper is an interactive Streamlit application that helps users transform their clinical and imaging research data into the standardized TCIA (The Cancer Imaging Archive) data model.

## Features

- **Phase 0: Dataset-Level Metadata Collection** - Collect high-level metadata for Program, Dataset, Investigator, and Related Work entities
- **Phase 1: Structure Mapping** - Map source data columns to TCIA target properties
- **Phase 2: Value Standardization** - Standardize data values using ontology-enhanced matching (NCIt, UBERON, SNOMED)

## Quick Start

### Prerequisites

Install the required dependencies:

```bash
pip install -r requirements.txt
```

### Running the Remapper

To launch the TCIA Dataset Remapper:

```bash
streamlit run tcia-remapper.py
```

The application will open in your default web browser at `http://localhost:8501`.

### Running the Original Validator

To launch the original TCIA Clinical Data Validator:

```bash
streamlit run tcia-clinical-validator.py
```

## Usage Guide

### Phase 0: Dataset-Level Metadata Collection

1. **Program Information**: Enter program details (most users should use "Community")
2. **Dataset Information**: Provide dataset description, abstract, participant count, etc.
3. **Investigator Information**: Add one or more investigators with contact details
4. **Related Work**: Add publications, DOIs, and related work references
5. **Review & Generate**: Review all metadata and generate TSV files

### Phase 1: Structure Mapping & Organization

1. Upload your source data file (CSV, TSV, or Excel)
2. Preview your data to verify it loaded correctly
3. Map each source column to a TCIA target property
4. Confirm the mapping to proceed to value standardization

### Phase 2: Value Standardization

1. Review validation issues for each target entity
2. View suggested corrections based on fuzzy matching and ontology knowledge
3. Apply corrections or manually resolve issues
4. Download the standardized TSV files

## Output Files

The remapper generates standardized TSV files in the `output/` directory:

- `program.tsv` - Program metadata
- `dataset.tsv` - Dataset metadata  
- `investigator.tsv` - Investigator information
- `related_work.tsv` - Related publications and work
- `subject.tsv`, `diagnosis.tsv`, etc. - Data entities extracted from uploaded files

## TCIA Data Model

The remapper supports the following TCIA entities:

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

Complete schema definitions can be found in `tcia-remapping-skill/resources/schema.json`.

## Ontology Support

The remapper uses permissible values with ontology codes from:

- **NCIt** (NCI Thesaurus) - Cancer-related terminology
- **UBERON** - Anatomical structures
- **SNOMED** - Clinical terminology

Permissible values are defined in `tcia-remapping-skill/resources/permissible_values.json`.

## Helper Functions

The `tcia-remapping-skill/remap_helper.py` module provides utility functions:

- `load_json()` - Load JSON configuration files
- `get_closest_match()` - Find closest matching permissible value
- `validate_dataframe()` - Validate data against permissible values
- `split_data_by_schema()` - Split source data into target entities
- `write_metadata_tsv()` - Generate TSV files from metadata
- `check_metadata_conflict()` - Detect conflicts between metadata sources

## Troubleshooting

### Import Issues

If you encounter import errors, ensure you're running the application from the repository root directory.

### Missing Permissible Values

If validation reports many missing values, you may need to:
1. Check if your terminology matches the TCIA permissible values
2. Use the fuzzy matching suggestions
3. Map custom values to standard terms manually

## Contributing

When making changes to the remapper:

1. Ensure schema and permissible values files are kept in sync
2. Test with various data formats (CSV, TSV, Excel)
3. Verify generated TSV files comply with TCIA standards
4. Update documentation for new features

## Resources

- [TCIA (The Cancer Imaging Archive)](https://www.cancerimagingarchive.net/)
- [NCI Thesaurus (NCIt)](https://ncithesaurus.nci.nih.gov/)
- [UBERON Anatomy Ontology](http://uberon.github.io/)
- [SNOMED CT](https://www.snomed.org/)
