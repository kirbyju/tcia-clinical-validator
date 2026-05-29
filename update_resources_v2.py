import json
import os

resources_dir = 'tcia-remapping-skill/resources'
schema_file = os.path.join(resources_dir, 'schema.json')
pv_file = os.path.join(resources_dir, 'permissible_values.json')

with open(pv_file, 'r') as f:
    pv = json.load(f)
pv['adult_or_childhood_study'] = [
    {"value": "Adolescent and Young Adult", "origin": "TCIA"},
    {"value": "Adult", "origin": "TCIA"},
    {"value": "Pediatric", "origin": "TCIA"}
]
with open(pv_file, 'w') as f:
    json.dump(pv, f, indent=2)

with open(schema_file, 'r') as f:
    schema = json.load(f)
dataset_props = schema.get('Dataset', [])
new_fields = [
    ("introduction", "Introduction section of the dataset description"),
    ("methods_subjects", "Subject inclusion and exclusion criteria"),
    ("methods_acquisition", "Data acquisition details"),
    ("methods_analysis", "Data analysis details"),
    ("usage_notes", "Usage notes for the dataset"),
    ("external_resources", "Links to external resources"),
    ("why_tcia", "Reasons for wanting to publish on TCIA")
]
for prop, desc in new_fields:
    if not any(p['Property'] == prop for p in dataset_props):
        dataset_props.append({"Property": prop, "Description": desc, "Required/optional": "O"})
schema['Dataset'] = dataset_props
with open(schema_file, 'w') as f:
    json.dump(schema, f, indent=2)
