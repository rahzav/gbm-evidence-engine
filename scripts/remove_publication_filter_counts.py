from pathlib import Path

path = Path('app_ui.py')
text = path.read_text(encoding='utf-8')
old = '''    for key in context_keys:\n        count = profile.context_map.get(key)\n        label = europepmc.CONTEXT_LABELS.get(key, key.replace("_", " ").title())\n        display = f"{label} ({count:,})" if isinstance(count, int) else label\n        context_options.append(display)\n        label_to_key[display] = key\n'''
new = '''    for key in context_keys:\n        label = europepmc.CONTEXT_LABELS.get(key, key.replace("_", " ").title())\n        context_options.append(label)\n        label_to_key[label] = key\n'''
if old not in text:
    raise SystemExit('Expected disease-context option block not found')
path.write_text(text.replace(old, new, 1), encoding='utf-8')
print('PUBLICATION_FILTER_COUNTS_REMOVED')
