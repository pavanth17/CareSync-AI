import os
root = r"c:\projects\Patient-Care"
null_files = []
for dirpath, dirs, files in os.walk(root):
    for f in files:
        if f.endswith('.py') or f.endswith('.html') or f.endswith('.js') or f.endswith('.css'):
            path = os.path.join(dirpath, f)
            try:
                with open(path, 'rb') as fh:
                    data = fh.read()
                    if b'\x00' in data:
                        null_files.append(path)
            except Exception as e:
                print('ERR reading', path, e)
if null_files:
    print('FILES_WITH_NULLS:')
    for p in null_files:
        print(p)
else:
    print('NO_NULLS')
