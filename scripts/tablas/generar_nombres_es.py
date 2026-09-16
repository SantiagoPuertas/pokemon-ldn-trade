#!/usr/bin/env python3
"""Regenera los nombres en español de objetos y movimientos.

    python3 scripts/tablas/generar_nombres_es.py          # necesita Internet

Los ids internos (`POR_ID`, `NOMBRE_A_ID`) vienen de la decompilacion
`pokefirered` y son la fuente autoritativa; aqui solo se les pone **nombre en
español**, que se saca de PokeAPI:

    - movimientos: el id nacional 1..354 coincide con el indice interno de Gen III
    - objetos:     PokeAPI publica el `game_index` de generacion 3 de cada objeto,
                   que ES el indice interno de FireRed. No hay que adivinar nada.
    - MT/MO:       ademas se les pega el movimiento que enseñan en FRLG,
                   para que en un desplegable se lea "MT26 - Terremoto".

Escribe el bloque final de `_datos_objetos.py` y `_datos_movimientos.py`
(a partir del marcador de abajo); lo de encima —incluido el `ALIAS_ES` curado a
mano— no se toca.
"""

import json
import os
import re
import sys
import urllib.request

AQUI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(AQUI))
from tablas import _datos_movimientos as _mov, _datos_objetos as _obj   # noqa: E402

API = "https://graphql.pokeapi.co/v1beta2"
MARCADOR = "# === NOMBRES ES (AUTOGENERADO por generar_nombres_es.py) ==="

# Tipos: PokeAPI devuelve el tipo ACTUAL. Estos tres pasaron a Hada en la 7ª
# generacion; en FireRed eran Normal, que es lo que interesa aqui.
TIPO_GEN3 = {"charm": "normal", "sweet-kiss": "normal", "moonlight": "normal"}

TIPOS_ES = {
    "normal": "Normal", "fighting": "Lucha", "flying": "Volador", "poison": "Veneno",
    "ground": "Tierra", "rock": "Roca", "bug": "Bicho", "ghost": "Fantasma",
    "steel": "Acero", "fire": "Fuego", "water": "Agua", "grass": "Planta",
    "electric": "Eléctrico", "psychic": "Psíquico", "ice": "Hielo",
    "dragon": "Dragón", "dark": "Siniestro", "fairy": "Hada",
}

# Objetos que PokeAPI no cubre bien. 261 es el caso raro: PokeAPI le cuelga dos
# objetos al mismo indice y gana la Llave Sotano, pero en FireRed el 261 es el
# Buscaobjetos (el 271 es la llave). La decomp manda.
NOMBRE_ES_MANUAL = {
    261: "Buscaobjetos",
    271: "Llave Sótano",
    176: "Baya sin usar 1",
    177: "Baya sin usar 2",
    178: "Baya sin usar 3",
}

# Categorias para agrupar el desplegable. Rangos de ids, inclusivos, en el
# orden en que se quieren ver.
CATEGORIAS = [
    ("Poké Balls",          [(1, 12)]),
    ("Medicinas",           [(13, 45)]),
    ("Vitaminas",           [(63, 71)]),
    ("Objetos de combate",  [(73, 81)]),
    ("Repelentes y huida",  [(83, 86)]),
    ("Piedras evolutivas",  [(93, 98)]),
    ("Tesoros",             [(46, 51), (103, 111)]),
    ("Cartas",              [(121, 132)]),
    ("Bayas",               [(133, 178)]),
    ("Objetos equipados",   [(179, 225)]),
    ("Pañuelos de concurso", [(254, 258)]),
    ("MT — máquinas técnicas", [(289, 338)]),
    ("MO — máquinas ocultas",  [(339, 346)]),
    ("Objetos clave",       [(259, 288), (347, 374)]),
]


def consultar(query):
    peticion = urllib.request.Request(
        API, data=json.dumps({"query": query}).encode(),
        # Sin User-Agent, PokeAPI responde 403 al urllib de Python.
        headers={"Content-Type": "application/json",
                 "User-Agent": "pokemon-ldn-trade/1.0"})
    with urllib.request.urlopen(peticion, timeout=60) as r:
        respuesta = json.load(r)
    if "errors" in respuesta:
        sys.exit("PokeAPI: %s" % respuesta["errors"])
    return respuesta["data"]


def movimientos():
    datos = consultar("""{
      move(limit: 400, where: {id: {_lte: 354}}, order_by: {id: asc}) {
        id name type { name }
        movenames(where: {language: {name: {_eq: "es"}}}) { name }
      }
    }""")["move"]
    nombres, tipos = {}, {}
    for m in datos:
        if _mov.POR_ID.get(m["id"]) != m["name"]:
            print("  aviso: id %d es %r aqui y %r en PokeAPI"
                  % (m["id"], _mov.POR_ID.get(m["id"]), m["name"]))
        if m["movenames"]:
            nombres[m["id"]] = m["movenames"][0]["name"]
        tipos[m["id"]] = TIPO_GEN3.get(m["name"], m["type"]["name"])
    return nombres, tipos


def objetos():
    datos = consultar("""{
      item(limit: 2000, order_by: {id: asc}) {
        name
        itemnames(where: {language: {name: {_eq: "es"}}}) { name }
        itemgameindices(where: {generation_id: {_eq: 3}}) { game_index }
      }
    }""")["item"]
    nombres = {}
    for it in datos:
        if not it["itemgameindices"] or not it["itemnames"]:
            continue
        ident = it["itemgameindices"][0]["game_index"]
        if ident not in _obj.POR_ID:
            continue            # objeto de Esmeralda: en FireRed no existe
        # Puede haber dos objetos con el mismo indice (PokeAPI arrastra nombres
        # de generaciones posteriores); se queda el que coincide con la decomp.
        if ident in nombres and _obj.POR_ID.get(ident) != it["name"]:
            continue
        nombres[ident] = it["itemnames"][0]["name"]

    # MT/MO: pegarles el movimiento que enseñan en FireRed/LeafGreen.
    maquinas = consultar("""{
      machine(limit: 200, where: {versiongroup: {name: {_eq: "firered-leafgreen"}}}) {
        item { name }
        move { movenames(where: {language: {name: {_eq: "es"}}}) { name } }
      }
    }""")["machine"]
    por_slug = {n: i for i, n in _obj.POR_ID.items()}
    for maq in maquinas:
        ident = por_slug.get(maq["item"]["name"])
        if ident in nombres and maq["move"]["movenames"]:
            nombres[ident] = "%s — %s" % (nombres[ident], maq["move"]["movenames"][0]["name"])

    nombres.update(NOMBRE_ES_MANUAL)
    return nombres


def bloque(titulo, nombres, extra=""):
    lineas = ["%s\n" % MARCADOR,
              "# %s\n" % titulo,
              "\nNOMBRE_ES = {\n"]
    for ident in sorted(nombres):
        lineas.append("    %d: %r,\n" % (ident, nombres[ident]))
    lineas.append("}\n")
    return "".join(lineas) + extra


def escribir(ruta, contenido):
    texto = open(ruta).read()
    corte = texto.find(MARCADOR)
    if corte != -1:
        texto = texto[:corte]
    texto = texto.rstrip("\n") + "\n\n" + contenido
    open(ruta, "w").write(texto)
    print("  escrito %s" % os.path.basename(ruta))


def main():
    print("Descargando de PokeAPI…")
    nombres_mov, tipos = movimientos()
    nombres_obj = objetos()
    print("  %d movimientos y %d objetos con nombre ES" % (len(nombres_mov), len(nombres_obj)))

    tipos_py = "\n# Tipo de cada movimiento (el de la 3ª generacion). Solo sirve para\n" \
               "# agrupar el desplegable de la GUI.\nTIPO = {\n"
    tipos_py += "".join("    %d: %r,\n" % (i, tipos[i]) for i in sorted(tipos)) + "}\n"
    tipos_py += "\nTIPOS_ES = %s\n" % json.dumps(TIPOS_ES, ensure_ascii=False, indent=4) \
        .replace('"', "'").replace("{\n", "{\n").replace("\n}", ",\n}")

    escribir(os.path.join(AQUI, "_datos_movimientos.py"),
             bloque("Nombres en español, de PokeAPI (id nacional == indice Gen III).",
                    nombres_mov, tipos_py))

    cat_py = "\n# Categorias para agrupar el desplegable: (titulo, [(id_min, id_max), ...]).\n"
    cat_py += "CATEGORIAS = [\n"
    for titulo, rangos in CATEGORIAS:
        cat_py += "    (%r, %r),\n" % (titulo, rangos)
    cat_py += "]\n"
    escribir(os.path.join(AQUI, "_datos_objetos.py"),
             bloque("Nombres en español, de PokeAPI (game_index de generacion 3).",
                    nombres_obj, cat_py))
    return 0


if __name__ == "__main__":
    sys.exit(main())
