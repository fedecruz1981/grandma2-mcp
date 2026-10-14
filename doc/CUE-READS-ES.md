---
title: Lectura de cues en el MCP — por qué cambié el código y qué comprobé
description: Referencia en español del refactor de lecturas de cues a resultados tipados
version: 2.0.0
created: 2026-10-13T00:00:00Z
last_updated: 2026-10-14T00:00:00Z
---

# Lectura de cues en el MCP — por qué cambié el código y qué comprobé

Documento de referencia en español. El código y los comentarios quedan en inglés
porque el repo es Apache-2.0, lo mantiene `drohi-r` y ya tiene tres personas
contribuyendo; un fork con comentarios en español se vuelve inabordable de
integrar. Este archivo es para vos.

Rama: `refactor/cue-reads` · 6 commits sobre `origin/main`

> **Versión 2.** La v1 documentaba el refactor tipado. Esta agrega lo que se
> descubrió después, con la consola en vivo, queresultó más grave que el
> refactor mismo. Está al final, en §10 y §11.

---

## 1. El problema de fondo

Una lectura por telnet tiene **tres** resultados, y un `str` pelado no los
distingue:

1. la consola contestó con datos
2. la consola no tenía ese objeto (`WARNING, NO OBJECTS FOUND FOR LIST`)
3. la respuesta llegó cortada, tarde, o nunca

El segundo es el peligroso. `NO OBJECTS FOUND` es una respuesta **perfectamente
bien formada**. Entonces el código que lee "no encontré nada" como "está vacío"
termina informando un resultado limpio sobre datos que nunca recibió.

---

## 2. Qué hace `src/cue_reads.py`

Un módulo nuevo, sin imports de `src.server`, que las herramientas pueden usar
sin cerrar un ciclo de imports.

### `ObjectRead` — el resultado tipado

```python
read = await read_cue(client, 156, 3)

read.found      # la consola tenía ese cue
read.rejected   # la consola lo rechazó (Error #N)
read.usable     # hubo una lectura real detrás
read.lines      # solo líneas de dato, sin el chrome de la consola
read.raw        # la respuesta cruda, sin filtrar
```

`found` y `usable` están separados a propósito. Una respuesta vacía se clasifica
como `found=False`: que no haya llegado nada **no es** lo mismo que la consola
confirme un objeto vacío.

### `cue_number()` — los números como los escribe la consola

```python
cue_number(3)     -> "3"      # int
cue_number(3.0)   -> "3"      # float entero, sin el ".0"
cue_number(1.1)   -> "1.1"    # sub-cue conserva el decimal
cue_number("1.1") -> "1.1"   # str tal cual
```

**Ojo: esto normaliza, no arregla un bug.** La consola acepta `3.0` y lo trata
como `3` — medido byte a byte en vivo. Es defensa ante firmas tipadas `float`,
no un workaround. Ver §10.

### `strip_chrome()` — el eco no es dato

Saca el eco del comando, el rechazo, los errores y el prompt.

### `object_ids_in()` — el parser que sí matchea

```python
object_ids_in(reply, limit)  # prefijos "Sequ", "Macro", "Cue", "Fixture"
cue_ids_in(reply, limit)     # mismo parser, nombrado por el pool de cues
```

Las filas reales de un listado llevan el tipo adelante:

```
Sequ   1 1    DIMER BEAM
Macro 1 1    Stomp Position
Cue 1 1       *    Go
Fixture 1 1   Mac700 Profile
```

El patrón anterior (`^\s*(\d+)\s`) matcheaba **cero filas reales**. Ver §11.

---

## 3. Un bug mío que encontré escribiendo los tests

El prompt de la consola **no es** `"[Fixture]>"`. Es `"[Fixture]>\x1b[K"`: lleva
un código ANSI de limpieza después del `>`. Mi regex de prompt no lo
contemplaba, así que **no quitaba el prompt** y dejaban pasar todas las líneas.

Si no hubiera escrito tests con respuestas que incluyen el `\x1b[K`, el bug
habría pasado inadvertido.

Los otros dos que aparecieron al probar:

- una respuesta vacía se clasificaba `found=True`
- `read_object` cortaba antes de enviar cuando `object_id` era `None`, lo que
  saltaba silenciosamente el listado de cues de una secuencia

---

## 4. Las herramientas migradas

| herramienta | qué cambió |
|---|---|
| `diff_cues` | usa `read_cue`; si un cue no está, `comparable: false` |
| `detect_tracking_leaks` | usa `list_cues`/`read_cue`; no compara pares con un lado ilegible |
| `compare_cue_values` | idem, y el diff es sobre `lines` (sin chrome) |
| `trace_attribute_lineage` | saltea cues ilegibles y lo dice en `summary` |
| `check_object_exists` | reporta `rejected` y el `Error #N` |
| `auto_number_cues` | **DESTRUCTIVA**, ver abajo |
| `find_preset_usages` | usa `list_cues` |
| `validate_preset_references` | usa `list_cues` + `strip_chrome` |

---

## 5. `auto_number_cues` — el destructivo

Es **DESTRUCTIVA**: mueve cues en un show vivo. Tenía dos problemas.

**El float.** Parseaba los ids como `float` y armaba los comandos `move cue`:

```
move cue 3.0 sequence 1 at cue 4 sequence 1
```

**El orden.** Con ids como `str`, `sorted(["1","2","10","9"])` da `1, 10, 2, 9`.
Para una operación destructiva, esa línea es la diferencia entre renumerar y
hacer un desastre. Ahora ordena con `key=float` explícito.

Y un tercer problema que encontró el test: el parseo leía un cue del **eco del
comando que el agente acababa de mandar**.

---

## 6. `find_unused_objects` — propone borrar

Leía el cuerpo de cada macro buscando referencias *entrantes* (`Go Macro N`), y
listaba como "sin usar" todo lo que no tuviera referencia. `NO OBJECTS`, un
`Error #N` y una respuesta vacía producen **exactamente lo mismo** que "nada
apunta a este macro". Estaba proponiendo borrar macros sobre la base de una
lectura fallida.

Ahora un cuerpo ilegible queda en `unreadable_objects` con `complete: false`, y
una nota dice que la lista no habla de ellos.

---

## 7. `plan_fixture_swap` — el veredicto de seguridad

Descubría los atributos de cada tipo de luminaria y solo cortaba si **ambos**
conjuntos venían vacíos:

```python
if not old_attrs and not new_attrs:
```

Con el tipo viejo leído bien y el nuevo **no parcheado**, el conjunto vacío
pasaba de largo y se volvía intersección. El resultado:

```
compatible_attributes  []
missing_in_new         ['Color','Dimmer','Focus','Gobo','Pan','Tilt']
compatibility_percent  0.0
risk_level             'high'
```

Seis atributos reportados como faltantes, riesgo alto, y un plan de migración
pidiendo ajustar seis atributos a mano. **La verdad era que el tipo nuevo no
estaba parcheado.**

Ahora devuelve `(atributos, estado)` con `ok` / `not_found` / `unreadable`, y si
un lado no es `ok` para y dice cuál falló, con `risk_level: null`.

---

## 8. Qué verifiqué y cómo

**Verificación en negativo.** Revertí solo el código y los tests nuevos fallan.

| reverto | fallan |
|---|---|
| `src/mcp_tools/` | 7 |
| solo `diagnostics.py` | 3 |
| solo `analysis.py` (find_unused) | 3 |
| solo `analysis.py` (plan_fixture_swap) | 5 |

**Suite completa**: 3371 pasan, 164 skip, 0 fallas. Era 3235 antes de empezar.

**Ruff**: limpio en todo lo que toqué.

**Import real, no lectura de código.** Al principio importé `ends_with_prompt`
desde `src.telnet_client` en `analysis.py` y rompí un ciclo de imports. Lo
detecté importando, no leyendo. Por eso `cue_reads.py` no importa nada de
`src.server`.

---

## 9. Commits

| commit | qué hace |
|---|---|
| `3f12226` | los 127 scripts de INTI Y LUNA (rama anterior) |
| `6d0c6e5` | avisar cuando el eco no corresponde al comando |
| `411603e` | el float en los números de cue y "sin leaks" sobre cues ilegibles |
| `922b6d1` | `diff_cues`: dos cues inexistentes no son idénticos |
| `e032430` | el módulo `cue_reads.py` |
| `bf72ae6` | migrar 8 herramientas a la lectura tipada |
| `d31ce1a` | no proponer borrar macros que no se pudieron leer |
| `f4321be` | no graduar un swap contra un tipo que no se pudo leer |
| `697418c` | **reparar el `.gitignore`** |
| `11a504b` | que las herramientas digan que no leen contenidos |

---

## 10. La consola en vivo — lo que cambia todo

Con grandMA2 abierta (`inti y luna oct2026`, 3.9.60.82) medí lo que hasta
entonces era inferencia.

### 10.1 El `.0` NO era un bug

Comparé byte a byte el mismo cue escrito de las dos formas:

```
list cue 1    sequence 156  -> 236 chars
list cue 1.0  sequence 156  -> 238 chars
```

Los 2 caracteres de diferencia están **solo en la línea del eco**:

```
Executing : List Cue 1    Sequence 156
Executing : List Cue 1.0  Sequence 156
```

**El cuerpo de datos es idéntico.** La consola normaliza `1.0` → `1`. Y `5` vs
`5.0` dan ambos `NO OBJECTS` correctamente.

`cue_number()` queda como normalización defensiva, no como corrección de un bug.
Lo afirmé al revés y debí medirlo antes.

### 10.2 `list cue` NO devuelve valores de canal

Este es el hallazgo grande. Probé **nueve** formas sobre un cue que sí tiene 749
valores grabados:

| comando | qué devuelve |
|---|---|
| `list cue 1 sequence 156` | la fila de la tabla: trig, modo, loop, tiempos |
| `cd Sequence 156 Cue 1` + `list` | la ficha: nombre, delay, fade, snap |
| `list cue` | la fila de la tabla |
| `list preset` | el pool de presets |
| `list preset 1` | una línea |
| `info` | `WARNING, NO OBJECTS FOUND FOR INFO` |
| `info attribute` | `WARNING, NO OBJECTS FOUND FOR INFO` |
| `pd` | `Error #1: UNKNOWN COMMAND` |
| `list pd` | `Error #14: OBJECT DOES NOT EXIST` |

El `cd` sí funciona, el prompt lo confirma:

```
cd Sequence 156 Cue 1  ->  Sequences/Global /E1 POR VOS 156/Cue 1 >
```

El cue existe y está donde debe. Lo que pasa es que **`list` sobre un cue
devuelve su ficha, no su contenido.**

Donde están los valores:

```xml
<Cue index="1">
  <CueData>
    <Channel fixture_id="1" attribute_name="DIM" />
    <Value>70</Value>
```

**Solo en el export XML.**

### 10.3 Consecuencia sobre las herramientas

`diff_cues` parseaba un formato `Dimmer=100` **que la consola nunca envía**. Leía
una fila de tabla buscando un formato inexistente, obtenía un mapa vacío, y
reportaba `identical: true` entre dos cues que nunca comparó.

`detect_tracking_leaks` buscaba filas de atributo que no existen en un listado, y
decía "No tracking leaks detected".

`trace_attribute_lineage` buscaba nombres de atributo en listings que no los
contienen.

Por eso ahora las cuatro llevan `cue_read_contents: false` y un caveat que dice
qué trae una lectura de cue y dónde están los valores. En
`detect_tracking_leaks` el caveat va **siempre**, incluso cuando el resultado sale
limpio: un informe limpio que no dice qué no vio es justamente el problema.

### 10.4 `list cue abc sequence N` no da error

Un número inválido devuelve la fila del cue 1 en vez de un rechazo. Cualquier
validación que se apoye solo en `NO OBJECTS` deja pasar basura.

---

## 11. El parser nunca matcheó una fila real

Este lo encontré capturando respuestas reales y pasándolas al código del repo.

```
cue_ids_in(respuesta real)              = []
detect_tracking_leaks  ->  cues_checked: 0   ("Need at least 2 cues")
find_unused_objects(sequence) -> 0 candidatos   (el show tiene 165 secuencias)
find_unused_objects(macro)    -> 0 candidatos   (el show tiene 6 macros)
```

**La causa raíz fui yo.** Escribí los tests con respuestas inventadas
(`"1  Cue1"`) que sí matcheaban el patrón, así que nunca detecté que el patrón
estaba mal. Un test que pasa porque el fixture es falso no prueba nada.

La consola antepone el tipo a cada fila:

```
Sequ   1 1    DIMER BEAM
Macro 1 1    Stomp Position
Cue 1 1       *    Go
```

`^\s*(\d+)\s` matchea **0 de 165**. Ahora `object_ids_in()` maneja el prefijo:

```
el parser viejo  ->  list sequence: 0 ids   list macro: 0 ids
el parser nuevo  ->  list sequence: 3 ids   list macro: 3 ids
```

Y las herramientas reales pasaron de 0 a 25 candidatos.

Las capturas reales quedaron como fixtures en `tests/fixtures/ma2_replies.py`,
con el ANSI tal cual llega. Hay 29 tests que las usan.

---

## 12. El `.gitignore` roto — y era mío

Encontré que `.env` no estaba ignorado. Causa: lo había restaurado con

```powershell
git show rama:.gitignore > archivo
```

PowerShell 5.1 escribe la redirección en **UTF-16LE**. Git parsea los archivos de
ignore como UTF-8, así que las reglas llegaban con bytes NUL entre los caracteres
y **ninguna coincidía**.

Las reglas que yo había agregado después con un editor UTF-8 sí funcionaban, lo
que daba un archivo con **encoding mixto** y hacía muy difícil notar el problema.

Lo que dejó de ignorarse:

```
.env   *.log   .pytest_cache   y varias más
```

Y `.env` contiene `GMA_PASSWORD`, `GMA_ADMIN_PASSWORD`,
`GITHUB_MODELS_TOKEN` y cuatro contraseñas de rol. Estaba a un `git add -A` de
terminar en GitHub.

**Verifiqué todo el historial de todas las ramas: nunca se commiteó nada que
debiera estar ignorado.** Reescrito en UTF-8 plano, las 13 reglas vuelven a
responder.

---

## 13. Cómo se usa ahora

```python
read = await read_cue(client, 156, 3)

if not read.found:
    return {"error": f"Cue {cue} not in sequence {seq}"}

if read.rejected:
    return {"error": read.error_text, "code": read.error_code}

for line in read.lines:
    ...   # esto ES dato del cue
```

Y para listados:

```python
ids = object_ids_in(reply, limit)   # maneja "Sequ 1", "Cue 1", "1  A"
```

### La regla que quedó

> **Nunca trates un `str` de una lectura como si fuera el objeto.** Usá el
> `ObjectRead` y decidí explícitamente qué significa un objeto que no está.
>
> **Y antes de parsear algo de un listado, mirá el formato real.** Las capturas
> están en `tests/fixtures/ma2_replies.py`.

---

## 14. Las sondas

En `scripts/`, para repetir cualquier medición de este documento:

| script | qué responde |
|---|---|
| `verificar_hipotesis_cue.py` | ¿`list cue 3.0` falla? ¿qué trae un cue? |
| `sonda_que_devuelve_cue.py` | qué show está abierto, cuántos cues, qué tablas |
| `prueba_decisiva_cue.py` | comparación byte a byte `1` vs `1.0` |
| `buscar_valores_cue.py` | busca un comando que traiga valores de canal |
| `explorar_arbol_cue.py` | recorre el árbol cd y compara contra el XML |
| `sonda_parsers_reales.py` | el formato de cada listado |
| `sonda_parsers_vs_repo.py` | **corre las herramientas del repo contra respuestas reales** |

Todas son **solo lectura**. La última es la que encontró el bug del parser: usa
las funciones reales del repo con las respuestas reales de la consola.

---

## 15. Lo que quedó sin resolver

**No existe comando telnet que lea los valores de un cue** (§10.2). Para eso hay
que parsear el export XML de la secuencia. El costo: exportar una secuencia son
cientos de KB y tarda; para un diff puntual hay que exportar la secuencia entera
y filtrar.

**`plan_fixture_swap` y `auto_number_cues` no se probaron contra la consola.**
La segunda es destructiva. Antes de apuntarla a una obra real, probarla sobre un
show de prueba.