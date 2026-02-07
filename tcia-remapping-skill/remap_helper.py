import pandas as pd
import json
import difflib
import os

def load_json(filename):
    with open(filename, 'r') as f:
        return json.load(f)

def get_closest_match(value, choices, n=1, cutoff=0.6):
    """
    choices can be a list of strings or a list of dicts with a 'value' key.
    """
    if not value or pd.isna(value):
        return None

    # Extract string values if choices is a list of dicts
    if choices and isinstance(choices[0], dict):
        choice_strings = [c['value'] for c in choices]
        value_to_choice = {c['value']: c for c in choices}
    else:
        choice_strings = choices
        value_to_choice = {c: c for c in choices}

    matches = difflib.get_close_matches(str(value), choice_strings, n=n, cutoff=cutoff)
    if matches:
        return value_to_choice[matches[0]]
    return None

def validate_dataframe(df, schema_name, schema, permissible_values):
    """
    Returns a summary report and a dict of suggested corrections.
    """
    report = []
    corrections = {}

    target_props = {p['Property']: p for p in schema.get(schema_name, [])}

    for col in df.columns:
        if col in target_props:
            if col in permissible_values:
                choices = permissible_values[col]
                # If choices is list of dicts, get values for easy lookup
                if choices and isinstance(choices[0], dict):
                    valid_set = {c['value'] for c in choices}
                else:
                    valid_set = set(choices)

                invalid_values = []
                for val in df[col].unique():
                    if pd.isna(val) or str(val).strip() == "":
                        continue
                    if val not in valid_set:
                        invalid_values.append(val)

                if invalid_values:
                    col_corrections = {}
                    for val in invalid_values:
                        match = get_closest_match(val, choices)
                        if match:
                            # match is either a string or a dict
                            suggestion = match['value'] if isinstance(match, dict) else match
                            col_corrections[val] = suggestion
                            report.append(f"Column '{col}': '{val}' -> Suggested: '{suggestion}'")
                        else:
                            report.append(f"Column '{col}': '{val}' -> No close match found.")
                    if col_corrections:
                        corrections[col] = col_corrections

    return report, corrections

def split_data_by_schema(df, column_mapping, schema):
    results = {}
    for sheet_name, properties in schema.items():
        target_cols = [p['Property'] for p in properties]
        mapped_target_cols = [tc for tc in target_cols if tc in column_mapping]

        if mapped_target_cols:
            new_df = pd.DataFrame()
            for tc in mapped_target_cols:
                source_col = column_mapping[tc]
                if source_col in df.columns:
                    new_df[tc] = df[source_col]
            new_df = new_df.drop_duplicates()
            results[sheet_name] = new_df
    return results

def main():
    print("TCIA Remap Helper loaded with metadata support.")

if __name__ == "__main__":
    main()
