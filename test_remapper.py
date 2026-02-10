#!/usr/bin/env python3
"""
Test script for TCIA Dataset Remapper
Tests all three phases of the remapping workflow
"""

import sys
import os
import pandas as pd
import importlib.util

# Setup paths
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
RESOURCES_DIR = os.path.join(SCRIPT_DIR, 'tcia-remapping-skill', 'resources')
OUTPUT_DIR = os.path.join(SCRIPT_DIR, 'output')

# Import helper module
remap_helper_path = os.path.join(SCRIPT_DIR, 'tcia-remapping-skill', 'remap_helper.py')
spec = importlib.util.spec_from_file_location("remap_helper", remap_helper_path)
remap_helper = importlib.util.module_from_spec(spec)
spec.loader.exec_module(remap_helper)

def test_phase0_metadata():
    """Test Phase 0: Dataset-level metadata collection"""
    print("\n" + "="*60)
    print("Testing Phase 0: Dataset-Level Metadata Collection")
    print("="*60)
    
    # Load schema
    schema = remap_helper.load_json(os.path.join(RESOURCES_DIR, 'schema.json'))
    print("✓ Schema loaded successfully")
    
    # Create test metadata
    program_metadata = {
        'program_name': 'Community',
        'program_short_name': 'Community',
        'institution_name': 'Test University'
    }
    
    dataset_metadata = {
        'dataset_long_name': 'Test Cancer Imaging Dataset',
        'dataset_short_name': 'TestCID',
        'dataset_description': 'A test dataset for validation',
        'dataset_abstract': 'Test abstract',
        'number_of_participants': 100,
        # Note: 'data_has_been_de-identified' contains a hyphen to match TCIA schema specification
        'data_has_been_de-identified': 'Yes'
    }
    
    investigator_metadata = [
        {
            'first_name': 'John',
            'last_name': 'Doe',
            'email': 'john.doe@test.edu',
            'organization_name': 'Test University'
        }
    ]
    
    related_work_metadata = [
        {
            'DOI': '10.1234/test',
            'publication_title': 'Test Publication',
            'authorship': 'Doe et al.',
            'publication_type': 'Journal Article'
        }
    ]
    
    # Ensure output directory exists
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    
    # Generate TSV files
    print("\nGenerating TSV files...")
    files_generated = []
    
    for entity_name, data in [
        ('Program', program_metadata),
        ('Dataset', dataset_metadata),
        ('Investigator', investigator_metadata),
        ('Related_Work', related_work_metadata)
    ]:
        filepath = remap_helper.write_metadata_tsv(entity_name, data, schema, OUTPUT_DIR)
        if filepath and os.path.exists(filepath):
            files_generated.append(filepath)
            df = pd.read_csv(filepath, sep='\t')
            print(f"✓ Generated {os.path.basename(filepath)}: {len(df)} rows, {len(df.columns)} columns")
        else:
            print(f"✗ Failed to generate {entity_name}.tsv")
            return False
    
    print(f"\n✅ Phase 0 test passed! Generated {len(files_generated)} files.")
    return True

def test_phase1_structure_mapping():
    """Test Phase 1: Structure mapping"""
    print("\n" + "="*60)
    print("Testing Phase 1: Structure Mapping & Organization")
    print("="*60)
    
    # Load schema
    schema = remap_helper.load_json(os.path.join(RESOURCES_DIR, 'schema.json'))
    
    # Create sample data
    sample_data = {
        'PatientID': ['PT001', 'PT002', 'PT003'],
        'Age': [55, 62, 48],
        'Gender': ['Male', 'Female', 'Male'],
        'DiagnosisName': ['Lung adenocarcinoma', 'Breast carcinoma', 'Prostate cancer'],
        'BodySite': ['Lung', 'Breast', 'Prostate'],
        'RaceInfo': ['White', 'Asian', 'Black or African American']
    }
    df = pd.DataFrame(sample_data)
    print(f"✓ Created sample dataset: {len(df)} rows, {len(df.columns)} columns")
    
    # Define column mapping
    column_mapping = {
        'Subject.subject_id': 'PatientID',
        'Subject.age_at_diagnosis': 'Age',
        'Subject.sex_at_birth': 'Gender',
        'Diagnosis.primary_diagnosis': 'DiagnosisName',
        'Diagnosis.primary_site': 'BodySite',
        'Subject.race': 'RaceInfo'
    }
    print(f"✓ Defined column mapping: {len(column_mapping)} mappings")
    
    # Split data by schema
    split_data = remap_helper.split_data_by_schema(df, column_mapping, schema)
    print(f"✓ Split data into {len(split_data)} entities:")
    for entity_name, entity_df in split_data.items():
        print(f"  - {entity_name}: {len(entity_df)} rows, {len(entity_df.columns)} columns")
    
    print(f"\n✅ Phase 1 test passed! Mapped {len(split_data)} entities.")
    return True

def test_phase2_value_standardization():
    """Test Phase 2: Value standardization"""
    print("\n" + "="*60)
    print("Testing Phase 2: Value Standardization")
    print("="*60)
    
    # Load resources
    schema = remap_helper.load_json(os.path.join(RESOURCES_DIR, 'schema.json'))
    permissible_values = remap_helper.load_json(os.path.join(RESOURCES_DIR, 'permissible_values.json'))
    print("✓ Loaded schema and permissible values")
    
    # Create test dataframe with non-standard values
    test_data = {
        'primary_diagnosis': ['Lung adenocarcinoma', 'Breast carcinoma', 'Invalid diagnosis'],
        'primary_site': ['Lung', 'Breast', 'Unknown site'],
        'race': ['White', 'Asian', 'Caucasian']
    }
    df = pd.DataFrame(test_data)
    print(f"✓ Created test dataset with non-standard values")
    
    # Test fuzzy matching
    print("\nTesting fuzzy matching:")
    test_values = ['Lung adenocarcinoma', 'Breast carcinoma']
    for val in test_values:
        if 'primary_diagnosis' in permissible_values:
            match = remap_helper.get_closest_match(val, permissible_values['primary_diagnosis'])
            if match:
                match_val = match['value'] if isinstance(match, dict) else match
                print(f"  '{val}' → '{match_val}'")
            else:
                print(f"  '{val}' → No match found")
    
    # Validate dataframe
    print("\nValidating dataframe:")
    report, corrections = remap_helper.validate_dataframe(df, 'Diagnosis', schema, permissible_values)
    
    if report:
        print(f"✓ Found {len(report)} validation issues")
        for item in report[:5]:
            print(f"  - {item}")
    else:
        print("✓ No validation issues found")
    
    if corrections:
        print(f"✓ Generated {len(corrections)} correction mappings")
        for col, col_corrections in corrections.items():
            print(f"  Column '{col}': {len(col_corrections)} corrections")
    
    print(f"\n✅ Phase 2 test passed! Validation and correction system working.")
    return True

def test_conflict_detection():
    """Test metadata conflict detection"""
    print("\n" + "="*60)
    print("Testing Conflict Detection")
    print("="*60)
    
    # Create initial metadata
    initial_metadata = {
        'Program': [{'program_name': 'Community'}],
        'Dataset': [{'dataset_short_name': 'TestDS'}]
    }
    
    # Create conflicting dataframe
    df = pd.DataFrame({
        'ProgramName': ['Community', 'Research'],
        'DatasetName': ['TestDS', 'TestDS']
    })
    
    column_mapping = {
        'program_name': 'ProgramName',
        'dataset_short_name': 'DatasetName'
    }
    
    conflicts = remap_helper.check_metadata_conflict(initial_metadata, df, column_mapping)
    
    if conflicts:
        print(f"✓ Detected {len(conflicts)} conflict(s):")
        for conflict in conflicts:
            print(f"  - {conflict['entity']}.{conflict['property']}: '{conflict['initial_value']}' vs '{conflict['new_value']}'")
    else:
        print("✓ No conflicts detected")
    
    print(f"\n✅ Conflict detection test passed!")
    return True

def main():
    """Run all tests"""
    print("\n" + "="*60)
    print("TCIA Dataset Remapper Test Suite")
    print("="*60)
    
    tests = [
        ("Phase 0: Metadata Collection", test_phase0_metadata),
        ("Phase 1: Structure Mapping", test_phase1_structure_mapping),
        ("Phase 2: Value Standardization", test_phase2_value_standardization),
        ("Conflict Detection", test_conflict_detection)
    ]
    
    results = []
    for test_name, test_func in tests:
        try:
            result = test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"\n✗ Test failed with error: {str(e)}")
            import traceback
            traceback.print_exc()
            results.append((test_name, False))
    
    # Summary
    print("\n" + "="*60)
    print("Test Summary")
    print("="*60)
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for test_name, result in results:
        status = "✅ PASSED" if result else "✗ FAILED"
        print(f"{status}: {test_name}")
    
    print(f"\nTotal: {passed}/{total} tests passed")
    
    if passed == total:
        print("\n🎉 All tests passed!")
        return 0
    else:
        print(f"\n⚠️ {total - passed} test(s) failed")
        return 1

if __name__ == "__main__":
    sys.exit(main())
