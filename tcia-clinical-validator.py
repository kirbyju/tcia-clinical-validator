import streamlit as st
import pandas as pd
import numpy as np
from io import BytesIO
import re

st.set_page_config(page_title="TCIA Clinical Data Validator")

# Permissible columns and enumerations
required_columns = ['Project Short Name', 'Case ID']
allowable_columns = [
    'Project Short Name', 'Case ID', 'Race', 'Ethnicity', 'Sex at Birth',
    'Age at Diagnosis', 'Age at Enrollment', 'Age at Surgery','Age UOM',
    'Primary Diagnosis', 'Tissue or Organ of Origin'
]

def reset_session_state():
    """Reset all session state variables to their initial values"""
    # Core step tracking
    st.session_state.step = 1
    st.session_state.project_short_name = ''
    st.session_state.age_uom = ''

    # Column mapping related states
    st.session_state.columns_mapped = False
    st.session_state.column_mapping = {}
    st.session_state.mapping_applied = False

    # Categorical validation states
    if 'kept_values' in st.session_state:
        del st.session_state.kept_values
    if 'fix_column_states' in st.session_state:
        del st.session_state.fix_column_states

    # Clear validation mappings
    if 'mapping_complete' in st.session_state:
        del st.session_state.mapping_complete
    if 'value_mappings' in st.session_state:
        del st.session_state.value_mappings

    # Primary Diagnosis and Tissue/Organ mapping states - Added explicit clearing
    if 'primary_diagnosis_mapped' in st.session_state:
        del st.session_state.primary_diagnosis_mapped
    if 'primary_diagnosis_mappings' in st.session_state:
        del st.session_state.primary_diagnosis_mappings
    if 'tissue_organ_mapped' in st.session_state:
        del st.session_state.tissue_organ_mapped
    if 'tissue_organ_mappings' in st.session_state:
        del st.session_state.tissue_organ_mappings

    # Clear the dataframe if it exists
    if 'df' in st.session_state:
        del st.session_state.df

    # Clear any skip flags or other dynamic states
    keys_to_remove = []
    for key in st.session_state.keys():
        if (key.startswith('skip_') or
            key.startswith('Race_') or
            key.startswith('Age_') or
            key.startswith('Primary_Diagnosis_') or
            key.startswith('Tissue_or_Organ_') or
            key.startswith('fix_')):
            keys_to_remove.append(key)

    for key in keys_to_remove:
        del st.session_state[key]

# Function to read and process permissible value lists for primary diagnosis and tissue of origin
def load_permissible_values(file_path):
    try:
        df = pd.read_excel(file_path)
        # Assuming 'Permissible Value' is the column name
        values = df['Permissible Value'].dropna().unique().tolist()
        # Sort values for easier lookup
        return sorted(values)
    except Exception as e:
        st.error(f"Error loading permissible values from {file_path}: {str(e)}")
        return []

# Load permissible values at app startup
@st.cache_data
def initialize_permissible_values():
    primary_diagnosis_values = load_permissible_values('primary_diagnosis_caDSR_6161032.xlsx')
    tissue_organ_values = load_permissible_values('tissue_or_organ_of_origin_caDSR_6161035.xlsx')
    return primary_diagnosis_values, tissue_organ_values

# Load the permissible values for Primary Diagnosis and Tissue/Organ of Origin
permissible_primary_diagnosis, permissible_tissue_or_organ = initialize_permissible_values()

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

# Conversion factors for Age UOM
age_uom_factors = {
    'Day': 1 / 365,
    'Month': 1 / 12,
    'Year': 1
}

# convert non-age columns to strings
def convert_to_strings(df):
    age_columns = ['Age at Diagnosis', 'Age at Enrollment', 'Age at Surgery', 'Age at Earliest Imaging']
    for col in df.columns:
        if col not in age_columns:
            df[col] = df[col].astype(str)
    return df

# Helper to validate and clean data
def validate_and_clean_data(df):
    report = []

    # Convert non-age columns to strings
    df = convert_to_strings(df)

    # Fix case sensitivity issues
    for col in ['Ethnicity', 'Sex at Birth']:
        if col in df.columns:
            df[col] = df[col].str.title().str.strip()

    # Handle multiple Race values
    if 'Race' in df.columns:
        df['Race'] = df['Race'].apply(lambda x: ';'.join(sorted(set([r.strip().title() for r in str(x).split(';')]))))

    # Drop duplicate rows and report their original row numbers
    duplicate_rows = df[df.duplicated()].index.tolist()
    if duplicate_rows:
        df.drop_duplicates(inplace=True)
        report.append(f"Removed {len(duplicate_rows)} duplicate rows: {duplicate_rows}")

    return df, report

def validate_categorical_data(df):
    # Define which columns are required vs optional
    required_categorical_columns = {
        'Ethnicity': permissible_ethnicity,
        'Sex at Birth': permissible_sex_at_birth,
        'Age UOM': permissible_age_uom,
    }

    optional_categorical_columns = {
        'Primary Diagnosis': permissible_primary_diagnosis,
        'Tissue or Organ of Origin': permissible_tissue_or_organ
    }

    corrections = {}

    # Initialize session state for kept values and mapping states
    if 'kept_values' not in st.session_state:
        st.session_state.kept_values = {}
    if 'fix_column_states' not in st.session_state:
        st.session_state.fix_column_states = {}
    if 'mapping_complete' not in st.session_state:
        st.session_state.mapping_complete = {}
    if 'value_mappings' not in st.session_state:
        st.session_state.value_mappings = {}

    # Function to find invalid values in a column
    def get_invalid_values(series, valid_values):
        valid_values_dict = {v.lower(): v for v in valid_values}
        invalid_mask = ~series.apply(lambda x: pd.isna(x) or
                                   str(x).lower() in valid_values_dict)
        return series[invalid_mask].unique()

    # Handle required categorical columns first
    for col, valid_values in required_categorical_columns.items():
        if col in df.columns:
            valid_values_dict = {v.lower(): v for v in valid_values}

            def correct_case(value):
                if pd.isna(value):
                    return value
                value_lower = str(value).lower()
                return valid_values_dict.get(value_lower, value)

            df[col] = df[col].apply(correct_case)
            invalid_values = get_invalid_values(df[col], valid_values)

            if len(invalid_values) > 0:
                st.markdown(f"#### Found {len(invalid_values)} invalid values in {col} (required field)")
                corrections[col] = {}
                for invalid_value in invalid_values:
                    correct_value = st.selectbox(
                        f"Correct value for '{invalid_value}' in {col}:",
                        options=valid_values,
                        key=f"{col}_{invalid_value}"
                    )
                    if correct_value:
                        corrections[col][invalid_value] = correct_value

    # Handle optional categorical columns
    for col, valid_values in optional_categorical_columns.items():
        if col in df.columns:
            # Initialize column-specific session state
            if col not in st.session_state.mapping_complete:
                st.session_state.mapping_complete[col] = False
            if col not in st.session_state.value_mappings:
                st.session_state.value_mappings[col] = {}

            valid_values_dict = {v.lower(): v for v in valid_values}

            # Apply case correction first
            df[col] = df[col].apply(lambda x: valid_values_dict.get(str(x).lower(), x)
                                  if pd.notna(x) else x)

            # Get all invalid values
            all_invalid_values = get_invalid_values(df[col], valid_values)

            if len(all_invalid_values) > 0 and not st.session_state.mapping_complete[col]:
                st.markdown(f"#### Found {len(all_invalid_values)} non-standard values in {col}")

                # Show example values
                if len(all_invalid_values) > 5:
                    example_values = ', '.join(f"'{v}'" for v in all_invalid_values[:5]) + f", and {len(all_invalid_values)-5} more"
                else:
                    example_values = ', '.join(f"'{v}'" for v in all_invalid_values)
                st.markdown(f"Examples of non-standard values: {example_values}")

                # Create a stable key for the checkbox
                checkbox_key = f"fix_{col.replace(' ', '_')}"

                # Show checkbox for standardization
                fix_col = st.checkbox(
                    f"Would you like to standardize the {col} values?",
                    key=checkbox_key
                )

                if fix_col:
                    temp_mappings = {}
                    for invalid_value in all_invalid_values:
                        from difflib import get_close_matches
                        close_matches = get_close_matches(str(invalid_value), valid_values, n=5, cutoff=0.6)

                        selection_key = f"{col.replace(' ', '_')}_{str(invalid_value).replace(' ', '_')}"

                        if close_matches:
                            correct_value = st.selectbox(
                                f"Select standardized value for '{invalid_value}':",
                                options=['Keep current value'] + close_matches + valid_values,
                                key=selection_key
                            )
                        else:
                            correct_value = st.selectbox(
                                f"No close matches found. Select standardized value for '{invalid_value}':",
                                options=['Keep current value'] + valid_values,
                                key=selection_key
                            )

                        temp_mappings[invalid_value] = correct_value

                    # Add a button to confirm mappings for this column
                    if st.button(f"Confirm mappings for {col}"):
                        # Store the mappings
                        st.session_state.value_mappings[col] = temp_mappings
                        st.session_state.mapping_complete[col] = True
                        st.rerun()

                else:
                    # If checkbox is unchecked, mark as complete with no changes
                    if st.button(f"Confirm keeping original values for {col}"):
                        st.session_state.mapping_complete[col] = True
                        st.session_state.value_mappings[col] = {val: 'Keep current value' for val in all_invalid_values}
                        st.rerun()

            elif len(all_invalid_values) > 0 and st.session_state.mapping_complete[col]:
                # Show summary of mappings
                st.markdown(f"#### Mapping Summary for {col}:")

                # Group values by action
                to_keep = [val for val, mapping in st.session_state.value_mappings[col].items()
                          if mapping == 'Keep current value']
                to_remap = {val: mapping for val, mapping in st.session_state.value_mappings[col].items()
                           if mapping != 'Keep current value'}

                if to_keep:
                    st.info(f"Values to keep unchanged: {', '.join(f'`{val}`' for val in to_keep)}")

                if to_remap:
                    remap_summary = [f"`{old}` → `{new}`" for old, new in to_remap.items()]
                    st.info(f"Values to be remapped: {', '.join(remap_summary)}")

                # Add mappings to corrections if there are any remappings
                if to_remap:
                    corrections[col] = to_remap

                # Add button to reset mappings if needed
                if st.button(f"Reset mappings for {col}"):
                    st.session_state.mapping_complete[col] = False
                    st.session_state.value_mappings[col] = {}
                    st.rerun()

    return df, corrections

# helper function to validate Project Short Name
def is_valid_project_short_name(name):
    return bool(re.match(r'^[a-zA-Z0-9\s_-]{1,30}$', name))

# helper function to find the correct capitalization of a column name
def get_correct_column_name(col):
    lower_allowable = {c.lower(): c for c in allowable_columns}
    return lower_allowable.get(col.lower(), col)

# helper function to get correct capitalization for categorical values
def get_correct_value(value, valid_values):
    lower_valid = {v.lower(): v for v in valid_values}
    return lower_valid.get(value.lower(), value)

# Function to clean and convert "Age at" columns to numeric
def clean_age_columns(df, age_columns):
    for col in age_columns:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce')  # Convert to numeric, set non-numeric to NaN
    return df

# Function to reorder columns
def reorder_columns(df):
    preferred_order = [
        'Project Short Name', 'Case ID', 'Primary Diagnosis', 'Tissue or Organ of Origin',
        'Race', 'Ethnicity', 'Sex at Birth', 'Age UOM',
        'Age at Diagnosis', 'Age at Enrollment', 'Age at Surgery', 'Age at Earliest Imaging'
    ]
    existing_columns = [col for col in preferred_order if col in df.columns]
    other_columns = [col for col in df.columns if col not in existing_columns]
    return df[existing_columns + other_columns]

# helper function to ingest spreadsheet file to dataframe
def process_file(file_or_url, is_url=False):
    """Helper function to process uploaded files or URLs"""
    try:
        if is_url:
            file_name = file_or_url
            if not any(file_name.lower().endswith(ext) for ext in ['.csv', '.xlsx', '.tsv']):
                st.error("URL must point to a .csv, .xlsx, or .tsv file")
                return None, False
        else:
            file_name = file_or_url.name  # Get the name from UploadedFile object

        # Determine file type and read accordingly
        if file_name.lower().endswith('.csv'):
            df = pd.read_csv(file_or_url)
            proceed_to_next = True
        elif file_name.lower().endswith('.xlsx'):
            excel_file = pd.ExcelFile(file_or_url)
            sheet_names = excel_file.sheet_names
            if len(sheet_names) > 1:
                selected_tab = st.selectbox("Select Sheet to Analyze", sheet_names)
                df = pd.read_excel(file_or_url, sheet_name=selected_tab)
                proceed_to_next = st.button("Next")
            else:
                df = pd.read_excel(file_or_url)
                proceed_to_next = True
        elif file_name.lower().endswith('.tsv'):
            df = pd.read_csv(file_or_url, delimiter='\t')
            proceed_to_next = True
        else:
            st.error("Unsupported file format. Please upload a .csv, .xlsx, or .tsv file")
            return None, False

        return df, proceed_to_next

    except Exception as e:
        st.error(f"Error processing file: {str(e)}")
        return None, False

# Main Streamlit app
# Custom CSS to switch logo based on the user's theme preference
st.markdown(
    """
    <style>
    @media (prefers-color-scheme: dark) {
        .logo {
            content: url(https://www.cancerimagingarchive.net/wp-content/uploads/2021/06/TCIA-Logo-02.png);
        }
    }
    @media (prefers-color-scheme: light) {
        .logo {
            content: url(https://www.cancerimagingarchive.net/wp-content/uploads/2021/06/TCIA-Logo-01.png);
        }
    }
    </style>
    <header class="main-header">
        <img class="logo" alt="App Logo">
    </header>
    """,
    unsafe_allow_html=True
)

# main column title
st.title("Clinical Data Validator")

# Initialize session state to track steps
if 'step' not in st.session_state:
    st.session_state.step = 1
if 'project_short_name' not in st.session_state:
    st.session_state.project_short_name = ''
if 'age_uom' not in st.session_state:
    st.session_state.age_uom = ''

# Step 1: File Upload and Import
if st.session_state.step == 1:
    st.subheader("Step 1: Upload your CSV, XLSX, or TSV file")
    uploaded_file = st.file_uploader("Upload your file", type=["csv", "xlsx", "tsv"])

    if uploaded_file:
        df, proceed_to_next = process_file(uploaded_file)
    else:
        url = st.text_input("...or provide the URL of the file")
        if url:
            df, proceed_to_next = process_file(url, is_url=True)

    # Process results if we have them
    if 'df' in locals() and df is not None and proceed_to_next:
        st.success("File imported successfully!")
        # Remove leading and trailing spaces from all strings in the dataframe
        df = df.map(lambda x: x.strip() if isinstance(x, str) else x)
        # move to the next step/state
        st.session_state.df = df
        st.session_state.step = 2
        st.rerun()

# Step 2: Analyze and Map Columns
elif st.session_state.step == 2:
    st.subheader("Step 2: Map column names to Common Data Elements")
    df = st.session_state.df

    # Clean and validate the data first
    df, validation_report = validate_and_clean_data(df)

    # Display any cleaning operations that were performed
    if validation_report:
        for message in validation_report:
            st.info(message)

    # Automatically correct capitalization for columns that match allowable columns
    columns_to_rename = {}
    for col in df.columns:
        # Convert column name to string to ensure it's not a UploadedFile object
        col_str = str(col)
        correct_name = get_correct_column_name(col_str)
        if correct_name != col_str:
            columns_to_rename[col_str] = correct_name

    if columns_to_rename:
        df.rename(columns=columns_to_rename, inplace=True)
        st.info(f"The following columns were automatically renamed to correct capitalization: {', '.join(columns_to_rename.values())}")

    # Find truly unexpected columns (those that don't match any allowable column, regardless of capitalization)
    unexpected_columns = [
        str(col) for col in df.columns
        if str(col).lower() not in [c.lower() for c in allowable_columns]
    ]

    # Initialize session state variables if not present
    if 'columns_mapped' not in st.session_state:
        st.session_state.columns_mapped = False
    if 'column_mapping' not in st.session_state:
        st.session_state.column_mapping = {}
    if 'mapping_applied' not in st.session_state:
        st.session_state.mapping_applied = False

    if unexpected_columns:
        if not st.session_state.mapping_applied:
            st.markdown("### The following unexpected columns were found:")
            column_mapping = {}
            for col in unexpected_columns:
                option = st.selectbox(
                    f"How should '{col}' be mapped?",
                    allowable_columns + ["Leave unmodified", "Delete column"],
                    key=col,
                    index=len(allowable_columns)
                )
                column_mapping[col] = option

            if st.button("Apply column mapping"):
                st.session_state.column_mapping = column_mapping
                st.session_state.mapping_applied = True

                # Apply the mappings
                for col, action in column_mapping.items():
                    if action == "Delete column":
                        df.drop(columns=[col], inplace=True)
                    elif action != "Leave unmodified":
                        df.rename(columns={col: action}, inplace=True)

                st.session_state.df = df
                st.rerun()
        else:
            # Group columns by action type
            to_delete = []
            to_remain = []
            to_remap = {}

            for col, action in st.session_state.column_mapping.items():
                if action == "Delete column":
                    to_delete.append(col)
                elif action == "Leave unmodified":
                    to_remain.append(col)
                else:
                    to_remap[col] = action

            # Show summary of applied mappings grouped by action
            st.markdown("### Column Mapping Summary:")

            if to_delete:
                st.info(f"The following columns will be deleted: {', '.join(f'`{col}`' for col in to_delete)}")

            if to_remain:
                st.info(f"The following columns will remain unchanged: {', '.join(f'`{col}`' for col in to_remain)}")

            if to_remap:
                remap_summary = [f"`{old}` → `{new}`" for old, new in to_remap.items()]
                st.info(f"The following columns will be remapped: {', '.join(remap_summary)}")

            st.session_state.columns_mapped = True
    else:
        # Only show success message if there are no unexpected columns
        # and automatic renaming (if any) has been completed
        st.success("All columns are correctly named or have been automatically corrected.")
        st.session_state.columns_mapped = True

    # Update the session state with the cleaned data
    st.session_state.df = df

    # Only show "Next step" button if all columns are mapped
    if st.session_state.columns_mapped:
        if st.button("Next step"):
            # Reset mapping state for if user comes back to this step
            st.session_state.mapping_applied = False
            st.session_state.column_mapping = {}
            st.session_state.step = 3
            st.rerun()

# Step 3: Check Required Columns and Validate Project Short Name
elif st.session_state.step == 3:
    st.subheader("Step 3: Check Required Columns and Validate Data")
    df = st.session_state.df

    # Convert non-age columns to strings
    df = convert_to_strings(df)

    missing_case_id = 'Case ID' not in df.columns
    missing_project_short_name = 'Project Short Name' not in df.columns
    age_columns = ['Age at Diagnosis', 'Age at Enrollment', 'Age at Surgery', 'Age at Earliest Imaging']
    existing_age_columns = [col for col in age_columns if col in df.columns]
    missing_age_uom = 'Age UOM' not in df.columns and existing_age_columns

    if missing_case_id:
        st.error("The 'Case ID' column is missing from your spreadsheet. This is a required column.")
        if st.button("Restart"):
            st.session_state.step = 1
            if 'df' in st.session_state:
                del st.session_state.df
            st.rerun()
    else:
        project_short_name_valid = True
        age_uom_valid = True

        # Handle Project Short Name
        name_updates = {}
        if missing_project_short_name:
            st.warning("The 'Project Short Name' column is missing from your spreadsheet.")
            project_short_name = st.text_input("Please specify a Project Short Name:", value=st.session_state.project_short_name)
            if project_short_name:
                if is_valid_project_short_name(project_short_name):
                    st.session_state.project_short_name = project_short_name
                else:
                    st.error("Invalid Project Short Name. It should be 1-30 characters long and contain only letters, numbers, dashes, and underscores.")
                    project_short_name_valid = False
            else:
                project_short_name_valid = False
        else:
            # Check existing Project Short Names
            invalid_names = df[~df['Project Short Name'].apply(is_valid_project_short_name)]['Project Short Name'].unique()
            if len(invalid_names) > 0:
                st.warning("Some Project Short Names are invalid. Please update them:")
                for name in invalid_names:
                    new_name = st.text_input(f"New name for '{name}' (1-30 characters, letters, numbers, dashes, underscores):")
                    if new_name:
                        if is_valid_project_short_name(new_name):
                            name_updates[name] = new_name
                        else:
                            st.error(f"'{new_name}' is not a valid Project Short Name.")
                            project_short_name_valid = False
                    else:
                        project_short_name_valid = False
            else:
                st.success("All Project Short Names are valid.")

        # Handle missing Age UOM
        if missing_age_uom:
            st.warning("The 'Age UOM' column is missing, but age-related columns are present.")
            age_uom = st.selectbox("Please select the Age Unit of Measure:", options=permissible_age_uom, index=0 if not st.session_state.age_uom else permissible_age_uom.index(st.session_state.age_uom))
            if age_uom:
                st.session_state.age_uom = age_uom
            else:
                age_uom_valid = False
        else:
            age_uom_valid = True

        # Single "Next step" button for both updating and continuing
        if st.button("Next step"):
            if project_short_name_valid and age_uom_valid:
                # Apply updates to Project Short Names if necessary
                if missing_project_short_name:
                    df['Project Short Name'] = st.session_state.project_short_name
                for old_name, new_name in name_updates.items():
                    df.loc[df['Project Short Name'] == old_name, 'Project Short Name'] = new_name

                # Apply Age UOM changes if necessary
                if missing_age_uom:
                    df['Age UOM'] = st.session_state.age_uom

                st.session_state.df = df
                st.success("Changes applied successfully!")
                st.session_state.step = 4
                st.rerun()
            else:
                if not project_short_name_valid:
                    st.error("Please provide a valid Project Short Name.")
                if not age_uom_valid:
                    st.error("Please select an Age Unit of Measure.")

# Step 4: Validate Data (modified to exclude Primary Diagnosis and Tissue/Organ)
elif st.session_state.step == 4:
    st.subheader("Step 4: Validate Race, Ethnicity, and Age Data")
    df = st.session_state.df

    # Dictionary to store all corrections
    all_corrections = {}

    # Function to apply all corrections
    def apply_corrections():
        for col, correct_dict in all_corrections.items():
            df[col] = df[col].replace(correct_dict)
        st.session_state.df = df
        st.success("Corrections applied successfully!")
        st.rerun()

    # 1. Validate Race column (special handling for multiple values)
    if 'Race' in df.columns:
        invalid_races = df['Race'].apply(lambda x: any(race.strip() not in permissible_race
                                                     for race in str(x).split(';')
                                                     if race.strip()))
        invalid_race_values = df[invalid_races]['Race'].unique()

        if len(invalid_race_values) > 0:
            st.markdown("#### Invalid values found in Race:")
            race_corrections = {}
            for value in invalid_race_values:
                st.write(f"Invalid value: '{value}'")
                correct_races = st.multiselect(
                    f"Select correct races for '{value}':",
                    options=permissible_race,
                    key=f"Race_{value}"
                )
                if correct_races:
                    race_corrections[value] = ';'.join(correct_races)

            if race_corrections:
                all_corrections['Race'] = race_corrections

    # 2. Validate categorical columns (excluding Primary Diagnosis and Tissue/Organ)
    categorical_columns = {
        'Ethnicity': permissible_ethnicity,
        'Sex at Birth': permissible_sex_at_birth,
        'Age UOM': permissible_age_uom
    }

    for col, valid_values in categorical_columns.items():
        if col in df.columns:
            invalid_values = df[~df[col].isin(valid_values)][col].unique()
            if len(invalid_values) > 0:
                st.markdown(f"#### Invalid values found in {col}:")
                corrections = {}
                for value in invalid_values:
                    correct_value = st.selectbox(
                        f"Correct value for '{value}' in {col}:",
                        options=valid_values,
                        key=f"{col}_{value}"
                    )
                    if correct_value:
                        corrections[value] = correct_value

                if corrections:
                    all_corrections[col] = corrections

    # 3. Validate numeric columns
    numeric_columns = ['Age at Diagnosis', 'Age at Enrollment',
                      'Age at Surgery', 'Age at Earliest Imaging']

    for col in numeric_columns:
        if col in df.columns:
            non_numeric = df[df[col].notna() &
                           pd.to_numeric(df[col], errors='coerce').isna()][col]
            if not non_numeric.empty:
                st.markdown(f"#### Non-numeric values found in {col}:")
                numeric_corrections = {}
                for idx, value in non_numeric.items():
                    correct_value = st.text_input(
                        f"Correct value for '{value}' in {col} (row {idx}):",
                        key=f"{col}_{idx}"
                    )
                    if correct_value:
                        try:
                            float(correct_value)
                            numeric_corrections[value] = correct_value
                        except ValueError:
                            st.error(f"'{correct_value}' is not a valid numeric value.")

                if numeric_corrections:
                    all_corrections[col] = numeric_corrections

    # Apply corrections button
    if all_corrections:
        if st.button("Apply All Corrections"):
            apply_corrections()
    else:
        st.success("All race, ethnicity and age data is valid!")

    # Only show "Next step" button if no corrections are needed
    remaining_corrections = {k: v for k, v in all_corrections.items()
                           if not k.startswith('skip_')}
    if not remaining_corrections:
        if st.button("Next step"):
            # Clear skip flags for next run
            for key in list(st.session_state.keys()):
                if key.startswith('skip_'):
                    del st.session_state[key]
            st.session_state.step = 5
            st.rerun()

# Step 5: Tissue or Organ of Origin Validation
elif st.session_state.step == 5:
    st.subheader("Step 5: Validate Tissue or Organ of Origin")
    df = st.session_state.df

    if 'Tissue or Organ of Origin' not in df.columns:
        st.info("No Tissue or Organ of Origin column found in the data. Proceeding to next step.")
        if st.button("Next step"):
            st.session_state.step = 6
            st.rerun()
    else:
        # Initialize session state for Tissue/Organ mapping
        if 'tissue_organ_mapped' not in st.session_state:
            st.session_state.tissue_organ_mapped = False
        if 'tissue_organ_mappings' not in st.session_state:
            st.session_state.tissue_organ_mappings = {}

        # Get invalid values
        invalid_values = df[~df['Tissue or Organ of Origin'].isin(permissible_tissue_or_organ)]['Tissue or Organ of Origin'].unique()

        if len(invalid_values) == 0:
            st.success("All Tissue or Organ of Origin values are valid!")
            if st.button("Next step"):
                st.session_state.step = 6
                st.rerun()
        else:
            if not st.session_state.tissue_organ_mapped:
                st.markdown(f"#### Found {len(invalid_values)} non-standard Tissue or Organ of Origin values")

                # Show mapping interface
                mappings = {}
                for value in invalid_values:
                    # Get close matches
                    from difflib import get_close_matches
                    close_matches = get_close_matches(str(value), permissible_tissue_or_organ, n=5, cutoff=0.6)

                    # Create selectbox with close matches first, then all options
                    options = ['Keep current value']
                    if close_matches:
                        options.extend(close_matches)
                    options.extend([v for v in permissible_tissue_or_organ if v not in close_matches])

                    selected_value = st.selectbox(
                        f"Map '{value}' to:",
                        options=options,
                        key=f"tissue_organ_{value}"
                    )

                    if selected_value != 'Keep current value':
                        mappings[value] = selected_value

                # Button to confirm mappings
                if st.button("Confirm Tissue or Organ of Origin mappings"):
                    st.session_state.tissue_organ_mappings = mappings
                    st.session_state.tissue_organ_mapped = True

                    # Apply mappings
                    if mappings:
                        df['Tissue or Organ of Origin'] = df['Tissue or Organ of Origin'].replace(mappings)
                        st.session_state.df = df

                    st.rerun()
            else:
                # Show mapping summary
                st.markdown("#### Tissue or Organ of Origin Mapping Summary:")

                # Group values by action
                to_keep = [val for val in invalid_values if val not in st.session_state.tissue_organ_mappings]
                to_remap = st.session_state.tissue_organ_mappings

                if to_keep:
                    st.info(f"Values to keep unchanged: {', '.join(f'`{val}`' for val in to_keep)}")

                if to_remap:
                    remap_summary = [f"`{old}` → `{new}`" for old, new in to_remap.items()]
                    st.info(f"Values that were remapped: {', '.join(remap_summary)}")

                # Button to reset mappings
                col1, col2 = st.columns(2)
                with col1:
                    if st.button("Reset mappings"):
                        st.session_state.tissue_organ_mapped = False
                        st.session_state.tissue_organ_mappings = {}
                        st.rerun()

                with col2:
                    if st.button("Next step"):
                        st.session_state.step = 6
                        st.rerun()

# Step 6: Primary Diagnosis Validation
elif st.session_state.step == 6:
    st.subheader("Step 6: Validate Primary Diagnosis")
    df = st.session_state.df

    if 'Primary Diagnosis' not in df.columns:
        st.info("No Primary Diagnosis column found in the data. Proceeding to next step.")
        if st.button("Next step"):
            st.session_state.step = 7
            st.rerun()
    else:
        # Initialize session state for Primary Diagnosis mapping
        if 'primary_diagnosis_mapped' not in st.session_state:
            st.session_state.primary_diagnosis_mapped = False
        if 'primary_diagnosis_mappings' not in st.session_state:
            st.session_state.primary_diagnosis_mappings = {}

        # Get invalid values
        invalid_values = df[~df['Primary Diagnosis'].isin(permissible_primary_diagnosis)]['Primary Diagnosis'].unique()

        if len(invalid_values) == 0:
            st.success("All Primary Diagnosis values are valid!")
            if st.button("Next step"):
                st.session_state.step = 7
                st.rerun()
        else:
            if not st.session_state.primary_diagnosis_mapped:
                st.markdown(f"#### Found {len(invalid_values)} non-standard Primary Diagnosis values")

                # Show mapping interface
                mappings = {}
                for value in invalid_values:
                    # Get close matches
                    from difflib import get_close_matches
                    close_matches = get_close_matches(str(value), permissible_primary_diagnosis, n=5, cutoff=0.6)

                    # Create selectbox with close matches first, then all options
                    options = ['Keep current value']
                    if close_matches:
                        options.extend(close_matches)
                    options.extend([v for v in permissible_primary_diagnosis if v not in close_matches])

                    selected_value = st.selectbox(
                        f"Map '{value}' to:",
                        options=options,
                        key=f"primary_diagnosis_{value}"
                    )

                    if selected_value != 'Keep current value':
                        mappings[value] = selected_value

                # Button to confirm mappings
                if st.button("Confirm Primary Diagnosis mappings"):
                    st.session_state.primary_diagnosis_mappings = mappings
                    st.session_state.primary_diagnosis_mapped = True

                    # Apply mappings
                    if mappings:
                        df['Primary Diagnosis'] = df['Primary Diagnosis'].replace(mappings)
                        st.session_state.df = df

                    st.rerun()
            else:
                # Show mapping summary
                st.markdown("#### Primary Diagnosis Mapping Summary:")

                # Group values by action
                to_keep = [val for val in invalid_values if val not in st.session_state.primary_diagnosis_mappings]
                to_remap = st.session_state.primary_diagnosis_mappings

                if to_keep:
                    st.info(f"Values to keep unchanged: {', '.join(f'`{val}`' for val in to_keep)}")

                if to_remap:
                    remap_summary = [f"`{old}` → `{new}`" for old, new in to_remap.items()]
                    st.info(f"Values that were remapped: {', '.join(remap_summary)}")

                # Button to reset mappings
                col1, col2 = st.columns(2)
                with col1:
                    if st.button("Reset mappings"):
                        st.session_state.primary_diagnosis_mapped = False
                        st.session_state.primary_diagnosis_mappings = {}
                        st.rerun()

                with col2:
                    if st.button("Next step"):
                        st.session_state.step = 7
                        st.rerun()

# Step 7: Download Standardized Data
elif st.session_state.step == 7:
    st.subheader("Step 7: Download Standardized Data")
    df = st.session_state.df

    # Reorder columns
    df = reorder_columns(df)

    output = BytesIO()
    df.to_csv(output, index=False)
    st.download_button("Download Standardized CSV", data=output.getvalue(), file_name="standardized_data.csv")

    if st.button("Restart"):
        reset_session_state()
        st.rerun()
