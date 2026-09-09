import glob
full = "（）、，．【】〔〕｛｝；：＋－＊／＝＜＞！？"
ascii = "(),.,[][]{};:+-*/=<>!?"
MAP = {ord(a): ord(b) for a,b in zip(full, ascii)}
DROP = {ord("˚"): None}
def norm(s):
    return s.translate(MAP).translate(DROP)
root = "/opt/data/lidar_platform/backend/lidar_analysis/simulation"
n =	 0
for path in glob.glob(root + "/**/*.py", recursive=True):
    with open(path, encoding="utf-8") as f:
        s = f.read()
    o = norm(s)
    if o != s:
        with open(path, "w", encoding="utf-8") as f:
            f.write(o)
        n =	 n +	 1
print("normalized", n)