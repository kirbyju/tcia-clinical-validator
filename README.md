# NCI Imaging Submission Validator & Proposal Tools

This repository contains tools designed to facilitate the submission of imaging and clinical research data to the National Cancer Institute (NCI).

## Problem & Solution

Researchers often have imaging and clinical data in diverse formats with inconsistent column names, non-standard values, and unclear entity relationships. These tools automate the transformation to the standardized NCI Imaging Submission Model, reducing manual effort and ensuring data quality.

## Tools Available

### 1. NCI Imaging Submission Validator (`tcia-remapper.py`)
An interactive tool that helps transform clinical and imaging research data into the standardized NCI Imaging Submission Model using a tiered conversational workflow.

**Purpose:** Convert messy, heterogeneous data into standardized submission-ready datasets.

**To run:**
```bash
streamlit run tcia-remapper.py
```

**Features:**
- **Phase 0: Summary Metadata**: Collect high-level metadata for Program, Dataset, Investigator, and Related Work. Supports importing data from the Dataset Proposal Form.
- **Phase 1: Column Headers**: Map your source data columns to target entities. Inter-entity linkages are automatically handled.
- **Phase 2: Permissible Values**: Standardize data values using ontology-enhanced matching (NCIt, UBERON, SNOMED) and generate standardized TSV files.

### 2. TCIA Dataset Proposal Form (`tcia-dataset-proposal.py`)
A streamlined application for researchers to propose new imaging collections or analysis results to TCIA.

**Purpose:** Create structured proposal packages with pre-filled submission agreements to initiate new TCIA datasets.

**To run:**
```bash
streamlit run tcia-dataset-proposal.py
```

**Features:**
- Collects necessary contact information and dataset details.
- Automatically generates a proposal package including a summary TSV, a DOCX summary, and a pre-filled Data Submission Agreement (PDF).
- The generated TSV can be imported directly into the **NCI Imaging Submission Validator** to pre-populate metadata.

## Installation

Install the required dependencies:

```bash
pip install -r requirements.txt
```

## Data Model & Ontology Support

These tools standardize data across 12 entity types: Program, Dataset, Study, Series, Image, Patient, Specimen, Diagnosis, Treatment, Adverse Event, Biomarker, and Related Work. This 12-entity model enables rich description of imaging research while maintaining interoperability with NCI systems.

The tools are built upon the [NCI Imaging Submission Model](https://github.com/CBIIT/nci-imaging-submission-model).

Value standardization leverages the following ontologies:
- **NCIt** (NCI Thesaurus) - Cancer-related terminology
- **UBERON** - Anatomical structures
- **SNOMED CT** - Clinical terminology

## Resources

- [TCIA (The Cancer Imaging Archive)](https://www.cancerimagingarchive.net/)
- [TCIA Submission Guidelines](https://www.cancerimagingarchive.net/submit-data/)
- [CICADAS Checklist](https://cancerimagingarchive.net/cicadas)
