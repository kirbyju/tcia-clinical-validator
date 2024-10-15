import streamlit as st
import pandas as pd
import numpy as np
from io import BytesIO
import re

# Permissible columns and enumerations
required_columns = ['Project Short Name', 'Case ID']
allowable_columns = [
    'Project Short Name', 'Case ID', 'Race', 'Ethnicity', 'Sex at Birth',
    'Age at Diagnosis', 'Age at Enrollment', 'Age at Surgery',
    'Age at Earliest Imaging', 'Age UOM', 'Primary Diagnosis', 'Primary Site'
]
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
    for col in ['Race', 'Ethnicity', 'Sex at Birth']:
        if col in df.columns:
            df[col] = df[col].str.title().str.strip()

    # Drop duplicate rows and report their original row numbers
    duplicate_rows = df[df.duplicated()].index.tolist()
    if duplicate_rows:
        df.drop_duplicates(inplace=True)
        report.append(f"Removed {len(duplicate_rows)} duplicate rows: {duplicate_rows}")

    return df, report

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

# Function to calculate 'Age at Baseline' in years
def calculate_age_at_baseline(df, age_columns, uom_column):
    df['Age at Baseline'] = np.nan

    if uom_column in df.columns:
        # Filter for age columns that actually exist in the dataframe
        existing_age_columns = [col for col in age_columns if col in df.columns]

        if existing_age_columns:
            for age_col in existing_age_columns:
                # Convert all ages to years based on the UOM column
                df[age_col] = df[age_col] * df[uom_column].map(age_uom_factors)

            # Set the 'Age at Baseline' to the minimum of the existing "Age at" columns (in years)
            df['Age at Baseline'] = df[existing_age_columns].min(axis=1)
        else:
            st.warning("No age columns found in the dataframe. 'Age at Baseline' could not be calculated.")

    return df

# Main Streamlit app
st.set_page_config(page_title="TCIA Clinical Data Validator")

# Custom CSS to switch logo based on the user's theme preference
st.markdown(
    """
    <style>
    @media (prefers-color-scheme: dark) {
        .logo {
            content: url(https://www.cancerimagingarchive.net/wp-content/uploads/2021/06/TCIA-Logo-01.png);
        }
    }
    @media (prefers-color-scheme: light) {
        .logo {
            content: url(https://www.cancerimagingarchive.net/wp-content/uploads/2021/06/TCIA-Logo-02.png);
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
    url = st.text_input("...or provide the URL of the file")

    if uploaded_file or url:
        try:
            if uploaded_file:
                if uploaded_file.name.endswith(".csv"):
                    df = pd.read_csv(uploaded_file)
                elif uploaded_file.name.endswith(".xlsx"):
                    df = pd.read_excel(uploaded_file)
                elif uploaded_file.name.endswith(".tsv"):
                    df = pd.read_csv(uploaded_file, delimiter='\t')
            elif url:
                df = pd.read_csv(url)  # Assuming URL is a CSV for simplicity

            st.success("File imported successfully!")

            # Remove leading and trailing spaces from all strings in the dataframe
            df = df.map(lambda x: x.strip() if isinstance(x, str) else x)
            # move to the next step/state
            st.session_state.df = df
            st.session_state.step = 2
            st.rerun()
        except Exception as e:
            st.error(f"Error processing file: {str(e)}")

# Step 2: Analyze and Map Columns
elif st.session_state.step == 2:
    st.subheader("Step 2: Map column names to Common Data Elements")
    df = st.session_state.df

    # Automatically correct capitalization for columns that match allowable columns
    columns_to_rename = {}
    for col in df.columns:
        correct_name = get_correct_column_name(col)
        if correct_name != col:
            columns_to_rename[col] = correct_name

    if columns_to_rename:
        df.rename(columns=columns_to_rename, inplace=True)
        st.info(f"The following columns were automatically renamed to correct capitalization: {', '.join(columns_to_rename.values())}")

    # Find truly unexpected columns (those that don't match any allowable column, regardless of capitalization)
    unexpected_columns = [col for col in df.columns if col.lower() not in [c.lower() for c in allowable_columns]]

    if unexpected_columns:
        st.write("The following unexpected columns were found:")
        column_mapping = {}
        for col in unexpected_columns:
            option = st.selectbox(f"How should '{col}' be mapped?", allowable_columns + ["Delete column"], key=col, index=len(allowable_columns))
            column_mapping[col] = option

        if st.button("Apply column mapping"):
            for col, action in column_mapping.items():
                if action == "Delete column":
                    df.drop(columns=[col], inplace=True)
                else:
                    df.rename(columns={col: action}, inplace=True)
            st.success("Columns mapped successfully!")
            st.session_state.df = df
            st.session_state.columns_mapped = True
            st.rerun()
    else:
        st.success("All columns are correctly named or have been automatically corrected.")
        st.session_state.columns_mapped = True

    # Only show "Next step" button if all columns are mapped
    if st.session_state.get('columns_mapped', False):
        if st.button("Next step"):
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

# Step 4: Validate Data
elif st.session_state.step == 4:
    st.subheader("Step 4: Validate Data")
    df = st.session_state.df

    # Dictionary to store corrections for each column
    corrections = {}

    # Function to apply corrections
    def apply_corrections():
        for col, correct_dict in corrections.items():
            df[col] = df[col].replace(correct_dict)
        st.session_state.df = df
        st.success("Corrections applied successfully!")
        st.rerun()

    # Validate categorical columns
    categorical_columns = {
        'Race': permissible_race,
        'Ethnicity': permissible_ethnicity,
        'Sex at Birth': permissible_sex_at_birth,
        'Age UOM': permissible_age_uom
    }

    for col, valid_values in categorical_columns.items():
        if col in df.columns:
            # Automatically correct capitalization
            df[col] = df[col].apply(lambda x: get_correct_value(x, valid_values) if pd.notna(x) else x)

            # Find remaining invalid values
            invalid_values = df[~df[col].isin(valid_values + [np.nan])][col].unique()

            if len(invalid_values) > 0:
                st.markdown(f"### Invalid values found in {col}:")
                corrections[col] = {}
                for value in invalid_values:
                    correct_value = st.selectbox(
                        f"Correct value for '{value}' in {col}:",
                        options=valid_values,
                        key=f"{col}_{value}"
                    )
                    corrections[col][value] = correct_value

    # Validate numeric columns
    numeric_columns = ['Age at Diagnosis', 'Age at Enrollment', 'Age at Surgery', 'Age at Earliest Imaging']
    for col in numeric_columns:
        if col in df.columns:
            #non_numeric = df[pd.to_numeric(df[col], errors='coerce').isna()][col]
            non_numeric = df[df[col].notna() & pd.to_numeric(df[col], errors='coerce').isna()][col]
            if not non_numeric.empty:
                st.write(f"Non-numeric values found in {col}:")
                corrections[col] = {}
                for idx, value in non_numeric.items():
                    correct_value = st.text_input(f"Correct value for '{value}' in {col} (row {idx}):", key=f"{col}_{idx}")
                    if correct_value:
                        try:
                            float(correct_value)
                            corrections[col][value] = correct_value
                        except ValueError:
                            st.error(f"'{correct_value}' is not a valid numeric value.")

    # Apply corrections button
    if corrections:
        if st.button("Apply Corrections"):
            apply_corrections()
    else:
        st.success("All data is valid!")

    # populate 'age at baseline' column
    age_columns = ['Age at Diagnosis', 'Age at Enrollment', 'Age at Surgery', 'Age at Earliest Imaging']
    df = clean_age_columns(df, age_columns)  # Ensure age columns are numeric
    df = calculate_age_at_baseline(df, age_columns, 'Age UOM')
    st.session_state.df = df

    # Only show "Next step" button if no corrections are needed
    if not corrections:
        if st.button("Next step"):
            st.session_state.step = 5
            st.rerun()

# this can happen behind the scenes at the end of step 4 after values are remapped
# Step 5: Age at Baseline Calculation
#elif st.session_state.step == 5:
#    st.subheader("Step 4: Calculate 'Age at Baseline'")
#    df = st.session_state.df
#    age_columns = ['Age at Diagnosis', 'Age at Enrollment', 'Age at Surgery', 'Age at Earliest Imaging']
#    df = clean_age_columns(df, age_columns)  # Ensure age columns are numeric
#    df = calculate_age_at_baseline(df, age_columns, 'Age UOM')  # Calculate baseline age

#    st.write("Age at Baseline column created and converted to years.")
#    st.session_state.df = df

#    if st.button("Next step"):
#        st.session_state.step = 6

# Step 5: Download Standardized Data
# TODO:
# reset sensible column order
# add support for multi-select enumerable values (semicolon separator?)
elif st.session_state.step == 5:
    st.subheader("Step 5: Download Standardized Data")
    df = st.session_state.df
    output = BytesIO()
    df.to_csv(output, index=False)
    st.download_button("Download Standardized CSV", data=output.getvalue(), file_name="standardized_data.csv")

    if st.button("Restart"):
        st.session_state.step = 1
        if 'df' in st.session_state:
            del st.session_state.df
        st.rerun()
