"""Gera terminal/dark.svg e terminal/light.svg: um card estilo fastfetch para o README.

Token do GitHub (para estatísticas, incluindo contribuições privadas):
  - na Action: secret ACCESS_TOKEN -> variável GH_TOKEN
  - localmente: usa `gh auth token` se GH_TOKEN não estiver definido
Sem token, as estatísticas aparecem como "-".
"""
import base64, datetime, hashlib, io, json, os, re, subprocess, sys, time, urllib.request
from html import escape

AQUI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, AQUI)
import config as C  # noqa: E402

CACHE = os.path.join(AQUI, ".cache", "loc.json")
API = "https://api.github.com"


# ── GitHub ─────────────────────────────────────────────────────────────────────
def token():
    t = os.environ.get("GH_TOKEN") or os.environ.get("GITHUB_TOKEN")
    if t:
        return t
    try:
        return subprocess.run(["gh", "auth", "token"], capture_output=True, text=True, check=True).stdout.strip()
    except Exception:
        return None


def req(url, tok, dados=None):
    r = urllib.request.Request(url, data=json.dumps(dados).encode() if dados else None,
                               headers={"Authorization": f"bearer {tok}", "User-Agent": "profile-terminal",
                                        "Accept": "application/vnd.github+json"})
    with urllib.request.urlopen(r, timeout=60) as resp:
        return resp.status, (json.loads(resp.read() or b"null"))


def gql(q, tok, **v):
    _, r = req(f"{API}/graphql", tok, {"query": q, "variables": v})
    if r.get("errors"):
        raise RuntimeError(r["errors"])
    return r["data"]


def repos_paginados(tok, campo, extra):
    nos, cursor = [], None
    while True:
        q = f"""query($u:String!,$c:String){{user(login:$u){{{campo}(first:100,after:$c{extra}){{
              totalCount pageInfo{{hasNextPage endCursor}}
              nodes{{nameWithOwner stargazerCount isFork pushedAt}} }} }} }}"""
        d = gql(q, tok, u=C.USER, c=cursor)["user"][campo]
        nos += d["nodes"]
        if not d["pageInfo"]["hasNextPage"]:
            return d["totalCount"], nos
        cursor = d["pageInfo"]["endCursor"]


def commits_totais(tok, criado):
    ano0, hoje = int(criado[:4]), datetime.datetime.now(datetime.timezone.utc)
    partes = []
    for ano in range(ano0, hoje.year + 1):
        ini = f"{ano}-01-01T00:00:00Z"
        fim = f"{ano}-12-31T23:59:59Z" if ano < hoje.year else hoje.strftime("%Y-%m-%dT%H:%M:%SZ")
        partes.append(f'y{ano}: contributionsCollection(from:"{ini}", to:"{fim}")'
                      "{totalCommitContributions restrictedContributionsCount}")
    d = gql("query($u:String!){user(login:$u){" + " ".join(partes) + "}}", tok, u=C.USER)["user"]
    return sum(v["totalCommitContributions"] + v["restrictedContributionsCount"] for v in d.values())


def linhas_de_codigo(tok, repos):
    """Soma adições/remoções do usuário via /stats/contributors, com cache por repositório.
    As chaves do cache são hashes: nomes de repositórios privados não ficam expostos."""
    os.makedirs(os.path.dirname(CACHE), exist_ok=True)
    cache = json.load(open(CACHE)) if os.path.exists(CACHE) else {}
    novo, add, dele = {}, 0, 0
    for r in repos:
        chave = hashlib.sha256(r["nameWithOwner"].encode()).hexdigest()[:16]
        antigo = cache.get(chave)
        if antigo and antigo["pushed"] == r["pushedAt"]:
            novo[chave] = antigo
        else:
            a = d = 0
            for _ in range(8):  # a API responde 202 enquanto calcula
                try:
                    st, dados = req(f"{API}/repos/{r['nameWithOwner']}/stats/contributors", tok)
                except Exception:
                    st, dados = 0, None
                if st == 200 and isinstance(dados, list):
                    for autor in dados:
                        if (autor.get("author") or {}).get("login", "").lower() == C.USER.lower():
                            a = sum(w["a"] for w in autor["weeks"]); d = sum(w["d"] for w in autor["weeks"])
                    break
                if st == 202:
                    time.sleep(3); continue
                break
            novo[chave] = {"pushed": r["pushedAt"], "add": a, "del": d}
        add += novo[chave]["add"]; dele += novo[chave]["del"]
    json.dump(novo, open(CACHE, "w"), indent=1, sort_keys=True)
    return add, dele


def idade():
    if C.BIRTHDAY:
        h = datetime.date.today(); b = C.BIRTHDAY
        return f"{h.year - b.year - ((h.month, h.day) < (b.month, b.day))} years"
    return C.AGE


def estatisticas():
    base = {"age": idade(), "repos": "-", "contrib": "-", "stars": "-", "followers": "-",
            "commits": "-", "loc": "-", "loc_add": "-", "loc_del": "-"}
    tok = token()
    if not tok:
        if os.environ.get("GITHUB_ACTIONS"):
            # na Action sem o secret ACCESS_TOKEN: não sobrescreve os SVGs com "-"
            print("aviso: secret ACCESS_TOKEN não configurado; nada foi alterado")
            sys.exit(0)
        print("aviso: sem token, estatísticas vazias")
        return base
    u = gql("query($u:String!){user(login:$u){createdAt followers{totalCount}}}", tok, u=C.USER)["user"]
    n_repos, proprios = repos_paginados(tok, "repositories", ",ownerAffiliations:OWNER")
    n_contrib, contrib = repos_paginados(
        tok, "repositoriesContributedTo",
        ",includeUserRepositories:false,contributionTypes:[COMMIT,PULL_REQUEST,REPOSITORY]")
    alvo = [r for r in proprios if C.LOC_COUNT_FORKS or not r["isFork"]] + contrib
    add, dele = linhas_de_codigo(tok, alvo)
    fmt = lambda n: f"{n:,}"
    base.update(repos=fmt(n_repos), contrib=fmt(n_contrib), followers=fmt(u["followers"]["totalCount"]),
                stars=fmt(sum(r["stargazerCount"] for r in proprios)),
                commits=fmt(commits_totais(tok, u["createdAt"])),
                loc=fmt(add - dele), loc_add=fmt(add), loc_del=fmt(dele))
    return base


# ── layout em "células" de texto ───────────────────────────────────────────────
# Cada linha é uma lista de (texto, papel) onde papel é uma chave de cor do tema.
def linha_kv(rot, val, largura):
    pontos = max(1, largura - len(rot) - len(val))
    return [(rot, "key"), ("." * pontos, "dim"), (val, "text")]


def linhas_info(st):
    W = C.INFO_WIDTH
    sub = lambda s: s.format(**st)
    out = [[(C.HANDLE, "title"), ("-" * (W - len(C.HANDLE)), "dim")], []]
    for row in C.ROWS:
        tipo = row[0]
        if tipo == "kv":
            out.append(linha_kv(row[1], sub(row[2]), W))
        elif tipo == "gap":
            out.append([])
        elif tipo == "rule":
            t = f"- {row[1]} "
            out.append([("- ", "dim"), (row[1], "title"), (" " + "-" * (W - len(t)), "dim")])
        elif tipo == "stat2":
            meia = (W - 1) // 2
            esq = linha_kv(row[1][0], sub(row[1][1]), meia)
            dir_ = linha_kv(row[2][0], sub(row[2][1]), W - meia - 1)
            out.append(esq + [("|", "dim")] + dir_)
        elif tipo == "loc":
            extra = f" ({st['loc_add']}++, {st['loc_del']}--)"
            base = linha_kv(row[1], st["loc"], W - len(extra))
            out.append(base + [(" (", "dim"), (st["loc_add"] + "++", "add"), (", ", "dim"),
                               (st["loc_del"] + "--", "del"), (")", "dim")])
    return out


def linhas_arte():
    caminho = os.path.join(AQUI, C.ART_FILE)
    out = []
    for crua in open(caminho, encoding="utf-8").read().rstrip("\n").split("\n"):
        segs, papel = [], "art2"
        for parte in re.split(r"(\$[12])", crua):
            if parte in ("$1", "$2"):
                papel = "art1" if parte == "$1" else "art2"
            elif parte:
                segs.append((parte, papel))
        out.append(segs)
    return out


def largura_texto(segs):
    return sum(len(t) for t, _ in segs)


# ── SVG ────────────────────────────────────────────────────────────────────────
def fonte_embutida(texto):
    from fontTools import subset
    from fontTools.ttLib import TTFont
    css = []
    for peso, arq in ((400, "JetBrainsMono-Regular.ttf"), (700, "JetBrainsMono-Bold.ttf")):
        f = TTFont(os.path.join(AQUI, "fonts", arq))
        op = subset.Options(); op.hinting = False; op.layout_features = []; op.name_IDs = []
        op.notdef_outline = True; op.drop_tables += ['DSIG', 'GDEF', 'GPOS', 'GSUB']
        s = subset.Subsetter(op)
        s.populate(text=texto)
        s.subset(f)
        buf = io.BytesIO(); f.save(buf)
        b64 = base64.b64encode(buf.getvalue()).decode()
        css.append(f"@font-face{{font-family:'JBM';font-weight:{peso};"
                   f"src:url(data:font/ttf;base64,{b64}) format('truetype');}}")
    return "".join(css)


# Braille (U+2800–U+28FF): cada caractere é uma grade 2x4 de pontos. A JetBrains Mono não
# tem esses glifos, então desenhamos cada ponto como um círculo (fica igual em qualquer lugar).
BITS = [(0, 0, 0x01), (0, 1, 0x02), (0, 2, 0x04), (1, 0, 0x08),
        (1, 1, 0x10), (1, 2, 0x20), (0, 3, 0x40), (1, 3, 0x80)]


def eh_braille(arte):
    return any(0x2800 <= ord(ch) <= 0x28FF for l in arte for t, _ in l for ch in t)


def pontos_braille(arte, x0, y0, passo, raio, T):
    por_cor = {}
    for i, segs in enumerate(arte):
        j = 0
        for t, papel in segs:
            for ch in t:
                cod = ord(ch) - 0x2800
                if 0 <= cod <= 0xFF:
                    for dx, dy, bit in BITS:
                        if cod & bit:
                            cx = x0 + (j * 2 + dx) * passo + passo / 2
                            cy = y0 + (i * 4 + dy) * passo + passo / 2
                            por_cor.setdefault(T[papel], []).append(f'<circle cx="{cx:.1f}" cy="{cy:.1f}" r="{raio}"/>')
                j += 1
    return "".join(f'<g fill="{cor}">{"".join(c)}</g>' for cor, c in por_cor.items())


def svg(tema, info, arte):
    T = C.THEMES[tema]
    fs, lh = C.FONT_SIZE, C.FONT_SIZE * C.LINE_HEIGHT
    cw = fs * 0.6                                   # avanço do JetBrains Mono (600/1000 em)
    pad, barra = 28, 38
    larg_arte = max((largura_texto(l) for l in arte), default=0)
    braille = eh_braille(arte)
    passo = getattr(C, "BRAILLE_PITCH", 5.0)
    if braille:
        import math
        larg_arte = math.ceil(larg_arte * 2 * passo / cw)   # largura em "colunas de texto"
    col_info = larg_arte + C.ART_GAP if arte else 0
    n = len(info) if braille else max(len(info), len(arte))
    desloc_arte = max(0, (len(info) - len(arte)) // 2)
    W = round(pad * 2 + (col_info + C.INFO_WIDTH) * cw)
    y0 = barra + pad + fs                           # primeira linha (prompt)
    corpo0 = y0 + lh * 2                            # depois do prompt + linha em branco
    H = round(corpo0 + lh * (n + 1) + pad)

    def texto(x_col, y, segs, peso=None):
        spans = "".join(f'<tspan fill="{T[p]}">{escape(t)}</tspan>' for t, p in segs)
        fw = f' font-weight="{peso}"' if peso else ""
        return f'<text x="{pad + x_col * cw:.1f}" y="{y:.1f}"{fw}>{spans}</text>'

    prompt = [(C.HANDLE, "title"), (":", "dim"), ("~", "path"), ("$ ", "dim")]
    corpo = [texto(0, y0, prompt, 700)[:-7] + f'<tspan fill="{T["text"]}" font-weight="400">{C.PROMPT_CMD}</tspan></text>']
    if braille:
        topo = corpo0 - fs * 0.8
        alt_info = (len(info) - 1) * lh + fs
        alt_arte = len(arte) * 4 * passo
        corpo.append(pontos_braille(arte, pad, topo + (alt_info - alt_arte) / 2, passo,
                                    getattr(C, "BRAILLE_DOT", 1.6), T))
    else:
        for i, segs in enumerate(arte):
            corpo.append(texto(0, corpo0 + (i + desloc_arte) * lh, segs))
    for i, segs in enumerate(info):
        if segs:
            peso = 700 if i == 0 else None
            corpo.append(texto(col_info, corpo0 + i * lh, segs, peso))
    y_fim = corpo0 + n * lh + lh
    corpo.append(texto(0, y_fim, prompt, 700))
    cx = pad + largura_texto(prompt) * cw
    corpo.append(f'<rect x="{cx:.1f}" y="{y_fim - fs + 2:.1f}" width="{cw:.1f}" height="{fs + 2:.1f}" '
                 f'rx="1.5" fill="{T["title"]}"><animate attributeName="opacity" values="1;1;0;0" '
                 f'dur="1.1s" repeatCount="indefinite"/></rect>')

    usados = "".join(t for l in info + arte for t, _ in l) + "".join(t for t, _ in prompt) \
        + C.PROMPT_CMD + C.WINDOW_TITLE + "0123456789,+-|.:~$"
    bolinhas = "".join(f'<circle cx="{22 + i * 20}" cy="{barra / 2}" r="6" fill="{c}"/>'
                       for i, c in enumerate(T["dots"]))
    return f"""<svg xmlns="http://www.w3.org/2000/svg" xml:space="preserve" width="{W}" height="{H}" viewBox="0 0 {W} {H}">
<style>{fonte_embutida(usados)} text{{font-family:'JBM','JetBrains Mono',monospace;font-size:{fs}px;white-space:pre;font-variant-ligatures:none;font-feature-settings:'liga' 0,'calt' 0}}</style>
<rect x="0.5" y="0.5" width="{W - 1}" height="{H - 1}" rx="12" fill="{T['bg']}" stroke="{T['border']}"/>
<path d="M0.5 {barra} V12.5 a12 12 0 0 1 12 -12 H{W - 12.5} a12 12 0 0 1 12 12 V{barra} Z" fill="{T['bar']}"/>
<line x1="0.5" y1="{barra}" x2="{W - 0.5}" y2="{barra}" stroke="{T['border']}"/>
{bolinhas}
<text x="{W / 2}" y="{barra / 2 + 4.5}" text-anchor="middle" fill="{T['dim']}" font-size="{fs - 1}px">{escape(C.WINDOW_TITLE)}</text>
{chr(10).join(corpo)}
</svg>
"""


def main():
    st = estatisticas()
    info, arte = linhas_info(st), linhas_arte()
    for tema in C.THEMES:
        caminho = os.path.join(AQUI, f"{tema}.svg")
        open(caminho, "w", encoding="utf-8").write(svg(tema, info, arte))
        print(f"gerado {caminho} ({os.path.getsize(caminho) // 1024} KB)")
    print({k: v for k, v in st.items()})


if __name__ == "__main__":
    main()
