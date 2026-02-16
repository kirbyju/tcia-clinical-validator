import os
import pandas as pd
import importlib.util
import sys

# Import mdf_parser and remap_helper
skill_dir = os.path.join(os.getcwd(), 'tcia-remapping-skill')
mdf_parser_path = os.path.join(skill_dir, 'mdf_parser.py')
spec_mdf = importlib.util.spec_from_file_location("mdf_parser", mdf_parser_path)
mdf_parser = importlib.util.module_from_spec(spec_mdf)
spec_mdf.loader.exec_module(mdf_parser)

remap_helper_path = os.path.join(skill_dir, 'remap_helper.py')
spec_rh = importlib.util.spec_from_file_location("remap_helper", remap_helper_path)
remap_helper = importlib.util.module_from_spec(spec_rh)
spec_rh.loader.exec_module(remap_helper)

def test_relationships():
    resource_dir = os.path.join(os.getcwd(), 'tcia-remapping-skill', 'resources')
    schema, permissible_values, relationships = mdf_parser.get_mdf_resources(resource_dir)

    assert relationships is not None
    assert 'of_Subject' in relationships
    print("✓ Relationships parsed successfully")

    # Test check_missing_links
    split_data = {
        'Subject': pd.DataFrame({'subject_id': ['S1']})
        # Missing dataset.dataset_id
    }

    missing = remap_helper.check_missing_links(split_data, schema, relationships)
    print(f"Detected missing links: {missing}")

    # of_Subject links Subject to Dataset. Linkage property should be dataset.dataset_id
    subject_missing = [m for m in missing if m['entity'] == 'Subject' and m['target_entity'] == 'Dataset']
    assert len(subject_missing) > 0
    assert subject_missing[0]['property'] == 'dataset.dataset_id'
    print("✓ check_missing_links correctly identified missing dataset linkage in Subject")

if __name__ == "__main__":
    try:
        test_relationships()
        print("\n✅ Relationship tests passed!")
    except Exception as e:
        print(f"\n❌ Relationship tests failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
