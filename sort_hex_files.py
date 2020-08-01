import os
def organize(dir, prefix_len):
    last_cwd = os.getcwd()
    os.chdir(dir)
    existing_dirs = set()

    find = os.popen('find -type f')

    for line in find:
        filename = line[2:].strip()
        if not filename or os.path.sep in filename:
            continue
        prefix = filename[:prefix_len]
        print(filename, '==>', prefix+os.path.sep)
        if prefix not in existing_dirs:
            try:
                os.mkdir(prefix)
            except FileExistsError:
                pass
            existing_dirs.add(prefix)
        os.rename(filename, prefix+os.path.sep+filename)
    os.chdir(last_cwd)

cwd = input('Process files in what directory (type <ALL> for recursive mode): ')
if cwd == '<ALL>':
    max_depth = int(input('Maximum depth of dir tree (example: 2 results in ./de/dead/deadbeef.txt): '))
    dirs = os.popen('find -type d')
    for dir in dirs:
        dir = dir.strip()
        if dir == './':
            organize('.', 2)
        leaf = dir.split('/')[-1]
        if len(leaf)+2 > max_depth*2: continue
        organize(dir, len(leaf)+2)
else:
    prefix_len = int(input('Prefix length: '))
    organize(cwd, prefix_len)


