import streamlit as st
import pandas as pd
import re
import tempfile
import requests

# Define permissible enumerations for certain fields
permissible_race = [
    "American Indian or Alaska Native", "Asian", "Black or African American",
    "Native Hawaiian or Other Pacific Islander", "Not Allowed To Collect",
    "Not Reported", "Unknown", "White"
]

permissible_ethnicity = [
    "Hispanic or Latino", "Not Allowed To Collect",
    "Not Hispanic or Latino", "Not Reported", "Unknown"
]

permissible_sex_at_birth = [
    "Don't know", "Female", "Intersex", "Male",
    "None of these describe me", "Prefer not to answer", "Unknown"
]

permissible_age_uom = ['Day', 'Month', 'Year']

# Define the required column headers
required_columns = [
    'Project Short Name', 'Case ID'
]

# Define the allowable column headers
allowable_columns = [
    'Project Short Name', 'Case ID', 'Race', 'Ethnicity', 'Sex at Birth',
    'Age at Diagnosis', 'Age at Enrollment', 'Age at Surgery',
    'Age at Earliest Imaging', 'Age UOM', 'Primary Diagnosis', 'Primary Site'
]

# Helper functions for validation
def validate_project_short_name(name):
    if len(name) > 32:
        return f"Exceeds 30 characters."
    if re.search(r"[^a-zA-Z0-9\s\-_]", name):
        return f"Contains special characters."
    return None

def validate_case_id(case_id):
    if len(case_id) > 30:
        return f"Exceeds 30 characters."
    if re.search(r"[^a-zA-Z0-9\s\-_]", case_id):
        return f"Contains invalid characters."
    return None

def validate_enumerated_field(value, permissible_values):
    invalid_values = []
    case_mismatched_values = []
    input_values = [v.strip() for v in value.split(';') if v.strip()]

    for input_value in input_values:
        if input_value.lower() not in [pv.lower() for pv in permissible_values]:
            invalid_values.append(input_value)
        else:
            correct_case_value = next(pv for pv in permissible_values if pv.lower() == input_value.lower())
            if input_value != correct_case_value:
                case_mismatched_values.append((input_value, correct_case_value))

    return invalid_values, case_mismatched_values

def convert_age_to_years(age_value, uom):
    if uom == 'Day':  # Days to years
        return round(age_value / 365.25, 1)
    elif uom == 'Month':  # Months to years
        return round(age_value / 12, 1)
    elif uom == 'Year':  # Already in years
        return round(age_value, 1)
    return None

# Function to check for correct column headers
def validate_headers(df):
    age_columns = [
        'Age at Diagnosis', 'Age at Enrollment', 'Age at Surgery', 'Age at Earliest Imaging'
    ]
    missing_columns = [col for col in required_columns if col not in df.columns]
    extra_columns = [col for col in df.columns if col not in allowable_columns]

    # Check if any 'Age at...' columns are present and 'Age UOM' is missing
    if any(col in df.columns for col in age_columns) and 'Age UOM' not in df.columns:
        missing_columns.append('Age UOM')

    if missing_columns:
        return False, f"Missing required columns: {', '.join(missing_columns)}"
    if extra_columns:
        st.warning(f"Warning: Unexpected columns found in the dataset: {', '.join(extra_columns)}")

    return True, None

# Summarize validation issues by column
def summarize_column_issues(issues):
    summary = ""
    for column, column_issues in issues.items():
        summary += f"**Column: {column}**\n"
        if 'enumerable' in column_issues:
            summary += f"- Allowed values: {', '.join(column_issues['allowed_values'])}\n"
            summary += f"- Illegal values found: {', '.join(set(column_issues['illegal_values']))} (Rows affected: {column_issues['rows_affected']})\n"
        elif 'free_text' in column_issues:
            summary += f"- {column_issues['requirement']}\n"
            summary += f"- Illegal values found: {', '.join(set(column_issues['illegal_values']))} (Rows affected: {column_issues['rows_affected']})\n"
        summary += "\n"
    return summary

# Function to validate and summarize data issues
def validate_data(df):
    log = []
    column_issues = {}
    case_mismatch_warnings = {}

    # Validate each required column
    for index, row in df.iterrows():
        # Validate Project Short Name
        if pd.notnull(row['Project Short Name']):
            result = validate_project_short_name(row['Project Short Name'])
            if result:
                column_issues.setdefault('Project Short Name', {'free_text': True, 'requirement': 'Must not exceed 30 characters or contain special characters (letters, numbers, spaces, dashes, and underscores allowed).', 'illegal_values': [], 'rows_affected': 0})
                column_issues['Project Short Name']['illegal_values'].append(row['Project Short Name'])
                column_issues['Project Short Name']['rows_affected'] += 1

        # Validate Case ID
        if pd.notnull(row['Case ID']):
            result = validate_case_id(row['Case ID'])
            if result:
                column_issues.setdefault('Case ID', {'free_text': True, 'requirement': 'Must not exceed 30 characters or contain special characters (except underscores and dashes).', 'illegal_values': [], 'rows_affected': 0})
                column_issues['Case ID']['illegal_values'].append(row['Case ID'])
                column_issues['Case ID']['rows_affected'] += 1

        # Validate Race
        if pd.notnull(row['Race']):
            invalid_values, case_mismatched = validate_enumerated_field(row['Race'], permissible_race)
            if invalid_values:
                column_issues.setdefault('Race', {'enumerable': True, 'allowed_values': permissible_race, 'illegal_values': [], 'rows_affected': 0})
                column_issues['Race']['illegal_values'].extend(invalid_values)
                column_issues['Race']['rows_affected'] += 1
            if case_mismatched:
                case_mismatch_warnings.setdefault('Race', [])
                case_mismatch_warnings['Race'].extend(case_mismatched)

        # Validate Ethnicity
        if pd.notnull(row['Ethnicity']):
            invalid_values, case_mismatched = validate_enumerated_field(row['Ethnicity'], permissible_ethnicity)
            if invalid_values:
                column_issues.setdefault('Ethnicity', {'enumerable': True, 'allowed_values': permissible_ethnicity, 'illegal_values': [], 'rows_affected': 0})
                column_issues['Ethnicity']['illegal_values'].extend(invalid_values)
                column_issues['Ethnicity']['rows_affected'] += 1
            if case_mismatched:
                case_mismatch_warnings.setdefault('Ethnicity', [])
                case_mismatch_warnings['Ethnicity'].extend(case_mismatched)

        # Validate Sex at Birth
        if pd.notnull(row['Sex at Birth']):
            invalid_values, case_mismatched = validate_enumerated_field(row['Sex at Birth'], permissible_sex_at_birth)
            if invalid_values:
                column_issues.setdefault('Sex at Birth', {'enumerable': True, 'allowed_values': permissible_sex_at_birth, 'illegal_values': [], 'rows_affected': 0})
                column_issues['Sex at Birth']['illegal_values'].extend(invalid_values)
                column_issues['Sex at Birth']['rows_affected'] += 1
            if case_mismatched:
                case_mismatch_warnings.setdefault('Sex at Birth', [])
                case_mismatch_warnings['Sex at Birth'].extend(case_mismatched)

    return column_issues, case_mismatch_warnings

# Set your page configuration
st.set_page_config(page_title="TCIA Clinical Data Validator", layout="wide")

# Logo URLs for light and dark mode
logo_light = "https://www.cancerimagingarchive.net/wp-content/uploads/2021/06/TCIA-Logo-01.png"
logo_dark = "https://www.cancerimagingarchive.net/wp-content/uploads/2021/06/TCIA-Logo-02.png"

# Custom CSS to switch logo based on the user's theme preference
st.sidebar.markdown(
    f"""
    <style>
    @media (prefers-color-scheme: dark) {{
        .logo {{
            content: url({logo_dark});
        }}
    }}
    @media (prefers-color-scheme: light) {{
        .logo {{
            content: url({logo_light});
        }}
    }}
    </style>
    <img class="logo" alt="App Logo">
    """,
    unsafe_allow_html=True
)

# main column title
st.title("Clinical Data Validator")

# User can either upload a file or enter a URL
st.sidebar.title("Upload your spreadsheet")
uploaded_file = st.sidebar.file_uploader("Upload an Excel, CSV, or TSV file", type=["xlsx", "csv", "tsv"])
sheet_url = st.sidebar.text_input("Or enter the URL of a Google Sheets, CSV, Excel, or TSV file")


# Function to load data from URL or file
def load_data_from_url(url):
    file_extension = url.split('.')[-1].lower()

    # Download the file
    try:
        response = requests.get(url)
        response.raise_for_status()  # Check if the URL is accessible

        if file_extension == 'xlsx':
            with tempfile.NamedTemporaryFile(suffix=".xlsx", delete=False) as tmp:
                tmp.write(response.content)
                tmp.seek(0)
                df = pd.read_excel(tmp.name)

        elif file_extension == 'csv':
            df = pd.read_csv(url)

        elif file_extension == 'tsv':
            df = pd.read_csv(url, sep='\t')

        else:
            st.error(f"Unsupported file format from URL: {file_extension}")
            return None

        return df

    except Exception as e:
        st.error(f"Error loading file from URL: {e}")
        return None

# Function to load data from file uploader
def load_data(uploaded_file):
    file_extension = uploaded_file.name.split('.')[-1].lower()

    if file_extension == 'xlsx':
        df = pd.read_excel(uploaded_file)
    elif file_extension == 'csv':
        df = pd.read_csv(uploaded_file)  # Default CSV handling
    elif file_extension == 'tsv':
        df = pd.read_csv(uploaded_file, sep='\t')  # Handle TSV (tab-separated)
    else:
        st.error("Unsupported file format")
        df = None
    return df

if uploaded_file is not None:
    df = load_data(uploaded_file)
    st.write("File uploaded successfully!")
elif sheet_url:
    df = load_data_from_url(sheet_url)
    if df is not None:
        st.write("Data loaded from URL successfully!")
else:
    df = None

# Check column headers before validation
if df is not None:
    headers_valid, header_error = validate_headers(df)
    if not headers_valid:
        st.error(header_error)
        df = None

# Run validation if file and headers are valid
if df is not None and st.button('Validate'):

    # Drop columns that are not in allowable_columns
    df = df[[col for col in df.columns if col in allowable_columns]]

    # Convert project short name and case id to strings and Sort by them
    df['Project Short Name'] = df['Project Short Name'].astype(str)
    df['Case ID'] = df['Case ID'].astype(str)
    df = df.sort_values(by=['Project Short Name', 'Case ID'])

    # Remove leading and trailing spaces from all values in the dataframe
    df = df.applymap(lambda x: x.strip() if isinstance(x, str) else x)

    # Run data validation steps
    column_issues, case_mismatch_warnings = validate_data(df)

    # Display validation issues
    if column_issues:
        st.error("Validation Errors Detected:")
        summary = summarize_column_issues(column_issues)
        st.markdown(summary)

    # Display case mismatch warnings
    if case_mismatch_warnings:
        st.warning("Validation Warnings Detected: (these will be automatically fixed after any errors are addressed)")
        for column, mismatches in case_mismatch_warnings.items():
            st.markdown(f"**{column}:**")
            # Unique mismatches
            unique_mismatches = list(set(mismatches))
            for original, correct in unique_mismatches:
                st.markdown(f"- '{original}' will be corrected to '{correct}'")

    # If no critical issues, allow downloading of the validated and corrected file
    if not column_issues:
        # Correct case mismatches in the DataFrame
        for column, mismatches in case_mismatch_warnings.items():
            unique_mismatches = list(set(mismatches))
            for original, correct in unique_mismatches:
                df[column] = df[column].replace(original, correct)

        # Save the corrected DataFrame
        with tempfile.NamedTemporaryFile(delete=False, suffix='.xlsx') as tmp:
            df.to_excel(tmp.name, index=False)
            tmp.seek(0)
            st.download_button(
                label="Download Validated and Corrected Excel File",
                data=tmp.read(),
                file_name="clinical-data-validated-corrected.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )

        if case_mismatch_warnings:
            st.success("Validation and automated cleanup complete.")
        else:
            st.success("Validation complete. No issues found.")
    else:
        st.error("Please correct the Validation Errors in your source data and try again.")
