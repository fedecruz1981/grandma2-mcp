---
title: Lectura de cues en el MCP — por qué cambié el código y qué comprobé
description: Referencia en español del refactor de lecturas de cues a resultados tipados
version: 1.0.0
created: 2026-10-13T00:00:00Z
last_updated: 2026-10-13T00:00:00Z
---

# Lectura de cues en el MCP — por qué cambié el código y qué comprobé

Documento de referencia en español. El código y los comentarios quedan en inglés
porque el repo es Apache-2.0, lo mantiene `drohi-r` y ya tiene tres personas
contribuyendo; un fork con comentarios en español se vuelve inabordable de
integrar. Este archivo es para vos.

Rama: `refactor/cue-reads` · base: `fede/inti-y-luna` (4 commits)

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

Y eso ya pasó cuatro veces en el repo, siempre con la misma raíz:

| herramienta | qué reportaba |
|---|---|
| `detect_tracking_leaks` | "No tracking leaks detected" sobre cues que no pudo leer |
| `diff_cues` | `identical: true` entre dos cues que **no existen** |
| `compare_cue_values` | igual que el anterior, y sin el flag de igualdad |
| `trace_attribute_lineage` | "ningún cue menciona este atributo" habiendo saltado cues |

Y además, cuatro herramientas arman el comando con los ids de cue parseados
como `float`. El cue 3 se vuelve `3.0` y el comando queda:

```
list cue 3.0 sequence 156      ← ese cue no existe
```

La respuesta es `NO OBJECTS FOUND`, y volvemos al problema de arriba.

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
cue_number(3)    -> "3"      # int
cue_number(3.0)  -> "3"      # float entero, sin el ".0"
cue_number(1.1)  -> "1.1"    # sub-cue conserva el decimal
cue_number("1.1") -> "1.1"   # str tal cual
```

Acepta los tres tipos porque las firmas del repo usan los tres.

### `strip_chrome()` — el eco no es dato

Saca el eco del comando, el rechazo, los errores y el prompt. Antes, la línea

```
Executing : List cue 3.0 sequence 1
```

se parseaba como fila de dos columnas y guardaba un atributo llamado
`Executing` con valor `": List cue 3.0 sequence 1"`. Con `NO OBJECTS FOUND`
aparecía además un atributo `NO`. Esos atributos se colaban en `changes[]` y en
`attributes_only_in_a` como si fueran datos del cue.

---

## 3. Un bug mío que encontré escribiendo los tests

El prompt de la consola **no es** `"[Fixture]>"`. Es `"[Fixture]>\x1b[K"`: lleva
un código ANSI de limpieza después del `>`. Mi regex de prompt no lo contemplaba,
así que **no quitaba el prompt** y todas las líneas de datos entraban igual.

Lo detecté porque los tests fallaron, pero el detalle importa: si no hubiera
escrito los tests con respuestas que incluyen el `\x1b[K`, el bug habría pasado
inadvertido.

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

## 5. `auto_number_cues` — el que más me preocupaba

Es **DESTRUCTIVA**: mueve cues en un show vivo. Y tenía dos problemas.

**El float.** Parseaba los ids como `float` y armaba los comandos `move cue`:

```
move cue 3.0 sequence 1 at cue 4 sequence 1     ← 3.0 no existe
```

**El orden.** Parseados como `float` y ordenados con `sorted()`, el orden era
numérico y correcto. Pero si alguien lo hubiera "arreglado" pasando a `str`, el
orden se rompe: `sorted(["1","2","10","9"])` da `1, 10, 2, 9`. Para una operación
destructiva, la diferencia entre renumerar y hacer un desastre es una línea.

Ahora: los ids se parsean como los escribe la consola, se ordenan con
`key=float` (numérico explícito), y cada comando pasa por `cue_number`.

Y un tercer problema que encontró el test: el parseo leía el **eco del comando
propio**. `"Executing : List cue sequence 1"` tiene dígitos después de la palabra
clave, así que un parseo flojo leía un cue del comando que el agente acababa de
mandar.

---

## 6. Qué verifiqué y cómo

**Verificación en negativo.** Revertí solo el código de las herramientas y los
tests nuevos fallan; con el arreglo pasan. No son tests que pasan siempre.

| reverto | fallan |
|---|---|
| `src/mcp_tools/` | 7 |
| solo `diagnostics.py` (auto_number_cues) | 3 |

**Suite completa**: 3320 pasan, 164 skip, 0 fallas. Era 3268 antes de empezar el
refactor.

**Ruff**: limpio en todo lo que toqué. Queda un `PropertyMock` sin usar en
`tests/test_analysis_tools.py` que ya venía del repo — lo comprobé contra HEAD y
no lo toqué, para no mezclar un arreglo ajeno en este commit.

**Import real, no lectura de código.** Al principio importé `ends_with_prompt`
desde `src.telnet_client` en `analysis.py` y rompí un ciclo de imports
(`src.server` importa `analysis`). Lo detecté importando, no leyendo. Por eso
`cue_reads.py` no importa nada de `src.server`.

---

## 7. Lo que NO pude verificar

**No hay consola.** El puerto 30000 rechaza conexiones: no hay proceso grandMA2
corriendo en esta máquina.

Así que esto **no está comprobado contra la consola**:

- que `list cue 3.0` falle de esa forma (que la consola conteste
  `NO OBJECTS FOUND` en vez de ignorarlo). Es inferencia, no medición.
- que el orden numérico con `key=float` sea el que la consola espera en un
  `move cue`. **Muy recomendable probar esto con un show de prueba antes de
  usar `auto_number_cues` sobre una obra real**, porque es destructiva.

Lo que sí está demostrado, por test, es que el comando se armaba con decimales, que
dos respuestas `NO OBJECTS FOUND` se reportaban como cues idénticos, y que el
orden por strings rompe el renumerado.

---

## 8. Cómo se usa ahora

```python
read = await read_cue(client, 156, 3)

if not read.found:
    return {"error": f"Cue {cue} not in sequence {seq}"}

if read.rejected:
    return {"error": read.error_text, "code": read.error_code}

for line in read.lines:
    ...   # esto ES dato del cue
```

Y para la regla general que quedó:

> **Nunca trates un `str` de una lectura como si fuera el objeto.** Usá el
> `ObjectRead` y decidí explícitamente qué significa un objeto que no está.

Si en el futuro se toca otra herramienta que lee del pool, lo primero que hay que
mirar es si usa `read_object`.

---

## 9. Commits

| commit | qué hace |
|---|---|
| `e032430` | el módulo `cue_reads.py` con sus 45 tests |
| (este) | migración de 8 herramientas a la lectura tipada |