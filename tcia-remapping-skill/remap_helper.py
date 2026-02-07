import pandas as pd
import json
import difflib
import os

def load_json(filename):
    with open(filename, 'r') as f:
        return json.load(f)

def get_closest_match(value, choices, n=1, cutoff=0.6):
    if not value or pd.isna(value):
        return None
    matches = difflib.get_close_matches(str(value), choices, n=n, cutoff=cutoff)
    return matches[0] if matches else None

def validate_dataframe(df, schema_name, schema, permissible_values):
    report = []
    corrections = {}

    target_props = {p['Property']: p for p in schema.get(schema_name, [])}

    for col in df.columns:
        if col in target_props:
            # Check permissible values
            if col in permissible_values:
                choices = permissible_values[col]
                for val in df[col].unique():
                    if pd.isna(val) or str(val).strip() == "":
                        continue
                    if val not in choices:
                        match = get_closest_match(val, choices)
                        if match:
                            if col not in corrections:
                                corrections[col] = {}
                            corrections[col][val] = match
                            report.append(f"Value '{val}' in '{col}' is not standard. Suggested: '{match}'")
                        else:
                            report.append(f"Value '{val}' in '{col}' is not standard and no close match found.")

    return report, corrections

def split_data_by_schema(df, column_mapping, schema):
    """
    df: source dataframe
    column_mapping: dict mapping target_property -> source_column
    schema: target schema from schema.json
    """
    results = {}
    for sheet_name, properties in schema.items():
        target_cols = [p['Property'] for p in properties]

        # Find which target columns are mapped to source columns
        mapped_target_cols = [tc for tc in target_cols if tc in column_mapping]

        if mapped_target_cols:
            # Create a new dataframe for this sheet
            new_df = pd.DataFrame()
            for tc in mapped_target_cols:
                source_col = column_mapping[tc]
                if source_col in df.columns:
                    new_df[tc] = df[source_col]

            # Remove duplicates for entity-level files if necessary
            # (e.g., Subject should only have one row per subject_id)
            # This is a simplification; more complex logic might be needed.
            new_df = new_df.drop_duplicates()

            results[sheet_name] = new_df

    return results

def main():
    print("TCIA Remap Helper loaded.")

if __name__ == "__main__":
    main()
