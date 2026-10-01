# Claude Skills

Skills para [Claude Code](https://claude.com/claude-code) que voy creando. Cada skill vive en su carpeta dentro de `skills/`.

## Skills disponibles

| Skill | Para qué sirve |
|---|---|
| [`clase-facultad`](skills/clase-facultad/) | Asistente en vivo para clases de la facu: le pasás los archivos de la clase, le vas contando lo que explica el profe, registra todo y al final genera un **HTML interactivo** (resumen, flashcards, autoevaluación, glosario, frases del profe) y un **PDF para imprimir**. |
| [`landing-page`](skills/landing-page/) | Genera landing pages para clientes nuevos: pide marca, rubro y tono, **recomienda el stack** según el cliente, define la dirección visual con la skill `frontend-design`, escribe el copy, construye la landing (responsive, SEO, accesibilidad), la verifica con capturas y ofrece deploy. |

## Cómo instalarlas

Necesitás [Node.js](https://nodejs.org) (para `npx`) y Claude Code.

**Una skill puntual, disponible en todas tus carpetas:**

```bash
npx skills add https://github.com/Valentino-git2305/claude-skills --skill clase-facultad --agent claude-code -g
```

Para otra skill, cambiá el nombre después de `--skill` (ej. `--skill landing-page`).

**Solo para la carpeta (proyecto) en la que estás:** el mismo comando sin `-g`.

**Todas las skills del repo:** cambiá `--skill clase-facultad` por `--skill '*'`.

**Para actualizar** cuando haya cambios:

```bash
npx skills update
```

Después de instalar, abrí una sesión nueva de Claude Code para que la skill aparezca.

## clase-facultad

### Requisitos
- Python 3 (sin librerías extra).
- Chromium, Google Chrome, Edge o Brave instalado para generar el PDF. Si no hay ninguno, la skill igual genera una versión imprimible en HTML que podés guardar como PDF con Ctrl+P.
- Conexión a internet al abrir el material, para que las fórmulas matemáticas se vean bien (sin conexión se ven en LaTeX).

### Cómo se usa
1. **Arrancá la clase** diciéndole la materia y el tema, y pasale los archivos: *"arranca la clase de Análisis II, hoy vemos gradiente"*. Si falta la materia o el tema, te lo pregunta antes de empezar.
2. **Durante la clase**, escribile lo que va diciendo el profe (aunque sea abreviado). Lo guarda al instante en `registro.md` y te contesta en 2-4 líneas. Si el profe dice que algo entra en el parcial, queda marcado.
3. **Al terminar**, decile *"terminó la clase"* y genera el HTML y el PDF.

Todo queda en `~/Facultad/<Materia>/<fecha>-<tema>/`.

## landing-page

### Requisitos
- Node.js (para `npx`): la skill instala sola la skill `frontend-design` si no la tenés, y usa Playwright para sacar capturas de verificación (la primera vez descarga su navegador).
- Python 3 para levantar un servidor local en las landings de HTML simple.
- Para el deploy, la CLI y la cuenta de la plataforma elegida (la skill te dice qué paso hacer si falta algo).

### Cómo se usa
1. Pedile *"crear una landing para un cliente nuevo"* o usá `/landing-page`. Te va a pedir **nombre/marca, rubro y tono** (obligatorios) y datos opcionales (colores, WhatsApp, redes, analytics…). Todo queda guardado en `brief.md` en la carpeta del proyecto.
2. Te hace unas preguntas sobre el cliente y te **recomienda 2-3 stacks** con pros, contras y costos. Elegís uno.
3. Te propone **2-3 direcciones visuales**. Elegís una.
4. Escribe el copy, arma la landing, corre un checklist de entrega y la revisa con capturas en mobile y desktop.
5. Te ofrece publicarla (nunca la publica sin que confirmes).

Cuando un cliente aprueba una landing, decile *"esta quedó aprobada"* y la registra en `aprobadas.md` para usarla como referencia con clientes parecidos.

> **Ojo al actualizar:** `aprobadas.md` vive dentro de la carpeta de la skill. Si actualizás con `npx skills update`, se reemplaza por la versión del repo y perdés tus entradas. Hacé una copia antes de actualizar.

## Agregar una skill nueva

Creá una carpeta `skills/<nombre-de-la-skill>/` con su `SKILL.md` y sumala a la tabla de arriba.

## Licencia

[MIT](LICENSE)
