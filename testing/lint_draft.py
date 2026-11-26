import re

txt = open("Draft_Isi_Kelompok.md", encoding="utf-8").read()
body = txt.split("## BAB 1 PENDAHULUAN")[1].split("## DAFTAR PUSTAKA")[0]
kp = txt.split("## KATA PENGANTAR")[1].split("## BAB 1 PENDAHULUAN")[0]
dp = txt.split("## DAFTAR PUSTAKA")[1]

print("EM_DASH_COUNT:", txt.count("\u2014"))

forb = [
    "komprehensif", "holistik", "signifikan", "krusial", "esensial",
    "fundamental", "optimalisasi", "implementatif", "transformatif", "inovatif",
    "revolusioner", "robust", "seamless", "akibatnya", "selain itu",
    "oleh karena itu", "dengan demikian", "lebih lanjut", "di sisi lain",
    "pada akhirnya", "secara keseluruhan", "hal ini menunjukkan bahwa",
    "perlu dicatat bahwa", "tidak dapat dipungkiri", "dalam hal ini",
    "di era digital saat ini", "seiring perkembangan zaman",
    "dalam dunia yang semakin", "memainkan peran penting", "menjadi kunci",
    "tidak hanya", "tetapi juga", "berbagai macam",
    "memberikan kemudahan bagi pengguna", "nah",
]
low = (kp + "\n" + body).lower()
found_forb = [w for w in forb if re.search(r"\b" + re.escape(w) + r"\b", low)]
print("FORBIDDEN_FOUND:", found_forb)

in_code = False
paras = []
list_items = []
for line in (kp + "\n" + body).splitlines():
    s = line.strip()
    if s.startswith("```"):
        in_code = not in_code
        continue
    if in_code or s.startswith("#") or s.startswith("|") or s.startswith("!") or s.startswith("Gambar ") or s.startswith("Tabel ") or s.startswith("Medan,") or s == "Penulis" or s == "---" or not s:
        continue
    if re.match(r"^\d+\.\s+", s):
        list_items.append(re.sub(r"^\d+\.\s+", "", s))
    else:
        paras.append(s)

one_sent = []
for p in paras:
    ps = re.split(r"(?<=[.!?])\s+(?=[A-Z*\[])", p)
    if len(ps) < 2:
        one_sent.append(p)
print("ONE_SENT_PARAS:", len(one_sent))
for x in one_sent:
    print(" ", x)

all_sents = []
for block in paras + list_items:
    for s in re.split(r"(?<=[.!?])\s+(?=[A-Z*\[])", block):
        all_sents.append(s.strip())

long_sents = [(len(s.split()), s) for s in all_sents if len(s.split()) > 30]
print("TOTAL_SENTS:", len(all_sents), "MAX_WORDS:", max((len(s.split()) for s in all_sents), default=0))
for l, s in long_sents:
    print(f"  LONG ({l}): {s}")

# Check italic consistency for key foreign terms
terms = ["WebGIS", "raster", "vector", "isochrone", "blindspot", "hotspot", "layout", "flowchart", "zonal statistics", "print layout", "custom layer", "fill-extrusion", "client-side", "open source", "headless", "black box testing"]
print("ITALIC_CHECK:")
for t in terms:
    # find bare occurrences not inside *...* and not inside code/paths/headers/URLs
    plain = body
    plain = re.sub(r"```.*?```", "", plain, flags=re.S)
    plain = re.sub(r"`[^`]+`", "", plain)
    plain = re.sub(r"!\[[^\]]*\]\([^\)]+\)", "", plain)
    ital = len(re.findall(r"\*[^*]*" + re.escape(t) + r"[^*]*\*", plain, flags=re.I))
    bare = len(re.findall(r"(?<!\*)\b" + re.escape(t) + r"\b(?!\*)", plain, flags=re.I))
    if ital > 0 and bare > 0:
        print(f"  MIXED {t}: italic={ital}, bare={bare}")

cites = re.findall(r"\(([A-Z][A-Za-z0-9.&,\s-]+?,\s*\d{4})\)", body)
print("CITES_COUNT:", len(cites), "UNIQUE:", len(set(cites)))
for i, m in enumerate(re.finditer(r"\(([A-Z][A-Za-z0-9.&,\s-]+?,\s*\d{4})\)", body), 1):
    idx = m.start()
    sec = "Unknown"
    for h in re.finditer(r"^#{2,4}\s+(.+)$", body[:idx], re.M):
        sec = h.group(1).replace("\t", " ")
    pre = " ".join(body[max(0, idx - 85) : idx].split())
    words_pre = " ".join(pre.split()[-7:])
    print(f"| {i} | {sec} | ...{words_pre} | ({m.group(1)}) |")
