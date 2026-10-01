#!/usr/bin/env python3
"""Genera el material de estudio de una clase a partir de material.json.

Uso:
    python3 generar_material.py <ruta/material.json> [--out-dir DIR] [--sin-pdf]

Salida (en la carpeta del JSON, o en --out-dir):
    <fecha>-<tema>.html             HTML interactivo
    <fecha>-<tema>-imprimible.html  versión para imprimir
    <fecha>-<tema>.pdf              PDF (requiere Chromium / Chrome / Edge)

Sin dependencias externas: solo la biblioteca estándar de Python.
"""

import argparse
import html
import json
import os
import re
import shutil
import subprocess
import sys
import unicodedata
from pathlib import Path

SKILL_DIR = Path(__file__).resolve().parent.parent
ASSETS = SKILL_DIR / "assets"

TIPOS_FRASE = {
    "parcial": "Entra en el parcial",
    "advertencia": "Advertencia",
    "consejo": "Consejo",
    "ejemplo": "Ejemplo",
    "no_se_toma": "No se toma",
}


# ---------------------------------------------------------------------------
# Validación
# ---------------------------------------------------------------------------

def validar(m):
    errores, avisos = [], []

    for campo in ("materia", "tema", "fecha", "resumen"):
        if not str(m.get(campo, "")).strip():
            errores.append(f"Falta '{campo}'.")
    if m.get("fecha") and not re.fullmatch(r"\d{4}-\d{2}-\d{2}", str(m["fecha"])):
        errores.append("'fecha' tiene que tener formato AAAA-MM-DD.")

    secciones = m.get("secciones") or []
    if not secciones:
        errores.append("'secciones' está vacío: tiene que haber al menos un tema.")
    for i, s in enumerate(secciones):
        if not s.get("titulo") or not s.get("contenido"):
            errores.append(f"secciones[{i}] necesita 'titulo' y 'contenido'.")
        if "profe" in s and not isinstance(s["profe"], list):
            errores.append(f"secciones[{i}].profe tiene que ser una lista de strings.")

    for i, q in enumerate(m.get("quiz") or []):
        ops = q.get("opciones") or []
        c = q.get("correcta")
        if not q.get("pregunta") or len(ops) < 2:
            errores.append(f"quiz[{i}] necesita 'pregunta' y al menos 2 'opciones'.")
        elif not isinstance(c, int) or not 0 <= c < len(ops):
            errores.append(f"quiz[{i}].correcta tiene que ser un índice entre 0 y {len(ops) - 1}.")

    for i, f in enumerate(m.get("flashcards") or []):
        if not f.get("pregunta") or not f.get("respuesta"):
            errores.append(f"flashcards[{i}] necesita 'pregunta' y 'respuesta'.")

    for i, g in enumerate(m.get("glosario") or []):
        if not g.get("termino") or not g.get("definicion"):
            errores.append(f"glosario[{i}] necesita 'termino' y 'definicion'.")

    for i, fr in enumerate(m.get("frases_profe") or []):
        if fr.get("tipo") and fr["tipo"] not in TIPOS_FRASE:
            avisos.append(f"frases_profe[{i}].tipo '{fr['tipo']}' no es uno de {list(TIPOS_FRASE)}; se muestra como 'consejo'.")

    n_fc, n_q = len(m.get("flashcards") or []), len(m.get("quiz") or [])
    if n_fc < 8:
        avisos.append(f"Hay {n_fc} flashcards (se recomiendan 8-20).")
    if n_q < 6:
        avisos.append(f"Hay {n_q} preguntas de quiz (se recomiendan 6-12).")
    if not m.get("glosario"):
        avisos.append("El glosario está vacío.")
    if n_q >= 4:
        posiciones = {q.get("correcta") for q in m["quiz"]}
        if len(posiciones) == 1:
            avisos.append("En el quiz la respuesta correcta está siempre en la misma posición; conviene variarla.")

    return errores, avisos


# ---------------------------------------------------------------------------
# Markdown mínimo -> HTML
# ---------------------------------------------------------------------------

def esc(s):
    return html.escape(str(s), quote=True)


def inline(s):
    """Markdown en línea: código, matemática, links, negrita, itálica."""
    guardados = []

    def guardar(fragmento):
        guardados.append(fragmento)
        return f"\x00{len(guardados) - 1}\x00"

    s = str(s)
    s = re.sub(r"`([^`]+)`", lambda m: guardar(f"<code>{esc(m[1])}</code>"), s)
    s = re.sub(r"\$\$(.+?)\$\$", lambda m: guardar(esc(m[0])), s)
    s = re.sub(r"(?<![\\$])\$(?=\S)([^$\n]*?\S)\$(?!\$)", lambda m: guardar(esc(m[0])), s)
    s = esc(s)
    s = re.sub(
        r"\[([^\]]+)\]\((https?://[^)\s]+)\)",
        lambda m: guardar(f'<a href="{m[2]}" target="_blank" rel="noopener">{m[1]}</a>'),
        s,
    )
    s = re.sub(r"\*\*(?=\S)(.+?)(?<=\S)\*\*", r"<strong>\1</strong>", s)
    s = re.sub(r"__(?=\S)(.+?)(?<=\S)__", r"<strong>\1</strong>", s)
    s = re.sub(r"(?<![*\w])\*(?=\S)(.+?)(?<=\S)\*(?![*\w])", r"<em>\1</em>", s)
    s = re.sub(r"(?<![_\w])_(?=\S)(.+?)(?<=\S)_(?![_\w])", r"<em>\1</em>", s)
    while "\x00" in s:
        s = re.sub(r"\x00(\d+)\x00", lambda m: guardados[int(m[1])], s)
    return s


RE_LISTA = re.compile(r"^(\s*)([-*+]|\d+[.)])\s+(.*)$")
RE_TITULO = re.compile(r"^(#{1,6})\s+(.*)$")
RE_SEP_TABLA = re.compile(r"^\s*\|?\s*:?-{2,}:?\s*(\|\s*:?-{2,}:?\s*)*\|?\s*$")


def _celdas(linea):
    """Divide una fila de tabla por '|', sin cortar dentro de $...$, `...` ni en '\\|'."""
    linea = linea.strip()
    if linea.startswith("|"):
        linea = linea[1:]
    if linea.endswith("|") and not linea.endswith("\\|"):
        linea = linea[:-1]
    celdas, actual, en_math, en_code, i = [], [], False, False, 0
    while i < len(linea):
        c = linea[i]
        if c == "\\" and i + 1 < len(linea) and linea[i + 1] == "|" and not en_math:
            actual.append("|")
            i += 2
            continue
        if c == "`" and not en_math:
            en_code = not en_code
        elif c == "$" and not en_code:
            en_math = not en_math
        if c == "|" and not en_math and not en_code:
            celdas.append("".join(actual).strip())
            actual = []
        else:
            actual.append(c)
        i += 1
    celdas.append("".join(actual).strip())
    return celdas


def _es_inicio_bloque(lineas, i):
    l = lineas[i]
    if l.strip().startswith(("```", "$$", ">")) or RE_TITULO.match(l) or RE_LISTA.match(l):
        return True
    if l.strip().startswith("|") and i + 1 < len(lineas) and RE_SEP_TABLA.match(lineas[i + 1]):
        return True
    return False


def _lista(items):
    out, pila = [], []  # pila de (indentación, tag)
    for indent, ordenada, texto in items:
        tag = "ol" if ordenada else "ul"
        if not pila or indent > pila[-1][0]:
            out.append(f"<{tag}>")
            pila.append((indent, tag))
        else:
            while len(pila) > 1 and indent < pila[-1][0]:
                out.append(f"</li></{pila.pop()[1]}>")
            out.append("</li>")
        out.append(f"<li>{inline(texto)}")
    while pila:
        out.append(f"</li></{pila.pop()[1]}>")
    return "".join(out)


def md(texto):
    if not texto:
        return ""
    lineas = str(texto).replace("\r\n", "\n").split("\n")
    out, i, n = [], 0, len(lineas)
    while i < n:
        l = lineas[i]
        s = l.strip()

        if not s:
            i += 1
            continue

        if s.startswith("```"):
            lang = s[3:].strip()
            i += 1
            cuerpo = []
            while i < n and not lineas[i].strip().startswith("```"):
                cuerpo.append(lineas[i])
                i += 1
            i += 1
            cls = f' class="language-{esc(lang)}"' if lang else ""
            out.append(f"<pre><code{cls}>{esc(chr(10).join(cuerpo))}</code></pre>")
            continue

        if s.startswith("$$"):
            if s.endswith("$$") and len(s) > 4:
                out.append(f'<div class="math-block">{esc(s)}</div>')
                i += 1
                continue
            cuerpo = [s]
            i += 1
            while i < n:
                cuerpo.append(lineas[i])
                if lineas[i].strip().endswith("$$"):
                    i += 1
                    break
                i += 1
            out.append(f'<div class="math-block">{esc(chr(10).join(cuerpo))}</div>')
            continue

        m = RE_TITULO.match(s)
        if m:
            nivel = min(len(m[1]) + 2, 6)
            out.append(f"<h{nivel}>{inline(m[2])}</h{nivel}>")
            i += 1
            continue

        if s.startswith("|") and i + 1 < n and RE_SEP_TABLA.match(lineas[i + 1]):
            cab = _celdas(s)
            i += 2
            filas = []
            while i < n and lineas[i].strip().startswith("|"):
                filas.append(_celdas(lineas[i]))
                i += 1
            t = ["<div class=\"table-wrap\"><table><thead><tr>"]
            t += [f"<th>{inline(c)}</th>" for c in cab]
            t.append("</tr></thead><tbody>")
            for f in filas:
                t.append("<tr>" + "".join(f"<td>{inline(c)}</td>" for c in f) + "</tr>")
            t.append("</tbody></table></div>")
            out.append("".join(t))
            continue

        if s.startswith(">"):
            cita = []
            while i < n and lineas[i].strip().startswith(">"):
                cita.append(re.sub(r"^\s*>\s?", "", lineas[i]))
                i += 1
            out.append(f"<blockquote>{md(chr(10).join(cita))}</blockquote>")
            continue

        if RE_LISTA.match(l):
            items = []
            while i < n:
                lm = RE_LISTA.match(lineas[i])
                if lm:
                    items.append([len(lm[1].expandtabs(4)), lm[2][0].isdigit(), lm[3]])
                    i += 1
                elif lineas[i].strip() and lineas[i][:1] in (" ", "\t") and items:
                    items[-1][2] += " " + lineas[i].strip()
                    i += 1
                else:
                    break
            out.append(_lista(items))
            continue

        parrafo = [s]
        i += 1
        while i < n and lineas[i].strip() and not _es_inicio_bloque(lineas, i):
            parrafo.append(lineas[i].strip())
            i += 1
        out.append(f"<p>{inline(' '.join(parrafo))}</p>")

    return "\n".join(out)


# ---------------------------------------------------------------------------
# Preparación de datos
# ---------------------------------------------------------------------------

def slugify(s):
    s = unicodedata.normalize("NFKD", str(s)).encode("ascii", "ignore").decode()
    s = re.sub(r"[^a-zA-Z0-9]+", "-", s).strip("-").lower()
    return s[:60].strip("-") or "clase"


def renderizar(m):
    """Copia de los datos con los textos ya convertidos a HTML (para el HTML interactivo)."""
    tipo_ok = lambda t: t if t in TIPOS_FRASE else "consejo"
    return {
        "materia": m["materia"],
        "tema": m["tema"],
        "fecha": m["fecha"],
        "profesor": m.get("profesor", ""),
        "archivos": m.get("archivos") or [],
        "resumen": md(m["resumen"]),
        "secciones": [
            {
                "titulo": inline(s["titulo"]),
                "contenido": md(s["contenido"]),
                "profe": [inline(p) for p in s.get("profe") or []],
                "importante": bool(s.get("importante")),
                "referencia": inline(s.get("referencia", "")),
            }
            for s in m["secciones"]
        ],
        "frases_profe": [
            {
                "texto": inline(f.get("texto", "")),
                "tipo": tipo_ok(f.get("tipo")),
                "etiqueta": TIPOS_FRASE[tipo_ok(f.get("tipo"))],
                "contexto": inline(f.get("contexto", "")),
            }
            for f in m.get("frases_profe") or []
        ],
        "glosario": [
            {"termino": inline(g["termino"]), "plano": str(g["termino"]) + " " + str(g["definicion"]), "definicion": md(g["definicion"])}
            for g in sorted(m.get("glosario") or [], key=lambda g: slugify(g["termino"]))
        ],
        "flashcards": [{"pregunta": md(f["pregunta"]), "respuesta": md(f["respuesta"])} for f in m.get("flashcards") or []],
        "quiz": [
            {
                "pregunta": md(q["pregunta"]),
                "opciones": [inline(o) for o in q["opciones"]],
                "correcta": q["correcta"],
                "explicacion": md(q.get("explicacion", "")),
            }
            for q in m.get("quiz") or []
        ],
        "dudas": [{"pregunta": inline(d.get("pregunta", "")), "respuesta": md(d.get("respuesta", ""))} for d in m.get("dudas") or []],
        "para_repasar": [inline(p) for p in m.get("para_repasar") or []],
        "no_visto": [inline(p) for p in m.get("no_visto") or []],
    }


def fecha_larga(f):
    meses = ["enero", "febrero", "marzo", "abril", "mayo", "junio", "julio",
             "agosto", "septiembre", "octubre", "noviembre", "diciembre"]
    try:
        a, mes, d = (int(x) for x in f.split("-"))
        return f"{d} de {meses[mes - 1]} de {a}"
    except Exception:
        return f


# ---------------------------------------------------------------------------
# HTML interactivo
# ---------------------------------------------------------------------------

def html_interactivo(m, datos, nombre_pdf):
    plantilla = (ASSETS / "interactivo.html").read_text(encoding="utf-8")
    payload = json.dumps(datos, ensure_ascii=False).replace("</", "<\\/")
    reemplazos = {
        "__TITULO__": esc(f"{m['tema']} · {m['materia']}"),
        "__DATOS__": payload,
        "__PDF__": esc(nombre_pdf),
        "__CLAVE__": esc(slugify(m["materia"]) + "/" + slugify(m["fecha"] + "-" + m["tema"])),
    }
    for k, v in reemplazos.items():
        plantilla = plantilla.replace(k, v)
    return plantilla


# ---------------------------------------------------------------------------
# HTML imprimible
# ---------------------------------------------------------------------------

def html_imprimible(m, d):
    css = (ASSETS / "imprimible.css").read_text(encoding="utf-8")
    p = []
    a = p.append

    a('<header class="portada">')
    a(f'<div class="materia">{esc(m["materia"])}</div>')
    a(f'<h1>{esc(m["tema"])}</h1>')
    meta = [fecha_larga(m["fecha"])]
    if m.get("profesor"):
        meta.append(esc(m["profesor"]))
    a(f'<div class="meta">{" · ".join(meta)}</div>')
    if d["archivos"]:
        a(f'<div class="archivos">Material: {esc(", ".join(d["archivos"]))}</div>')
    a("</header>")

    a('<section class="resumen"><h2>Resumen</h2>' + d["resumen"] + "</section>")

    # Índice
    a('<nav class="indice"><h2>Contenido</h2><ol>')
    for s in d["secciones"]:
        marca = ' <span class="badge">Parcial</span>' if s["importante"] else ""
        a(f"<li>{s['titulo']}{marca}</li>")
    a("</ol></nav>")

    # Secciones
    for n, s in enumerate(d["secciones"], 1):
        cls = "seccion importante" if s["importante"] else "seccion"
        a(f'<section class="{cls}">')
        ref = f'<span class="ref">{s["referencia"]}</span>' if s["referencia"] else ""
        badge = '<span class="badge">Entra en el parcial</span>' if s["importante"] else ""
        a(f'<h2><span class="num">{n}.</span> {s["titulo"]} {badge}</h2>{ref}')
        a(s["contenido"])
        if s["profe"]:
            a('<aside class="profe"><div class="profe-titulo">Lo que dijo el profe</div><ul>')
            a("".join(f"<li>{x}</li>" for x in s["profe"]))
            a("</ul></aside>")
        a("</section>")

    if d["no_visto"]:
        a('<section class="caja"><h2>No se vio en clase</h2><ul>')
        a("".join(f"<li>{x}</li>" for x in d["no_visto"]))
        a("</ul></section>")

    if d["frases_profe"]:
        a('<section class="frases"><h2>Frases del profe</h2>')
        for f in d["frases_profe"]:
            ctx = f'<span class="ctx">{f["contexto"]}</span>' if f["contexto"] else ""
            a(f'<blockquote class="frase t-{f["tipo"]}"><span class="tipo">{f["etiqueta"]}</span>'
              f'<p>“{f["texto"]}”</p>{ctx}</blockquote>')
        a("</section>")

    if d["glosario"]:
        a('<section class="glosario"><h2>Glosario</h2><dl>')
        for g in d["glosario"]:
            a(f'<div class="termino"><dt>{g["termino"]}</dt><dd>{g["definicion"]}</dd></div>')
        a("</dl></section>")

    if d["dudas"]:
        a('<section class="dudas"><h2>Dudas de la clase, resueltas</h2>')
        for x in d["dudas"]:
            a(f'<div class="duda"><h3>{x["pregunta"]}</h3>{x["respuesta"]}</div>')
        a("</section>")

    if d["flashcards"]:
        a('<section class="preguntas"><h2>Preguntas de repaso</h2>'
          '<p class="nota">Tapá la respuesta e intentá contestar de memoria.</p><ol>')
        for f in d["flashcards"]:
            a(f'<li><div class="q">{f["pregunta"]}</div><div class="a">{f["respuesta"]}</div></li>')
        a("</ol></section>")

    if d["quiz"]:
        a('<section class="quiz"><h2>Autoevaluación</h2>'
          '<p class="nota">Las respuestas están al final.</p><ol>')
        for q in d["quiz"]:
            ops = "".join(f'<li>{o}</li>' for o in q["opciones"])
            a(f'<li class="pregunta">{q["pregunta"]}<ol type="a" class="opciones">{ops}</ol></li>')
        a("</ol></section>")

    if d["para_repasar"]:
        a('<section class="caja repasar"><h2>Para repasar</h2><ul class="check">')
        a("".join(f"<li>{x}</li>" for x in d["para_repasar"]))
        a("</ul></section>")

    if d["quiz"]:
        a('<section class="clave"><h2>Respuestas de la autoevaluación</h2><ol>')
        for q in d["quiz"]:
            letra = "abcdefghij"[q["correcta"]]
            a(f'<li><strong>{letra})</strong> {q["opciones"][q["correcta"]]}<div class="expl">{q["explicacion"]}</div></li>')
        a("</ol></section>")

    titulo = esc(f"{m['tema']} · {m['materia']}")
    pie = esc(f"{m['materia']} — {m['tema']}")
    katex = (
        '<link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/katex@0.16.11/dist/katex.min.css">'
        '<script defer src="https://cdn.jsdelivr.net/npm/katex@0.16.11/dist/katex.min.js"></script>'
        '<script defer src="https://cdn.jsdelivr.net/npm/katex@0.16.11/dist/contrib/auto-render.min.js"'
        ' onload="renderMathInElement(document.body,{delimiters:[{left:\'$$\',right:\'$$\',display:true},'
        '{left:\'$\',right:\'$\',display:false}],throwOnError:false})"></script>'
    )
    return (
        f'<!doctype html><html lang="es"><head><meta charset="utf-8"><title>{titulo}</title>'
        f'<meta name="viewport" content="width=device-width,initial-scale=1">{katex}'
        f'<style>{css}\n@page {{ @bottom-left {{ content: "{pie}"; }} }}</style></head>'
        f'<body>{"".join(p)}</body></html>'
    )


# ---------------------------------------------------------------------------
# PDF
# ---------------------------------------------------------------------------

def buscar_navegador():
    candidatos = [
        "chromium", "chromium-browser", "google-chrome", "google-chrome-stable",
        "microsoft-edge", "microsoft-edge-stable", "brave-browser", "chrome",
    ]
    for c in candidatos:
        ruta = shutil.which(c)
        if ruta:
            return ruta
    rutas = [
        "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
        "/Applications/Chromium.app/Contents/MacOS/Chromium",
        "/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge",
        "/snap/bin/chromium",
        r"C:\Program Files\Google\Chrome\Application\chrome.exe",
        r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
        r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
    ]
    return next((r for r in rutas if os.path.exists(r)), None)


def generar_pdf(html_path, pdf_path):
    nav = buscar_navegador()
    if not nav:
        return False, "No encontré Chromium/Chrome/Edge."
    if pdf_path.exists():
        pdf_path.unlink()
    cmd = [
        nav, "--headless", "--disable-gpu", "--no-sandbox", "--hide-scrollbars",
        "--no-pdf-header-footer", "--print-to-pdf-no-header",
        "--virtual-time-budget=15000", "--run-all-compositor-stages-before-draw",
        f"--print-to-pdf={pdf_path}", html_path.resolve().as_uri(),
    ]
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
    except subprocess.TimeoutExpired:
        return False, "El navegador tardó demasiado en generar el PDF."
    if pdf_path.exists() and pdf_path.stat().st_size > 0:
        return True, nav
    return False, (r.stderr or r.stdout or "sin salida").strip()[-800:]


# ---------------------------------------------------------------------------

def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("material", type=Path)
    ap.add_argument("--out-dir", type=Path)
    ap.add_argument("--sin-pdf", action="store_true")
    args = ap.parse_args()

    try:
        m = json.loads(args.material.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        sys.exit(f"ERROR: material.json no es JSON válido: {e}")

    errores, avisos = validar(m)
    for av in avisos:
        print(f"AVISO: {av}")
    if errores:
        print("\n".join(f"ERROR: {e}" for e in errores))
        sys.exit(1)

    out = (args.out_dir or args.material.parent).resolve()
    out.mkdir(parents=True, exist_ok=True)
    base = slugify(f"{m['fecha']}-{m['tema']}")
    p_html = out / f"{base}.html"
    p_print = out / f"{base}-imprimible.html"
    p_pdf = out / f"{base}.pdf"

    datos = renderizar(m)
    p_html.write_text(html_interactivo(m, datos, p_pdf.name), encoding="utf-8")
    p_print.write_text(html_imprimible(m, datos), encoding="utf-8")
    print(f"HTML interactivo: {p_html}")
    print(f"HTML imprimible:  {p_print}")

    if args.sin_pdf:
        return
    ok, info = generar_pdf(p_print, p_pdf)
    if ok:
        print(f"PDF:              {p_pdf}")
    else:
        print(f"AVISO: no se pudo generar el PDF ({info}).")
        print(f"       Abrí {p_print.name} en el navegador y usá Ctrl+P → Guardar como PDF.")


if __name__ == "__main__":
    main()
