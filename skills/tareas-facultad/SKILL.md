---
name: tareas-facultad
description: Barre todas las plataformas donde las cátedras publican (aula virtual Moodle/Canvas, Google Classroom, Slack, Discord, WhatsApp, repositorios de Git, mail institucional), consolida las tareas pendientes en una planilla Excel o Google Sheets con fechas, estado y de qué fuente salió cada dato, y arma prompts con todo el contexto para encarar una entrega puntual. Usar cuando el usuario pide revisar la cátedra o el aula virtual, preguntar si tiene algo pendiente, actualizar su planilla de tareas, ver qué entregas se vienen, buscar la consigna de un TP, o pedir un prompt para empezar un trabajo práctico, parcial o proyecto de una materia.
---

# Seguimiento de la cursada

La consigna de fondo: **las materias no publican todas en el mismo lugar**. Una usa el aula virtual, otra un canal de Slack, otra un repo de Git, otra el grupo de WhatsApp y nada más. Un pendiente que vive solo en un grupo de chat es igual de real que uno cargado en la plataforma, y es el que se pasa de largo. Esta skill junta todo en un solo lado.

Tres modos. Identificá cuál corresponde antes de arrancar:

- **Configuración inicial** — primera vez, o cuando cambia el cuatrimestre.
- **Relevamiento** — "revisá todo", "actualizá la planilla", "¿tengo algo pendiente?".
- **Prompt de entrega** — "dame un prompt para hacer X", "quiero arrancar el TP de Y".

Respondé en el idioma del usuario, directo y sin relleno.

---

## Configuración inicial

No arranques a barrer a ciegas. Averiguá primero, con `AskUserQuestion` donde haya opciones acotadas:

1. **Qué materias cursa este período.** Si el aula virtual lista muchas más (matriculaciones viejas, materias ya regulares), mostrale las que tienen actividad reciente y que confirme cuáles son de verdad. Anotá también las que ya tiene regulares: de esas se ignoran las consignas pero **sí** interesan las mesas de final.
2. **Dónde publica cada materia.** Una por una. Las respuestas típicas: aula virtual (Moodle, Canvas, Blackboard), Google Classroom, Slack, Discord, Teams, grupo de WhatsApp o Telegram, repositorio de Git, mail.
3. **Qué casilla de mail usan los profesores.** Suele ser la institucional y no la personal, y suele no estar conectada como conector — en ese caso se lee por navegador.
4. **Excepciones por materia.** Lo que distorsiona el estado real: entregas grupales que sube un solo integrante (en la cuenta del resto figuran como no entregadas), materias donde la plataforma es solo depósito y la aprobación pasa antes con el docente, cátedras que dejaron tareas viejas abiertas de ciclos anteriores.

**Guardá todo esto en memoria** (un archivo por materia, o uno de la cursada). En las corridas siguientes se lee de ahí y no se vuelve a preguntar. Cuando algo cambie, actualizalo.

---

## Relevamiento

Creá una task list: una tarea por fuente, más una de consolidación. Después recordé de dónde salió cada dato — va en la planilla.

### Aulas virtuales Moodle

Es la plataforma más común y se puede leer por fetch, mucho más rápido que navegar curso por curso. Entrá con el navegador (sesión ya iniciada) y **verificá la sesión antes de nada**:

```js
document.title + ' | ' + (typeof M !== 'undefined' && M.cfg.sesskey ? 'OK' : 'NOLOGIN')
```

Si redirige al login, **la sesión expiró**. Nunca ingreses contraseñas: decíselo al usuario en una línea, seguí con las otras fuentes, y marcá en la planilla que esos datos son de la corrida anterior.

Cursos matriculados:

```js
const r = await fetch(M.cfg.wwwroot+'/lib/ajax/service.php?sesskey='+M.cfg.sesskey+'&info=core_course_get_enrolled_courses_by_timeline_classification',
  {method:'POST', headers:{'Content-Type':'application/json'},
   body: JSON.stringify([{index:0, methodname:'core_course_get_enrolled_courses_by_timeline_classification',
                          args:{offset:0, limit:0, classification:'all', sort:'fullname'}}])});
(await r.json())[0].data.courses.map(c => c.id + ' | ' + c.fullname)
```

Tareas de un curso (`tds[1]` tarea, `tds[2]` fecha, `tds[3]` estado):

```js
const grab = async (id) => {
  const html = await (await fetch(M.cfg.wwwroot+'/mod/assign/index.php?id='+id, {credentials:'include'})).text();
  const doc = new DOMParser().parseFromString(html,'text/html');
  return Array.from(doc.querySelectorAll('table.generaltable tbody tr')).map(tr => {
    const tds = Array.from(tr.querySelectorAll('td')).map(td => td.textContent.trim().replace(/\s+/g,' '));
    return tds.length > 3 ? [tds[1], tds[2], tds[3]].join(' || ') : '';
  }).filter(x => x.length > 3).join("\n");
};
```

**Cruzá siempre contra el calendario**, que trae cosas que el listado de tareas no muestra:

```js
// core_calendar_get_calendar_monthly_view con {year, month, courseid:1, categoryid:0, mini:false, day:1}
// recorré d.weeks[].days[].events[] y filtrá eventtype !== 'attendance'
```

Mirá además `/mod/quiz/index.php?id=<curso>` (parciales y cuestionarios) y, si una materia no tiene tareas, `/course/view.php?id=<curso>` para ver qué actividades hay. El libro de calificaciones (`/grade/report/user/index.php?id=<curso>`) sirve para confirmar si algo quedó registrado.

**Gotchas de Moodle:**
- Si el resultado del JS contiene URLs con query string, la herramienta devuelve `[BLOCKED: Cookie/query string data]`. Devolvé texto y nombres, no hrefs.
- Para leer un PDF adjunto: sacá `forcedownload=1` del href y navegá con `window.location.assign(u)`, después leelo con screenshots. El fetch directo al adjunto está bloqueado.
- La vista "Mis cursos" carga por JS y suele venir vacía al leerla — usá la API de arriba.

### Repositorios de Git

Varias cátedras técnicas publican consignas en un repo y **no avisan por el canal de la materia**. Si alguna usa repo, revisalo en cada corrida, no solo el chat:

```js
await (await fetch('https://api.github.com/repos/<org>/<repo>/contents/<carpeta-de-tps>')).json()
// y los commits recientes para ver qué se liberó últimamente
```

Las consignas en markdown se leen crudas desde `raw.githubusercontent.com/<org>/<repo>/main/<ruta>`.

### Slack / Discord / Teams

Si hay conector, usalo (`slack_read_channel` y equivalentes). Si no, por navegador. Ojo con asumir que el canal tiene todo: compará la fecha del último mensaje contra la actividad del repo o la plataforma — un canal quieto no significa que no haya novedades.

### WhatsApp / Telegram

Por navegador (`web.whatsapp.com`, sesión persistente). **Acá es donde aparecen las fechas que no están en ningún otro lado**: parciales presenciales, cambios de clase, repartos de trabajo grupal. No lo saltees.

Leer el chat abierto:

```js
const main = document.querySelector('#main');
Array.from(main.querySelectorAll('div[role="row"]'))
  .map(r => r.innerText.replace(/\s*\n\s*/g,' ⏎ ').slice(0,400)).slice(-30).join('\n')
```

**Gotchas de WhatsApp Web:**
- El buscador a veces pierde lo tipeado: tomá un screenshot para confirmar que el texto entró antes de leer resultados.
- Para encontrar archivos, buscá por extensión (`pdf`, `docx`, `pkt`, `zip`) o por palabra del nombre.
- Los mensajes largos vienen cortados: click en "Read more" antes de extraerlos.
- Los audios no se pueden escuchar. Si hay info importante en uno, decílo en vez de adivinar.

### Mail institucional

Si el conector de mail apunta a la casilla personal y los profesores escriben a la institucional, se lee por navegador. En Gmail multi-cuenta: `https://mail.google.com/mail/u/<n>/#search/<query>`, confirmando en el `<title>` que es la cuenta correcta.

**Gmail no re-renderiza al cambiar el hash**: después de navegar a una búsqueda hacé `location.reload()` y esperá unos segundos. Filas: `tr.zA` (remitente `.yW`, asunto `.y6`, snippet `.y2`, fecha `.xW`).

---

## La planilla

Por defecto Excel con openpyxl, recalculado con el `recalc.py` de la skill `xlsx`. Si el usuario prefiere Google Sheets, misma estructura vía el conector de Google Workspace. Nombre con fecha, en `/mnt/user-data/outputs/`.

**Hojas:**

1. **Resumen** — tarjetas de KPI (pendientes / vencidos / próximos 15 días / entregados) como fórmulas que apuntan a las otras hojas; tabla "Lo que viene" ordenada por fecha con prioridad; una alerta si hay fechas amontonadas; y un bloque **"Cambios desde <fecha de la corrida anterior>"**, que es lo primero que el usuario lee.
2. **Pendientes** — materia, tarea, tipo, fecha límite, días, estado, situación, **fuente**, link. La columna Días es fórmula contra una celda de fecha de referencia (`=D<fila>-$<celda>`), así el usuario cambia esa celda y se recalcula todo. Autofiltro y paneles fijos.
3. **Ya entregado**
4. **Ciclos anteriores** — entregas viejas que la cátedra dejó abiertas, fuera de la lista principal para que no inflen el conteo.
5. **Notas por materia** — el detalle de cada aviso: quién lo dijo, cuándo y dónde. Acá van también las materias sin entregas online y las excepciones.
6. **Una hoja por excepción** — por ejemplo, la materia de entrega grupal: dos columnas, "cómo figura en tu cuenta" vs. "situación real".

**La columna Fuente es lo que hace útil la planilla**: chip de color por origen (aula virtual, chat, repo, mail). Dice de dónde salió cada dato y cuál puede estar desactualizado.

Estilo: tipografía sobria, sin gridlines, cabeceras oscuras, filas alternadas, chips de color por estado (rojo vencido, verde a tiempo, gris sin fecha), formato condicional en Días (ámbar cuando faltan ≤10, rojo si es negativo).

Tareas sin fecha: `None` en los datos, "Sin fecha" en la celda, "—" en días. No deben romper las fórmulas ni el ordenamiento.

Las corridas siguientes parten del script de la anterior: se actualizan los datos y el bloque de cambios, no se rehace el diseño.

---

## Prompt de entrega

1. **Buscá la consigna real.** No armes el prompt de memoria ni del título de la tarea. Andá a la fuente y leé el enunciado completo, **incluidos los adjuntos** — abrilos y leelos de verdad.
2. **Fijate qué ya existe.** Puede haber un avance circulando en el grupo, un archivo que ya subió, una devolución previa o un reparto de tareas entre compañeros. Eso cambia por completo el prompt.
3. **Armá el prompt en un bloque de código**, listo para copiar, con:
   - quién es, qué carrera y qué materia
   - la consigna desglosada en ítems, y **las reglas que cambian el juego**: si hay que hacer aprobar antes de subir, si la evaluación es individual aunque el trabajo sea grupal, si hay defensa oral, si entra en la nota de regularidad
   - qué material adjuntar o dónde está
   - el contexto de la cátedra: temas vistos, herramienta que se usa, criterios de evaluación si están publicados
   - cómo quiere trabajar: por partes, entendiendo cada paso, sin entregable para copiar
4. **Si el prompt es para otra sesión con acceso a herramientas**, incluí las URLs exactas y cómo navegar para que pueda buscar la consigna sola.
5. Cerrá con **lo que no entra en el prompt pero le muerde**: fechas que dependen de terceros, coordinaciones pendientes, presentaciones posteriores a la entrega.

**No resuelvas la entrega en el prompt.** El objetivo es que el estudiante entienda y pueda defender lo que presenta; pedí explícitamente explicación paso a paso y preguntas de control.

---

## Al cerrar

- Mandá la planilla con `SendUserFile`.
- En el chat: tabla corta de lo que viene, las novedades desde la última corrida, y al final el riesgo real (fechas amontonadas, algo que depende de un tercero, una entrega que exige un paso previo). Nada de recapitular hoja por hoja.
- Si alguna fuente no se pudo revisar, decilo explícitamente — un relevamiento incompleto presentado como completo es peor que no hacerlo.
- Guardá en memoria lo durable: fechas nuevas, cambios de modalidad, dónde publica cada cátedra.
- Cerrá las pestañas que abriste.
