# tcia-clinical-validator

A streamlit validator to ensure Common Data Element compliance for submitting clinical data to TCIA.

## Tools Available

This repository contains two Streamlit applications:

### 1. TCIA Clinical Data Validator (`tcia-clinical-validator.py`)
The original validator that ensures your clinical data meets TCIA Common Data Element (CDE) compliance requirements.

**To run:**
```bash
streamlit run tcia-clinical-validator.py
```

### 2. TCIA Dataset Remapper (`tcia-remapper.py`)
An interactive tool that helps transform clinical and imaging research data into the standardized TCIA data model using a tiered conversational workflow.

**To run:**
```bash
streamlit run tcia-remapper.py
```

**Features:**
- **Phase 0**: Dataset-level metadata collection (Program, Dataset, Investigator, Related Work)
- **Phase 1**: Structure mapping - map source columns to TCIA target properties
- **Phase 2**: Value standardization using ontology-enhanced matching (NCIt, UBERON, SNOMED)

See [REMAPPER_README.md](REMAPPER_README.md) for detailed usage instructions.

## Installation

Install the required dependencies:

```bash
pip install -r requirements.txt
```

## Testing

To test the remapper functionality:

```bash
python test_remapper.py
```

## Resources

- [TCIA (The Cancer Imaging Archive)](https://www.cancerimagingarchive.net/)
- [TCIA Submission Guidelines](https://www.cancerimagingarchive.net/submit-data/)

