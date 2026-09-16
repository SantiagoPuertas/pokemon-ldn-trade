# Tablas de objetos y movimientos (Gen III)

Todo lo que hace falta para hablar de objetos y movimientos **por nombre** en
vez de por número: los 310 objetos y los 354 movimientos de FireRed, con su id
interno y su nombre oficial en español.

| Dato | Qué es | De dónde sale |
|---|---|---|
| `POR_ID`, `NOMBRE_A_ID` | id interno ↔ nombre EN | decompilación `pokefirered` — **autoritativo** |
| `NOMBRE_ES` | id interno → nombre oficial en español | PokeAPI |
| `TIPO`, `TIPOS_ES` (movimientos) | tipo de cada movimiento, para agrupar | PokeAPI |
| `CATEGORIAS` (objetos) | rangos de ids por categoría, para agrupar | a mano |
| `ALIAS_ES` | apodos extra («gigadrenaje», «mente-en-calma») | a mano |

`__init__.py` expone `resolver_objeto()`, `resolver_movimiento()`,
`nombre_objeto()`, `nombre_movimiento()`, `nombre_es_objeto()`,
`nombre_es_movimiento()`, `objetos_por_categoria()` y `movimientos_por_tipo()`.

Se resuelve por id, por nombre EN, por nombre ES o por alias:

```python
resolver_objeto("Pepita") == resolver_objeto("nugget") == resolver_objeto("110")
resolver_movimiento("Rayo Solar") == resolver_movimiento("solar-beam") == 76
resolver_objeto("MT26")            # -> 314, la MT de Terremoto
```

## Regenerar los nombres en español

```bash
python3 scripts/tablas/generar_nombres_es.py     # necesita Internet
```

Reescribe el bloque final de los dos ficheros de datos; lo de arriba —incluidos
los ids y el `ALIAS_ES` curado— no se toca.

El truco que lo hace fiable: PokeAPI publica, para cada objeto, el
`game_index` de la **3ª generación**, que *es* el índice interno de FireRed. No
hay que emparejar nombres ni adivinar nada. Con los movimientos es aún más
directo: el id nacional 1..354 coincide con el índice interno.

Dos correcciones que aplica el generador a mano, documentadas en su cabecera:

- **id 261**: PokeAPI cuelga dos objetos de ese índice y gana la Llave Sótano;
  en FireRed el 261 es el **Buscaobjetos** (la llave es el 271). Manda la decomp.
- **Encanto, Beso Dulce y Claro de Luna** salen como tipo Hada, que no existe en
  la 3ª generación: se fuerzan a Normal.

## Regenerar los ids (sólo si cambia la fuente)

```bash
curl -fsSL https://raw.githubusercontent.com/pret/pokefirered/master/include/constants/items.h -o /tmp/items.h
curl -fsSL https://raw.githubusercontent.com/pret/pokefirered/master/include/constants/moves.h -o /tmp/moves.h
```

y volver a correr el parser (ver el historial de git de este directorio).

Fuentes: <https://github.com/pret/pokefirered> y <https://pokeapi.co>. Aquí sólo
se usan las correspondencias nombre↔id, que son datos de interoperabilidad.
