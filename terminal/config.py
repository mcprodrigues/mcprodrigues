"""
Configuração do terminal do README. EDITE SÓ ESTE ARQUIVO.
Depois rode:  python terminal/generate.py   (a GitHub Action roda sozinha 1x por dia)

Placeholders disponíveis nos valores (trocados automaticamente):
  {age}        idade (fixa em AGE, ou calculada de BIRTHDAY se preenchido)
  {repos}      repositórios próprios        {contrib}   repositórios de terceiros com contribuição
  {stars}      stars recebidas              {followers} seguidores
  {commits}    commits (inclui privados)    {loc} {loc_add} {loc_del}  linhas de código
"""

import datetime

# --- quem é você ----------------------------------------------------------------
USER = "mcprodrigues"
HANDLE = "clara@github"            # título do card e do prompt
AGE = "21 years"                   # usado se BIRTHDAY for None
BIRTHDAY = None                    # ex.: datetime.date(2005, 1, 31) -> idade se atualiza sozinha

LOC_COUNT_FORKS = False            # contar forks nas linhas de código?

# --- linhas do card ---------------------------------------------------------------
#   ("kv", "Label:", "valor")                     linha com pontilhado
#   ("gap",)                                      linha em branco
#   ("rule", "Título")                            divisória  - Título --------
#   ("stat2", ("A:", "{x}"), ("B:", "{y}"))       duas colunas
#   ("loc", "Lines of Code:")                     total (+adicionadas, -removidas)
ROWS = [
    ("kv", "OS:",               "Linux Mint · Cinnamon"),
    ("kv", "Uptime:",           "{age}"),
    ("kv", "Host:",             "Exitus"),
    ("kv", "Role:",             "Software / AI Engineer"),
    ("kv", "Kernel:",           "Universidade de Fortaleza"),
    ("kv", "Degree:",           "Systems Analysis & Dev. (final semester)"),
    ("kv", "IDE/Text.Editor:",  "VSCode, Claude Code"),
    ("gap",),
    ("kv", "Languages.Code:",   "Python, TypeScript, JavaScript, Java"),
    ("kv", "Languages.Real:",   "Português, English"),
    ("gap",),
    ("kv", "Stack.Backend:",    "NestJS, Node.js, FastAPI, Spring"),
    ("kv", "Stack.AI:",         "LangChain, Haystack, OpenAI, Ollama"),
    ("kv", "Stack.Data:",       "Postgres, MongoDB, Elasticsearch"),
    ("gap",),
    ("kv", "Focus:",            "Multi-agent systems, RAG, LLM pipelines"),
    ("kv", "Hobbies:",          "Game Dev, Pixel Art"),
    ("gap",),
    ("rule", "Contact"),
    ("kv", "Email:",            "dev.mcprodrigues@gmail.com"),
    ("kv", "LinkedIn:",         "linkedin.com/in/mcprodrigues"),
    ("gap",),
    ("rule", "GitHub Stats"),
    ("stat2", ("Repos:", "{repos} {{+{contrib}}}"), ("Stars:", "{stars}")),
    ("stat2", ("Commits:", "{commits}"), ("Followers:", "{followers}")),
    ("loc", "Lines of Code:"),
]

# --- janela -----------------------------------------------------------------------
WINDOW_TITLE = "clara@github: ~"
PROMPT_CMD = "fastfetch"
ART_FILE = "art.txt"               # $1 / $2 marcam as duas cores da arte
BRAILLE_PITCH = 6.5                # arte em braille: distância entre os pontos (px)
BRAILLE_DOT = 2.0                  # arte em braille: raio de cada ponto (px)
INFO_WIDTH = 56                    # largura da coluna de texto, em caracteres
ART_GAP = 5                        # espaço entre a arte e o texto, em caracteres
FONT_SIZE = 14.0
LINE_HEIGHT = 1.5

# --- cores (mesma paleta pastel do setup) ------------------------------------------
THEMES = {
    "dark": {
        "bg": "#171416", "bar": "#1f1b1e", "border": "#2e282c",
        "text": "#e9e4e7", "key": "#c4b0dc", "dim": "#5c5357", "title": "#e3a1b0",
        "add": "#a8cbb4", "del": "#e88a9c", "path": "#c4b0dc",
        "art1": "#e3a1b0", "art2": "#d3c3e6",
        "dots": ["#e3a1b0", "#e6c9a3", "#a8cbb4"],
    },
    "light": {
        "bg": "#fbf6f4", "bar": "#f3e9e8", "border": "#e8dcdc",
        "text": "#3b3437", "key": "#8e6aa8", "dim": "#cbbec2", "title": "#b9637f",
        "add": "#5f9474", "del": "#c0566f", "path": "#8e6aa8",
        "art1": "#c5869d", "art2": "#9c84bd",
        "dots": ["#e3a1b0", "#e6c9a3", "#a8cbb4"],
    },
}
