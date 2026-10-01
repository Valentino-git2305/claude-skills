# Esquema de `material.json`

Es lo único que tenés que escribir al cerrar la clase: el script `generar_material.py` arma el HTML interactivo y el PDF a partir de esto. Todos los textos largos aceptan **Markdown** (ver abajo qué subconjunto).

## Campos

| Campo | Tipo | Obligatorio | Qué va |
|---|---|---|---|
| `materia` | string | sí | Nombre legible: "Análisis Matemático II" |
| `tema` | string | sí | Tema de la clase: "Derivadas direccionales y gradiente" |
| `fecha` | string | sí | `AAAA-MM-DD` |
| `profesor` | string | no | Si se mencionó |
| `archivos` | string[] | no | Nombres de los archivos de la clase |
| `resumen` | markdown | sí | 3-5 oraciones: qué se vio y la idea central |
| `secciones` | objeto[] | sí | Ver abajo. En el orden en que se dieron |
| `frases_profe` | objeto[] | no | Ver abajo |
| `glosario` | objeto[] | sí | `{ "termino", "definicion" }` |
| `flashcards` | objeto[] | sí | `{ "pregunta", "respuesta" }`, 8-20 |
| `quiz` | objeto[] | sí | Ver abajo, 6-12 |
| `dudas` | objeto[] | no | `{ "pregunta", "respuesta" }` — la respuesta desarrollada |
| `para_repasar` | string[] | no | Pendientes concretos de estudio |
| `no_visto` | string[] | no | Temas del material que el profe salteó |

### `secciones[]`

```json
{
  "titulo": "Derivada direccional",
  "contenido": "Markdown con la explicación completa...",
  "profe": ["Lo que dijo el profe sobre este tema, una idea por elemento"],
  "importante": true,
  "referencia": "Diapos 10-14"
}
```

- `contenido`: el corazón del material. Explicá como un buen apunte: definición, intuición, fórmula, ejemplo resuelto, errores comunes. Integrá lo que dijo el profe y tus aclaraciones del registro. Si el profe hizo un ejercicio en el pizarrón, incluí los pasos.
- `profe`: lo dicho por el profe, fiel (puede ser textual o parafraseado de cerca). Se muestra destacado aparte del contenido para distinguir "lo que dijo el profe" de "la explicación".
- `importante`: `true` si el profe lo marcó como tema de parcial o hizo hincapié. Se ve con un badge.
- `referencia`: opcional, ubicación en el material.

### `frases_profe[]`

```json
{ "texto": "Si en el parcial no normalizan el vector, está mal todo el ejercicio", "tipo": "parcial", "contexto": "Derivada direccional" }
```

`tipo` ∈ `parcial` · `advertencia` · `consejo` · `ejemplo` · `no_se_toma`. Son las frases que el usuario querría releer la noche antes del examen.

### `quiz[]`

```json
{
  "pregunta": "¿En qué dirección es máxima la derivada direccional de $f$ en $P$?",
  "opciones": ["En la dirección de $\\nabla f(P)$", "Perpendicular a $\\nabla f(P)$", "En la dirección de $-\\nabla f(P)$", "En la dirección del eje $x$"],
  "correcta": 0,
  "explicacion": "$D_u f = \\nabla f \\cdot u = |\\nabla f|\\cos\\theta$, máximo cuando $\\theta = 0$."
}
```

- `correcta` es el **índice** (desde 0) de la opción correcta. Variá la posición de la correcta entre preguntas.
- Distractores plausibles: errores que un estudiante realmente cometería.
- La explicación dice por qué la correcta es correcta (y, si sirve, por qué la trampa más tentadora no).

## Markdown soportado

- Párrafos separados por línea en blanco
- `**negrita**`, `*itálica*`, `` `código` ``, `[link](url)`
- Listas con `- ` o `1. ` (un nivel; para subniveles indentá con 2 espacios)
- `### Subtítulo` dentro de una sección
- `> cita` (útil para definiciones formales)
- Bloques de código con ``` (con lenguaje opcional)
- Tablas con `|` y fila separadora `|---|---|`
- Matemática: `$inline$` y `$$bloque$$` (LaTeX, se renderiza con KaTeX). En JSON, las barras invertidas van dobles: `"$\\frac{a}{b}$"`

## Ejemplo mínimo completo

```json
{
  "materia": "Análisis Matemático II",
  "tema": "Derivadas direccionales y gradiente",
  "fecha": "2026-09-30",
  "profesor": "Ing. Gómez",
  "archivos": ["AM2-clase08.pdf"],
  "resumen": "Se definió la derivada direccional como límite y se mostró que, si $f$ es diferenciable, se calcula como $\\nabla f \\cdot \\hat u$. El gradiente apunta en la dirección de máximo crecimiento.",
  "secciones": [
    {
      "titulo": "Derivada direccional",
      "contenido": "> **Definición.** $D_{\\hat u} f(P) = \\lim_{h\\to0} \\frac{f(P+h\\hat u)-f(P)}{h}$\n\nSi $f$ es diferenciable en $P$:\n\n$$D_{\\hat u} f(P) = \\nabla f(P) \\cdot \\hat u$$\n\n**Ojo:** $\\hat u$ tiene que ser unitario.",
      "profe": ["\"Si no normalizan el vector está mal todo el ejercicio\""],
      "importante": true,
      "referencia": "Diapos 10-14"
    }
  ],
  "frases_profe": [
    { "texto": "Si no normalizan el vector está mal todo el ejercicio", "tipo": "parcial", "contexto": "Derivada direccional" }
  ],
  "glosario": [
    { "termino": "Gradiente", "definicion": "Vector de derivadas parciales $\\nabla f = (f_x, f_y)$." }
  ],
  "flashcards": [
    { "pregunta": "¿Cómo se calcula $D_{\\hat u} f$ si $f$ es diferenciable?", "respuesta": "$\\nabla f \\cdot \\hat u$, con $\\hat u$ unitario." }
  ],
  "quiz": [
    {
      "pregunta": "¿En qué dirección es máxima la derivada direccional?",
      "opciones": ["$-\\nabla f$", "$\\nabla f$", "Perpendicular a $\\nabla f$", "Eje $x$"],
      "correcta": 1,
      "explicacion": "$D_u f = |\\nabla f|\\cos\\theta$, máxima con $\\theta=0$."
    }
  ],
  "dudas": [
    { "pregunta": "¿Por qué el versor tiene que ser unitario?", "respuesta": "Porque si $|v| \\neq 1$, $\\nabla f \\cdot v = |v| D_{\\hat v} f$: el resultado queda escalado..." }
  ],
  "para_repasar": ["Ejercicios 3 a 7 de la guía 4"],
  "no_visto": ["Diapo 20: plano tangente (queda para la próxima)"]
}
```
