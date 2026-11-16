"""Converte uma imagem em arte ASCII de duas cores para o terminal (gera terminal/art.txt).

Uso:
  python terminal/make_art.py caminho/da/imagem.png [--largura 34] [--inverter] [--limiar 245]

Dicas: imagens com o rosto/personagem bem recortado e fundo liso funcionam melhor.
Pixels transparentes ou mais claros que o --limiar viram espaço (fundo).
As áreas mais escuras usam a cor art2 (lavanda) e as mais claras a art1 (rosé).
Depois rode:  python terminal/generate.py
"""
import argparse, os
from PIL import Image, ImageOps

RAMPA = " .:-=+*#%@"           # do mais claro ao mais denso
PROPORCAO = 0.42               # célula do texto: largura/altura (8.4px x 21px no card)

ap = argparse.ArgumentParser()
ap.add_argument("imagem")
ap.add_argument("--largura", type=int, default=34)
ap.add_argument("--inverter", action="store_true", help="para imagens claras sobre fundo escuro")
ap.add_argument("--limiar", type=int, default=245, help="acima disto (0-255) é fundo")
a = ap.parse_args()

img = Image.open(a.imagem).convert("RGBA")
fundo = Image.new("RGBA", img.size, (255, 255, 255, 255))
img = Image.alpha_composite(fundo, img).convert("L")
if a.inverter:
    img = ImageOps.invert(img)
img = ImageOps.autocontrast(img, cutoff=1)
altura = max(1, round(img.height / img.width * a.largura * PROPORCAO))
img = img.resize((a.largura, altura), Image.LANCZOS)

linhas = []
for y in range(img.height):
    linha, cor_atual = "", None
    for x in range(img.width):
        v = img.getpixel((x, y))
        if v >= a.limiar:
            linha += " "
            continue
        densidade = 1 - v / 255
        ch = RAMPA[min(len(RAMPA) - 1, 1 + int(densidade * (len(RAMPA) - 1)))]
        cor = "$2" if densidade > 0.5 else "$1"
        if cor != cor_atual:
            linha += cor; cor_atual = cor
        linha += ch
    linhas.append(linha.rstrip())

while linhas and not linhas[0].replace("$1", "").replace("$2", "").strip():
    linhas.pop(0)
while linhas and not linhas[-1].replace("$1", "").replace("$2", "").strip():
    linhas.pop()

destino = os.path.join(os.path.dirname(os.path.abspath(__file__)), "art.txt")
open(destino, "w", encoding="utf-8").write("\n".join(linhas) + "\n")
print(f"art.txt gerado: {len(linhas)} linhas x {a.largura} colunas")
