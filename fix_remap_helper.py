import sys

filepath = 'tcia-remapping-skill/remap_helper.py'
with open(filepath, 'r') as f:
    lines = f.readlines()

new_lines = []
for line in lines:
    if 'df = pd.DataFrame(data)' in line:
        new_lines.append(line)
        new_lines.append('    for col in df.columns:\n')
        new_lines.append('        df[col] = df[col].apply(lambda x: str(x) if isinstance(x, list) else x)\n')
        continue
    new_lines.append(line)

with open(filepath, 'w') as f:
    f.writelines(new_lines)
