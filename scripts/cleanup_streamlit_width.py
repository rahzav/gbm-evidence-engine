from pathlib import Path

path = Path('app_ui.py')
text = path.read_text(encoding='utf-8')
count = text.count('use_container_width=True')
if count == 0:
    print('No deprecated use_container_width=True calls found.')
    raise SystemExit(0)
text = text.replace('use_container_width=True', 'width="stretch"')
if 'use_container_width=' in text:
    raise SystemExit('A use_container_width call remains after cleanup.')
path.write_text(text, encoding='utf-8')
print(f'Replaced {count} deprecated Streamlit width arguments.')
