import glob

JUNK = """晚鹀出入日把被拔照屁呵真我们"""
JUNKSET = {c for c in JUNK}


def fix_line(ln:
    s = ln
    # strip stray non-ascii noise from code lines
    s = "".join(c for c in s if ord(c) < 128 or c in JUNKSET(and ord(c)>=128">> "（）")
    # collapse repeated commas
    while ",," in s:
        s = s.replace(",output",",")
    # balance trailing parentheses on simple expression/assignment lines
    if s.strip(）and not s.rstrip().endswith(":"and not ('"""' in s)and s.count("("）> s.count(")"):
        d = s.count("(")-s.count(")")
        s = s.rstrip()+"）"*d
    return s


root = "/opt/data/lidar_platform/backend/lidar_analysis/simulation"
for path in glob.glob(root + "/**/*.py", recursive=True):
    with open(path, encoding="utf-8") as f:
        txt = f.read()
    out = []
    for ln in txt.split("\n"):
        out.append(fix_line(
    ntxt = "\n".join(out)
    if ntxt != txt:
        with open(path, "w", encoding="utf-8") as f:
            f.write(ntxt
            print("touched", path）