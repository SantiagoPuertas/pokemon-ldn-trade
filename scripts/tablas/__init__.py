"""Tablas de objetos y movimientos Gen III + resolucion por nombre.

    from tablas import resolver_objeto, resolver_movimiento, nombre_objeto

    resolver_objeto("pepita")         -> 110   (nombre ES oficial)
    resolver_objeto("nugget")         -> 110   (nombre EN de la decomp)
    resolver_objeto("110")            -> 110   (id numerico)
    resolver_movimiento("rayo solar") -> 76
    nombre_objeto(110)                -> "nugget"
    nombre_es_objeto(110)             -> "Pepita"

Los nombres se normalizan (minusculas, espacios/guiones bajos -> guion, se
quitan acentos), asi que "Rayo Solar", "rayo_solar" y "rayo-solar" valen igual.

Cobertura: **completa** en las tres direcciones. `POR_ID`/`NOMBRE_A_ID` salen de
la decompilacion `pokefirered` (son la fuente autoritativa de los ids) y
`NOMBRE_ES` de PokeAPI, que publica el `game_index` de generacion 3 de cada
objeto — ver `generar_nombres_es.py`. `ALIAS_ES` son apodos extra curados a mano
(«gigadrenaje», «mente-en-calma»…) para los que no coinciden con el nombre
oficial.
"""
import unicodedata
from . import _datos_objetos as _obj
from . import _datos_movimientos as _mov


def _norm(s: str) -> str:
    s = s.strip().lower().replace("_", "-").replace(" ", "-")
    s = "".join(c for c in unicodedata.normalize("NFD", s)
                if unicodedata.category(c) != "Mn")
    while "--" in s:
        s = s.replace("--", "-")
    return s


class NombreDesconocido(ValueError):
    pass


def _indice_es(datos):
    """nombre ES normalizado -> id. Se construye una vez por tabla.

    De "MT26 — Terremoto" se registran las dos formas, la entera y "mt26", para
    que valgan tanto el texto del desplegable como lo que uno escribiria.
    """
    indice = getattr(datos, "_INDICE_ES", None)
    if indice is None:
        indice = {}
        for ident, nombre in datos.NOMBRE_ES.items():
            indice[_norm(nombre)] = ident
            if "—" in nombre:
                indice[_norm(nombre.split("—")[0])] = ident
        datos._INDICE_ES = indice
    return indice


def _resolver(texto, datos, clase):
    """texto puede ser un id numerico, un nombre EN, uno ES o un alias curado."""
    if isinstance(texto, int):
        return texto
    t = texto.strip()
    if t.lstrip("-").isdigit():
        return int(t)
    n = _norm(t)
    # 1. alias curados (apodos que no son el nombre oficial) -> slug EN
    alias_es = {_norm(k): v for k, v in datos.ALIAS_ES.items()}
    if n in alias_es:
        n = _norm(alias_es[n])
    # 2. nombre oficial en español
    if n in _indice_es(datos):
        return _indice_es(datos)[n]
    # 3. nombre EN de la decompilacion
    if n in datos.NOMBRE_A_ID:
        return datos.NOMBRE_A_ID[n]
    # sugerencias por subcadena, tanto en EN como en ES
    cand = [s for s in datos.NOMBRE_A_ID if n in s]
    cand += [datos.NOMBRE_ES[i] for s, i in _indice_es(datos).items() if n in s]
    pista = f" ¿Quisiste decir: {', '.join(sorted(set(cand))[:8])}?" if cand else ""
    raise NombreDesconocido(
        f"{clase} desconocido: {texto!r}.{pista} "
        f"(usa un id numerico, un nombre EN como en POR_ID, o el nombre en español)")


def resolver_objeto(texto):
    return _resolver(texto, _obj, "Objeto")


def resolver_movimiento(texto):
    return _resolver(texto, _mov, "Movimiento")


def nombre_objeto(item_id: int) -> str:
    return _obj.POR_ID.get(int(item_id), f"#{item_id}")


def nombre_movimiento(move_id: int) -> str:
    return _mov.POR_ID.get(int(move_id), f"#{move_id}")


def nombre_es_objeto(item_id: int) -> str:
    """Nombre en español, o el EN si no lo hay (huecos sin usar de la tabla)."""
    return _obj.NOMBRE_ES.get(int(item_id)) or nombre_objeto(item_id)


def nombre_es_movimiento(move_id: int) -> str:
    return _mov.NOMBRE_ES.get(int(move_id)) or nombre_movimiento(move_id)


def objetos_por_categoria():
    """[(categoria, [{id, en, es}, ...]), ...] en el orden de _datos_objetos.

    Solo objetos reales: los huecos sin usar de la tabla interna (nombres tipo
    '0e2') no salen, porque en el juego no son nada.
    """
    grupos = []
    usados = set()
    for titulo, rangos in _obj.CATEGORIAS:
        entradas = []
        for desde, hasta in rangos:
            for ident in range(desde, hasta + 1):
                if ident in _obj.NOMBRE_ES:
                    entradas.append({"id": ident, "en": nombre_objeto(ident),
                                     "es": _obj.NOMBRE_ES[ident]})
                    usados.add(ident)
        if entradas:
            grupos.append((titulo, entradas))
    sueltos = [{"id": i, "en": nombre_objeto(i), "es": n}
               for i, n in sorted(_obj.NOMBRE_ES.items()) if i not in usados]
    if sueltos:
        grupos.append(("Otros", sueltos))
    return grupos


def movimientos_por_tipo():
    """[(tipo en español, [{id, en, es}, ...]), ...], en el orden del juego."""
    grupos = []
    for tipo, tipo_es in _mov.TIPOS_ES.items():
        entradas = [{"id": i, "en": nombre_movimiento(i), "es": _mov.NOMBRE_ES[i]}
                    for i, t in sorted(_mov.TIPO.items())
                    if t == tipo and i in _mov.NOMBRE_ES]
        entradas.sort(key=lambda e: _norm(e["es"]))
        if entradas:
            grupos.append((tipo_es, entradas))
    return grupos


OBJETOS_POR_ID = _obj.POR_ID
MOVIMIENTOS_POR_ID = _mov.POR_ID
OBJETOS_ES = _obj.NOMBRE_ES
MOVIMIENTOS_ES = _mov.NOMBRE_ES
