import ast
import glob
files = sorted(glob.glob("backend/lidar_analysis/simulation/**/*.py", recursive=True))
fail = 0
for f in files:
    try:
        src = open(f).read()
    except OSError:
        continue
    try:
        ast.parse(src)
    except SyntaxError as e:
        fail +=  1
        print("ERR", f, e.lineno, e.msg)
print("scanned", len(files), "failures", fail)