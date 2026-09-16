#!/usr/bin/env python3
"""Genera ficheros .pk3 (Gen III) validos para frlg-ldn-trade.

    # los dos ficheros minimos para el primer intercambio
    python3 scripts/make_pk3.py --preparar-primer-intercambio

    # uno a medida (objeto y movimientos por nombre EN o ES; ver scripts/tablas/)
    python3 scripts/make_pk3.py --especie mew --nivel 30 --naturaleza seria \\
        --movimientos "hiperrayo,llamarada,ventisca,trueno" --objeto pepita \\
        --ivs 31,31,31,31,31,31 --mote MEW -o pk3/mew.pk3

No reimplementa el formato: construye la estructura de 80 bytes descifrada y
luego la pasa por `frlgsim.mon.Mon`, el MISMO codigo que leera los ficheros
durante el intercambio. Si `Mon` dice que el checksum es correcto y decodifica
la especie y el nivel esperados, el fichero sirve.

Necesita el frlg-ldn-trade clonado (lo hace `scripts/setup_ubuntu.sh`).
"""

import argparse
import os
import random
import sys

# --- Localizar frlgsim -----------------------------------------------------
RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CANDIDATOS = [
    os.path.join(RAIZ, "vendor", "frlg-ldn-trade"),
    os.path.join(RAIZ, "..", "frlg-ldn-trade"),
    os.environ.get("FRLG_PATH", ""),
]
for _c in CANDIDATOS:
    if _c and os.path.isdir(os.path.join(_c, "frlgsim")):
        sys.path.insert(0, os.path.abspath(_c))
        break
try:
    from frlgsim import basestats, charmap, mon as monmod, stats
except ImportError:
    sys.exit(
        "No encuentro el paquete 'frlgsim'.\n"
        "Clona el proyecto primero:  bash scripts/setup_ubuntu.sh\n"
        "O indica su ruta:           FRLG_PATH=/ruta/a/frlg-ldn-trade python3 %s"
        % sys.argv[0]
    )

# --- Tablas de objetos y movimientos (nombre <-> id interno Gen III) --------
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import tablas

# --- Tablas mínimas --------------------------------------------------------
# Para los indices 1-251 el indice interno coincide con el numero de la Pokedex
# Nacional, asi que para Kanto (1-151) basta con la lista en orden.
KANTO = """bulbasaur ivysaur venusaur charmander charmeleon charizard squirtle
wartortle blastoise caterpie metapod butterfree weedle kakuna beedrill pidgey
pidgeotto pidgeot rattata raticate spearow fearow ekans arbok pikachu raichu
sandshrew sandslash nidoran-f nidorina nidoqueen nidoran-m nidorino nidoking
clefairy clefable vulpix ninetales jigglypuff wigglytuff zubat golbat oddish
gloom vileplume paras parasect venonat venomoth diglett dugtrio meowth persian
psyduck golduck mankey primeape growlithe arcanine poliwag poliwhirl poliwrath
abra kadabra alakazam machop machoke machamp bellsprout weepinbell victreebel
tentacool tentacruel geodude graveler golem ponyta rapidash slowpoke slowbro
magnemite magneton farfetchd doduo dodrio seel dewgong grimer muk shellder
cloyster gastly haunter gengar onix drowzee hypno krabby kingler voltorb
electrode exeggcute exeggutor cubone marowak hitmonlee hitmonchan lickitung
koffing weezing rhyhorn rhydon chansey tangela kangaskhan horsea seadra goldeen
seaking staryu starmie mr-mime scyther jynx electabuzz magmar pinsir tauros
magikarp gyarados lapras ditto eevee vaporeon jolteon flareon porygon omanyte
omastar kabuto kabutops aerodactyl snorlax articuno zapdos moltres dratini
dragonair dragonite mewtwo mew""".split()
ESPECIES = {nombre: i + 1 for i, nombre in enumerate(KANTO)}

# Naturaleza = personality % 25, en el orden del juego.
NATURALEZAS = """hardy lonely brave adamant naughty bold docile relaxed impish
lax timid hasty serious jolly naive modest mild quiet bashful rash calm gentle
sassy careful quirky""".split()
NAT_ES = {
    "fuerte": "hardy", "huraña": "lonely", "hurana": "lonely", "audaz": "brave",
    "firme": "adamant", "picara": "naughty", "pícara": "naughty", "osada": "bold",
    "docil": "docile", "dócil": "docile", "plácida": "relaxed", "placida": "relaxed",
    "agitada": "impish", "floja": "lax", "miedosa": "timid", "activa": "hasty",
    "seria": "serious", "alegre": "jolly", "ingenua": "naive", "modesta": "modest",
    "afable": "mild", "mansa": "quiet", "timida": "bashful", "tímida": "bashful",
    "alocada": "rash", "serena": "calm", "amable": "gentle", "grosera": "sassy",
    "cauta": "careful", "rara": "quirky",
}

# PP reales de unos pocos movimientos habituales; el resto usa 20 por defecto.
PP_CONOCIDOS = {1: 35, 5: 20, 33: 35, 118: 10, 144: 10, 156: 10, 219: 20}
PP_POR_DEFECTO = 20

JUEGO_FIRERED = 4          # gameOfOrigin en originsInfo
BALL_POKE = 4              # Poke Ball
IDIOMA_INGLES = 2


def especie_id(txt):
    t = txt.strip().lower()
    if t.isdigit():
        return int(t)
    if t in ESPECIES:
        return ESPECIES[t]
    raise argparse.ArgumentTypeError(
        "especie desconocida: %r (usa un nombre de Kanto en ingles o un numero)" % txt)


def naturaleza_id(txt):
    t = txt.strip().lower()
    t = NAT_ES.get(t, t)
    if t.isdigit():
        return int(t) % 25
    if t in NATURALEZAS:
        return NATURALEZAS.index(t)
    raise argparse.ArgumentTypeError("naturaleza desconocida: %r" % txt)


def objeto_id(txt):
    """Acepta id numerico, nombre EN (nugget) o alias ES (pepita)."""
    try:
        return tablas.resolver_objeto(txt)
    except tablas.NombreDesconocido as e:
        raise argparse.ArgumentTypeError(str(e))


def lista_movimientos(txt):
    """Hasta 4 movimientos por id o nombre (EN/ES), separados por coma.
    Rellena con 0 (ninguno) hasta 4."""
    partes = [p.strip() for p in txt.split(",") if p.strip() != ""]
    if len(partes) > 4:
        raise argparse.ArgumentTypeError("movimientos: como mucho 4")
    ids = []
    for p in partes:
        try:
            ids.append(tablas.resolver_movimiento(p))
        except tablas.NombreDesconocido as e:
            raise argparse.ArgumentTypeError(str(e))
    return (ids + [0, 0, 0, 0])[:4]


def lista_num(txt, n, maximo, nombre):
    partes = [p for p in txt.replace(" ", "").split(",") if p != ""]
    if len(partes) != n:
        raise argparse.ArgumentTypeError("%s: hacen falta %d valores" % (nombre, n))
    vals = []
    for p in partes:
        v = int(p)
        if not 0 <= v <= maximo:
            raise argparse.ArgumentTypeError("%s: %d fuera de rango 0..%d" % (nombre, v, maximo))
        vals.append(v)
    return vals


def buscar_pid(nature, otid, shiny, rng):
    """PID que cumple naturaleza y, si se pide, que el mon sea shiny.

    shiny  <=>  (otid_alto ^ otid_bajo ^ pid_alto ^ pid_bajo) < 8
    Se construye directamente en vez de sortear a ciegas: se fija el medio
    bajo del PID y se despeja el alto, lo que deja solo la naturaleza al azar
    (1 de cada 25 intentos).
    """
    otid_lo, otid_hi = otid & 0xFFFF, (otid >> 16) & 0xFFFF
    for _ in range(1_000_000):
        pid_lo = rng.randrange(0x10000)
        if shiny:
            pid_hi = otid_lo ^ otid_hi ^ pid_lo ^ rng.randrange(8)
        else:
            pid_hi = rng.randrange(0x10000)
            if (otid_lo ^ otid_hi ^ pid_lo ^ pid_hi) < 8:
                continue                      # evitar shiny por accidente
        pid = (pid_hi << 16) | pid_lo
        if pid % 25 == nature:
            return pid
    raise RuntimeError("no se encontro un PID valido")


def construir_pk3(species, level, nature, shiny, ivs, evs, moves, item,
                  nickname, ot_name, otid, ability_slot, friendship, rng,
                  fateful=None):
    """Devuelve los 80 bytes del .pk3 DESCIFRADO en orden canonico G,A,E,M.

    fateful: bit `modernFatefulEncounter`. En FRLG controla la OBEDIENCIA y, sobre
    todo, si un Mew/Deoxys **se puede intercambiar** (el juego rechaza uno sin el
    flag: "el otro entrenador no ha podido enviar su Pokemon"). None = automatico:
    se activa solo para Mew (151) y Deoxys (410).
    """
    if fateful is None:
        fateful = species in (151, 410)
    if species not in basestats.BASE_STATS:
        raise ValueError("la especie %d no tiene stats base en la tabla del proyecto" % species)
    if not 1 <= level <= stats.MAX_LEVEL:
        raise ValueError("nivel fuera de rango 1..100")
    if sum(evs) > 510:
        raise ValueError("la suma de EVs (%d) supera el maximo de 510" % sum(evs))

    pid = buscar_pid(nature, otid, shiny, rng)
    growth_rate = basestats.BASE_STATS[species][6]
    exp = stats.EXP_TABLES[growth_rate][level]

    # --- Growth (12 B) ---
    growth = bytearray(12)
    growth[0:2] = species.to_bytes(2, "little")
    growth[2:4] = item.to_bytes(2, "little")
    growth[4:8] = exp.to_bytes(4, "little")
    growth[8] = 0                                    # ppBonuses
    growth[9] = friendship

    # --- Attacks (12 B) ---
    attacks = bytearray(12)
    for i, mv in enumerate(moves):
        attacks[i * 2:i * 2 + 2] = mv.to_bytes(2, "little")
        attacks[8 + i] = PP_CONOCIDOS.get(mv, PP_POR_DEFECTO) if mv else 0

    # --- EVs y concurso (12 B) ---
    evbloc = bytearray(12)
    evbloc[0:6] = bytes(evs)

    # --- Misc (12 B) ---
    misc = bytearray(12)
    misc[0] = 0                                      # pokerus
    misc[1] = 0                                      # metLocation
    origins = (level & 0x7F) | (JUEGO_FIRERED << 7) | (BALL_POKE << 11)
    misc[2:4] = origins.to_bytes(2, "little")
    iv_word = 0
    for i, v in enumerate(ivs):
        iv_word |= (v & 0x1F) << (5 * i)
    if ability_slot:
        iv_word |= 1 << 31                           # bit 30 = isEgg, bit 31 = habilidad
    misc[4:8] = iv_word.to_bytes(4, "little")
    # Palabra de cintas + obediencia. bit 31 = modernFatefulEncounter: en FRLG
    # habilita la obediencia y el intercambio de Mew/Deoxys (pokemon.h, Substruct3).
    ribbons = 0
    if fateful:
        ribbons |= 1 << 31
    misc[8:12] = ribbons.to_bytes(4, "little")

    seguro = bytes(growth + attacks + evbloc + misc)
    assert len(seguro) == 48

    # --- Cabecera (32 B) ---
    pk3 = bytearray(80)
    pk3[0:4] = pid.to_bytes(4, "little")
    pk3[4:8] = otid.to_bytes(4, "little")
    pk3[8:18] = charmap.encode(nickname.upper(), width=10)
    pk3[18] = IDIOMA_INGLES
    pk3[19] = 0x02                                   # hasSpecies
    pk3[20:27] = charmap.encode(ot_name.upper(), width=7)
    pk3[27] = 0                                      # markings
    # El checksum suma los 24 u16 de la region segura DESCIFRADA. Es una suma
    # plana, asi que no depende del barajado: vale igual antes y despues.
    checksum = sum(int.from_bytes(seguro[i * 2:i * 2 + 2], "little")
                   for i in range(24)) & 0xFFFF
    pk3[28:30] = checksum.to_bytes(2, "little")
    pk3[32:80] = seguro
    return bytes(pk3)


def generar(ruta, **kw):
    """Construye, valida con el codigo del propio proyecto y escribe el fichero."""
    pk3 = construir_pk3(**kw)

    # Validacion con frlgsim: es el mismo parser que usara el intercambio.
    m = monmod.Mon.from_pk3(pk3)
    d = m.decode()
    problemas = []
    if not d:
        problemas.append("no decodifica")
    else:
        if not d["checksum_ok"]:
            problemas.append("checksum invalido (%04x != %04x)" % (d["calc"], d["stored"]))
        if d["species"] != kw["species"]:
            problemas.append("especie %d != %d esperada" % (d["species"], kw["species"]))
        if d["level"] != kw["level"]:
            problemas.append("nivel %s != %d esperado" % (d["level"], kw["level"]))
    # Ida y vuelta: cifrar y volver a descifrar debe devolver lo mismo
    if monmod.to_decrypted(m.party_bytes())[:80] != pk3:
        problemas.append("el ciclo cifrar/descifrar no es reversible")
    if problemas:
        raise RuntimeError("el .pk3 generado no es valido:\n  - " + "\n  - ".join(problemas))

    os.makedirs(os.path.dirname(os.path.abspath(ruta)), exist_ok=True)
    with open(ruta, "wb") as f:
        f.write(pk3)
    return m, d


def main():
    ap = argparse.ArgumentParser(
        description="Genera .pk3 Gen III validos para frlg-ldn-trade",
        formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--preparar-primer-intercambio", action="store_true",
                    help="crea pk3/dummy.pk3 y pk3/enviar.pk3 y termina")
    ap.add_argument("-o", "--salida", default="pk3/generado.pk3")
    ap.add_argument("--especie", type=especie_id, default="bulbasaur")
    ap.add_argument("--nivel", type=int, default=5)
    ap.add_argument("--naturaleza", type=naturaleza_id, default="hardy")
    ap.add_argument("--shiny", action="store_true")
    ap.add_argument("--ivs", default="31,31,31,31,31,31",
                    help="PS,Ata,Def,Vel,AtEsp,DefEsp (0-31)")
    ap.add_argument("--evs", default="0,0,0,0,0,0", help="PS,Ata,Def,Vel,AtEsp,DefEsp (0-255)")
    ap.add_argument("--movimientos", default="tackle",
                    help="hasta 4, por id o nombre EN/ES separados por coma "
                         "(ej: \"rayo-solar,bomba-lodo,somnifero,drenadoras\")")
    ap.add_argument("--objeto", type=objeto_id, default=0,
                    help="id, nombre EN (nugget) o alias ES (pepita)")
    ap.add_argument("--mote", default="")
    ap.add_argument("--ot", default="EMU", help="nombre del entrenador original")
    ap.add_argument("--otid", type=lambda s: int(s, 0), default=None)
    ap.add_argument("--habilidad", type=int, choices=(0, 1), default=0)
    ap.add_argument("--amistad", type=int, default=70)
    ap.add_argument("--fateful", action=argparse.BooleanOptionalAction, default=None,
                    help="bit modernFatefulEncounter (obediencia/intercambio de "
                         "Mew y Deoxys). Por defecto: automatico para Mew/Deoxys")
    ap.add_argument("--semilla", type=int, default=None,
                    help="semilla del generador, para resultados reproducibles")
    args = ap.parse_args()

    rng = random.Random(args.semilla)
    otid = args.otid if args.otid is not None else rng.randrange(1 << 32)

    def emitir(ruta, **kw):
        kw.setdefault("otid", otid)
        kw.setdefault("rng", rng)
        m, d = generar(ruta, **kw)
        tam = os.path.getsize(ruta)
        print("  %-22s %3d B  %s" % (os.path.basename(ruta), tam, m.describe()))

    if args.preparar_primer_intercambio:
        print("Generando los dos .pk3 minimos para el primer intercambio:\n")
        emitir(os.path.join(RAIZ, "pk3", "dummy.pk3"),
               species=ESPECIES["rattata"], level=3, nature=0, shiny=False,
               ivs=[0] * 6, evs=[0] * 6, moves=[33, 0, 0, 0], item=0,
               nickname="RATTATA", ot_name=args.ot, ability_slot=0, friendship=70)
        emitir(os.path.join(RAIZ, "pk3", "enviar.pk3"),
               species=ESPECIES["bulbasaur"], level=5, nature=naturaleza_id("modest"),
               shiny=False, ivs=[31] * 6, evs=[0] * 6, moves=[33, 0, 0, 0], item=0,
               nickname="BULBASAUR", ot_name=args.ot, ability_slot=0, friendship=70)
        print("\nListos. El primero es relleno de party; el segundo es el que se envia.")
        print("Comprueba que se leen bien con:  python3 scripts/read_pk3.py pk3/*.pk3")
        return 0

    if args.mote:
        mote = args.mote
    elif 1 <= args.especie <= len(KANTO):
        mote = KANTO[args.especie - 1]
    else:
        mote = "MON"

    print("Generando:\n")
    emitir(args.salida,
           species=args.especie, level=args.nivel, nature=args.naturaleza,
           shiny=args.shiny,
           ivs=lista_num(args.ivs, 6, 31, "ivs"),
           evs=lista_num(args.evs, 6, 255, "evs"),
           moves=lista_movimientos(args.movimientos),
           item=args.objeto, nickname=mote,
           ot_name=args.ot, ability_slot=args.habilidad, friendship=args.amistad,
           fateful=args.fateful)
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    # ArgumentTypeError no es ValueError: sin esto, un nombre de movimiento mal
    # escrito salia como traceback en vez de como error.
    except (ValueError, RuntimeError, argparse.ArgumentTypeError) as e:
        sys.exit("Error: %s" % e)
