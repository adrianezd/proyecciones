"""
Portada de Proyecciones: «España en datos hoy», el comparador de series y
los avisos que enseñan las once páginas.

    python -m fuente.construir

No descarga nada de las fuentes originales: lee la caché que cada página
ya guarda en su propio repositorio (cache/*.json, la escribe su GitHub
Action dos veces al día) y con eso calcula los cambios, los avisos y lo
más llamativo. Solo usa la librería estándar.

Escribe:
  docs/datos/resumen.json          último dato, cambios y avisos de cada serie
  docs/datos/series/<id>.json      la serie para el comparador
  docs/hoy/index.html              España en datos hoy
  historia/gasolina.json           media nacional de cada día (la caché de
                                   gasolina solo guarda el día de hoy, así
                                   que el histórico lo lleva este repo)

Como el resto del proyecto: si una caché no responde, esa serie no sale.
Nunca se rellena con datos aproximados.
"""

from __future__ import annotations

import concurrent.futures as cf
import datetime as dt
import html
import json
import math
import urllib.request
from pathlib import Path

RAIZ = Path(__file__).parent.parent
DOCS = RAIZ / "docs"
DATOS = DOCS / "datos"
HISTORIA = RAIZ / "historia"

USUARIO = "adrianezd"
RAW = "https://raw.githubusercontent.com/" + USUARIO + "/{repo}/main/cache/{fichero}"
HUB = f"https://{USUARIO}.github.io/proyecciones/"


def sitio(repo: str) -> str:
    return f"https://{USUARIO}.github.io/{repo}/"


# id, repo, fichero, nombre corto, sujeto de la frase, grupo, unidad, tipo, decimales
#   tipo «precio»: los cambios van en %, y en el comparador se lleva a base 100
#   tipo «tasa»: ya es un porcentaje; los cambios van en puntos
SERIES = [
    ("sp500", "proyecciones-bolsa", "cotiz-sp500.json", "S&P 500", "El S&P 500", "Bolsa", "puntos", "precio", 0),
    ("nasdaq", "proyecciones-bolsa", "cotiz-nasdaq.json", "Nasdaq 100", "El Nasdaq 100", "Bolsa", "puntos", "precio", 0),
    ("ibex", "proyecciones-bolsa", "cotiz-ibex.json", "IBEX 35", "El IBEX 35", "Bolsa", "puntos", "precio", 0),
    ("eurostx", "proyecciones-bolsa", "cotiz-eurostx.json", "Euro Stoxx 50", "El Euro Stoxx 50", "Bolsa", "puntos", "precio", 0),
    ("nikkei", "proyecciones-bolsa", "cotiz-nikkei.json", "Nikkei 225", "El Nikkei 225", "Bolsa", "puntos", "precio", 0),
    ("brent", "proyecciones-materias-primas", "cotiz-brent.json", "Petróleo Brent", "El petróleo Brent", "Materias primas", "$/barril", "precio", 2),
    ("gas", "proyecciones-materias-primas", "cotiz-gas.json", "Gas natural", "El gas natural", "Materias primas", "$/MMBtu", "precio", 2),
    ("oro", "proyecciones-materias-primas", "cotiz-oro.json", "Oro", "El oro", "Materias primas", "$/onza", "precio", 0),
    ("plata", "proyecciones-materias-primas", "cotiz-plata.json", "Plata", "La plata", "Materias primas", "$/onza", "precio", 2),
    ("eurusd", "proyecciones-divisas", "cotiz-eurusd.json", "Euro / dólar", "El euro frente al dólar", "Divisas", "$ por €", "precio", 4),
    ("eurgbp", "proyecciones-divisas", "cotiz-eurgbp.json", "Euro / libra", "El euro frente a la libra", "Divisas", "£ por €", "precio", 4),
    ("eurjpy", "proyecciones-divisas", "cotiz-eurjpy.json", "Euro / yen", "El euro frente al yen", "Divisas", "¥ por €", "precio", 2),
    ("bitcoin", "proyecciones-bitcoin", "cotiz-bitcoin.json", "Bitcoin", "El bitcoin", "Cripto", "€", "precio", 0),
    ("ethereum", "proyecciones-bitcoin", "cotiz-ethereum.json", "Ethereum", "Ethereum", "Cripto", "€", "precio", 0),
    ("xrp", "proyecciones-bitcoin", "cotiz-xrp.json", "XRP", "XRP", "Cripto", "€", "precio", 3),
    ("bono-es", "proyecciones-bonos", "bce-ES.json", "Bono España", "La rentabilidad del bono español a 10 años", "Bonos", "%", "tasa", 2),
    ("bono-de", "proyecciones-bonos", "bce-DE.json", "Bono Alemania", "La rentabilidad del bono alemán a 10 años", "Bonos", "%", "tasa", 2),
    ("bono-it", "proyecciones-bonos", "bce-IT.json", "Bono Italia", "La rentabilidad del bono italiano a 10 años", "Bonos", "%", "tasa", 2),
    ("bono-fr", "proyecciones-bonos", "bce-FR.json", "Bono Francia", "La rentabilidad del bono francés a 10 años", "Bonos", "%", "tasa", 2),
    ("bono-pt", "proyecciones-bonos", "bce-PT.json", "Bono Portugal", "La rentabilidad del bono portugués a 10 años", "Bonos", "%", "tasa", 2),
    ("bono-gr", "proyecciones-bonos", "bce-GR.json", "Bono Grecia", "La rentabilidad del bono griego a 10 años", "Bonos", "%", "tasa", 2),
    ("vivienda", "proyecciones-vivienda", "ine-IPV1279.json", "Precio de la vivienda", "El precio de la vivienda", "Vivienda", "% anual", "tasa", 1),
    ("alquiler", "proyecciones-alquiler", "ine-IPVA9824.json", "Alquiler, nuevos contratos", "El alquiler de los nuevos contratos", "Vivienda", "% anual", "tasa", 1),
]
GRUPOS = ["Bolsa", "Materias primas", "Divisas", "Cripto", "Bonos", "Vivienda", "Carburantes"]

CABECERAS = {"User-Agent": "proyecciones-portada (+https://github.com/adrianezd/proyecciones)"}


# ---------------------------------------------------------------- descarga

def bajar(repo: str, fichero: str):
    url = RAW.format(repo=repo, fichero=fichero)
    for _ in range(3):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers=CABECERAS), timeout=90) as r:
                return json.loads(r.read().decode("utf-8"))
        except Exception as e:   # noqa: BLE001
            ultimo = e
    print(f"  FALLO       {repo}/{fichero} ({type(ultimo).__name__})")
    return None


def a_puntos(bruto) -> list[tuple[str, float]]:
    """Cualquiera de las cachés a [(fecha ISO, valor)] ordenado."""
    if bruto is None:
        return []
    if isinstance(bruto, list):          # cotizaciones y BCE: [{"f", "v"}]
        out = []
        for p in bruto:
            f, v = p.get("f"), p.get("v")
            if f is None or v is None:
                continue
            if len(f) == 7:                  # mensual "AAAA-MM": se fecha a fin de mes
                a, m = int(f[:4]), int(f[5:])
                fin = (dt.date(a + (m == 12), m % 12 + 1, 1) - dt.timedelta(days=1)).isoformat()
                out.append((fin, float(v)))
            else:
                out.append((f[:10], float(v)))
        return sorted(out)
    if isinstance(bruto, dict) and "Data" in bruto:   # INE: anual
        out = [(f"{d['Anyo']}-12-31", float(d["Valor"])) for d in bruto["Data"]
               if d.get("Valor") is not None and not d.get("Secreto")]
        return sorted(out)
    return []


# ---------------------------------------------------------------- números

def num(v: float, dec: int = 0) -> str:
    """Número a la española: 1.234,56."""
    texto = f"{abs(v):,.{dec}f}".replace(",", "X").replace(".", ",").replace("X", ".")
    return ("−" if v < 0 else "") + texto


def fecha_larga(f: str) -> str:
    meses = ["enero", "febrero", "marzo", "abril", "mayo", "junio", "julio", "agosto",
             "septiembre", "octubre", "noviembre", "diciembre"]
    d = dt.date.fromisoformat(f)
    return f"{d.day} de {meses[d.month - 1]} de {d.year}"


def valor_en(puntos, fecha: dt.date):
    """Último valor en o antes de esa fecha."""
    elegido = None
    for f, v in puntos:
        if dt.date.fromisoformat(f) <= fecha:
            elegido = (f, v)
        else:
            break
    return elegido


def frecuencia(puntos) -> str:
    if len(puntos) < 3:
        return "anual"
    a, b = dt.date.fromisoformat(puntos[-2][0]), dt.date.fromisoformat(puntos[-1][0])
    dias = (b - a).days
    return "diaria" if dias <= 5 else "mensual" if dias <= 40 else "anual"


# ---------------------------------------------------------------- estadística

def analizar(cfg: dict, puntos) -> dict:
    hoy = dt.date.today()
    f_ult, v_ult = puntos[-1]
    d_ult = dt.date.fromisoformat(f_ult)
    freq = frecuencia(puntos)
    precio = cfg["tipo"] == "precio"

    def cambio(dias):
        p = valor_en(puntos, d_ult - dt.timedelta(days=dias))
        if not p or p[1] == 0:
            return None
        return round((v_ult / p[1] - 1) * 100, 2) if precio else round(v_ult - p[1], 2)

    cambios = {"d": cambio(1) if freq == "diaria" else None, "s": cambio(7) if freq == "diaria" else None,
               "m": cambio(30) if freq != "anual" else None, "a": cambio(365)}
    if freq == "diaria" and cambios["d"] is not None:
        # el cambio «de un día» es frente a la sesión anterior, aunque haya fin de semana en medio
        v_ant = puntos[-2][1]
        cambios["d"] = round((v_ult / v_ant - 1) * 100, 2) if precio else round(v_ult - v_ant, 2)

    ano = [v for f, v in puntos if dt.date.fromisoformat(f) > d_ult - dt.timedelta(days=365)]
    info = {
        "id": cfg["id"], "nombre": cfg["nombre"], "sujeto": cfg["sujeto"], "grupo": cfg["grupo"],
        "unidad": cfg["unidad"], "tipo": cfg["tipo"], "dec": cfg["dec"], "pagina": cfg["repo"],
        "url": sitio(cfg["repo"]), "frecuencia": freq,
        "fecha": f_ult, "ultimo": round(v_ult, 6), "cambios": cambios, "n": len(puntos),
        "alto52": round(max(ano), 6), "bajo52": round(min(ano), 6), "maxhist": round(max(v for _, v in puntos), 6),
        "fresco": (hoy - d_ult).days <= (5 if freq == "diaria" else 45 if freq == "mensual" else 400),
        "spark": [round(v, 6) for _, v in puntos[-90:]] if freq == "diaria" else [round(v, 6) for _, v in puntos[-24:]],
    }

    # rareza del movimiento (z): cuánto se sale de lo normal en esta serie
    z1 = z5 = zm = 0.0
    if freq == "diaria" and precio:
        diarios = []
        for (fa, va), (fb, vb) in zip(puntos[-262:-1], puntos[-261:]):
            if va > 0 and (dt.date.fromisoformat(fb) - dt.date.fromisoformat(fa)).days <= 5:
                diarios.append(math.log(vb / va))
        if len(diarios) > 60:
            media = sum(diarios) / len(diarios)
            sd = math.sqrt(sum((x - media) ** 2 for x in diarios) / (len(diarios) - 1)) or 1e-9
            info["vol_diaria"] = round(sd * 100, 3)
            if cambios["d"] is not None:
                z1 = math.log(1 + cambios["d"] / 100) / sd
            if cambios["s"] is not None:
                z5 = math.log(1 + cambios["s"] / 100) / (sd * math.sqrt(5))
            if cambios["m"] is not None:
                zm = math.log(1 + cambios["m"] / 100) / (sd * math.sqrt(21))
    elif freq in ("mensual", "anual"):
        saltos = [b - a for (_, a), (_, b) in zip(puntos[:-1], puntos[1:])][-60:]
        if len(saltos) > 8:
            sd = math.sqrt(sum(x * x for x in saltos) / len(saltos)) or 1e-9
            ultimo_salto = puntos[-1][1] - puntos[-2][1]
            zm = ultimo_salto / sd
            info["salto"] = round(ultimo_salto, 2)
    info["z"] = {"d": round(z1, 2), "s": round(z5, 2), "m": round(zm, 2)}
    info["puntuacion"] = round(max(abs(z1), abs(z5), abs(zm) * 0.8), 2) if info["fresco"] else 0
    return info


def sube_baja(v: float, femenino: bool = False) -> str:
    return "sube" if v > 0 else "baja"


def frase_cambio(s: dict, clave: str) -> str | None:
    v = s["cambios"].get(clave)
    if v is None or v == 0:
        return None
    cuando = {"d": "en un día", "s": "en una semana", "m": "en un mes", "a": "en un año"}[clave]
    if s["tipo"] == "precio":
        return f"{s['sujeto']} {sube_baja(v)} un {num(abs(v), 1)} % {cuando}"
    return f"{s['sujeto']} {sube_baja(v)} {num(abs(v), 2)} puntos {cuando}"


def frase_destacada(s: dict) -> str:
    """La frase de «Lo más llamativo» para una serie."""
    if s["frecuencia"] == "anual":
        v = s["ultimo"]
        texto = f"{s['sujeto']} {'sube' if v >= 0 else 'baja'} un {num(abs(v), s['dec'])} % en un año"
        if s.get("salto") is not None:
            texto += f", {num(abs(s['salto']), 1)} puntos {'más' if s['salto'] > 0 else 'menos'} que el año anterior"
        return texto + " (INE)."
    z = s["z"]
    clave = max(("d", "s", "m"), key=lambda k: abs(z.get(k, 0)) if s["cambios"].get(k) is not None else -1)
    texto = frase_cambio(s, clave) or frase_cambio(s, "a") or s["sujeto"]
    extra = ""
    if s.get("n", 0) < 250:
        pass
    elif s["ultimo"] >= s["maxhist"]:
        extra = ", en máximos históricos"
    elif s["ultimo"] >= s["alto52"]:
        extra = ", en máximos de un año"
    elif s["ultimo"] <= s["bajo52"]:
        extra = ", en mínimos de un año"
    return texto + extra + "."


# ---------------------------------------------------------------- avisos

def avisos_de(s: dict) -> list[dict]:
    if not s["fresco"]:
        return []
    out = []

    def aviso(tipo, texto, nivel, puntuacion):
        out.append({"id": f"{s['id']}-{tipo}-{s['fecha']}", "serie": s["id"], "pagina": s["pagina"], "url": s["url"],
                    "texto": texto, "nivel": nivel, "fecha": s["fecha"], "puntuacion": round(puntuacion, 2)})

    z = s["z"]
    # los máximos y mínimos solo cuentan con al menos un año de historia
    largo = s.get("n", 0) >= 250
    if s["frecuencia"] == "diaria" and s["tipo"] == "precio":
        if abs(z["d"]) >= 2.5 and frase_cambio(s, "d"):
            aviso("dia", frase_cambio(s, "d") + ": un movimiento muy poco habitual para esta serie.", "alto" if abs(z["d"]) >= 3.5 else "medio", abs(z["d"]))
        elif abs(z["s"]) >= 2.5 and frase_cambio(s, "s"):
            aviso("semana", frase_cambio(s, "s") + ": un movimiento muy poco habitual para esta serie.", "alto" if abs(z["s"]) >= 3.5 else "medio", abs(z["s"]))
        if not largo:
            pass
        elif s["ultimo"] >= s["maxhist"]:
            aviso("maxhist", f"{s['sujeto']} marca máximo histórico: {num(s['ultimo'], s['dec'])} {s['unidad']}.", "medio", 2.6)
        elif s["ultimo"] >= s["alto52"]:
            aviso("max52", f"{s['sujeto']} toca su máximo de un año: {num(s['ultimo'], s['dec'])} {s['unidad']}.", "bajo", 2.0)
        elif s["ultimo"] <= s["bajo52"]:
            aviso("min52", f"{s['sujeto']} cae a su mínimo de un año: {num(s['ultimo'], s['dec'])} {s['unidad']}.", "bajo", 2.0)
    elif s["frecuencia"] == "mensual" and s["cambios"]["m"] is not None and abs(s["cambios"]["m"]) >= 0.35:
        aviso("mes", frase_cambio(s, "m") + ".", "medio", 2.2 + abs(s["cambios"]["m"]))
    elif s["frecuencia"] == "anual" and s.get("salto") is not None and abs(s["salto"]) >= 3:
        aviso("ano", f"{s['sujeto']} cambia de ritmo: {num(abs(s['salto']), 1)} puntos {'más' if s['salto'] > 0 else 'menos'} de subida anual que el año anterior (INE).", "bajo", 1.5)
    return out


# ---------------------------------------------------------------- gasolina

def nombre_provincia(t: str) -> str:
    """«PALMAS (LAS)» -> «Las Palmas»; «BALEARS (ILLES)» -> «Illes Balears»."""
    t = t.strip().title()
    if t.endswith(")") and "(" in t:
        base, art = t[:-1].split("(", 1)
        t = f"{art.strip()} {base.strip()}"
    for a, b in ((" De ", " de "), (" Del ", " del "), (" La ", " la ")):
        t = t.replace(a, b)
    return t

def gasolina() -> tuple[list[dict], dict | None]:
    """Media nacional de hoy (y por provincia) desde las 52 cachés, y su
    histórico diario, que guarda este repositorio."""
    ficheros = [f"carb-{i:02d}.json" for i in range(1, 53)]
    with cf.ThreadPoolExecutor(8) as ex:
        brutos = list(ex.map(lambda f: bajar("proyecciones-gasolina", f), ficheros))

    def precio(t):
        try:
            return float(str(t).replace(",", ".")) if t else None
        except ValueError:
            return None

    g95, gao, provincias, fecha = [], [], [], None
    for b in brutos:
        if not b or not b.get("ListaEESSPrecio"):
            continue
        fecha = fecha or b.get("Fecha")
        lista = b["ListaEESSPrecio"]
        pg = [x for x in (precio(e.get("Precio Gasolina 95 E5")) for e in lista) if x]
        pd = [x for x in (precio(e.get("Precio Gasoleo A")) for e in lista) if x]
        g95 += pg
        gao += pd
        if pg and lista:
            provincias.append({"nombre": nombre_provincia(lista[0].get("Provincia") or ""), "g95": round(sum(pg) / len(pg), 3),
                               "gasoleo": round(sum(pd) / len(pd), 3) if pd else None, "estaciones": len(lista)})
    fichero = HISTORIA / "gasolina.json"
    historia = json.loads(fichero.read_text(encoding="utf-8")) if fichero.exists() else []
    if len(g95) < 1000 or not fecha:
        print("  SALTADA     gasolina (no hay suficientes estaciones)")
        return historia, None
    d, m, a = fecha.split(" ")[0].split("/")
    f_iso = f"{a}-{int(m):02d}-{int(d):02d}"
    hoy = {"f": f_iso, "g95": round(sum(g95) / len(g95), 4), "gasoleo": round(sum(gao) / len(gao), 4), "estaciones": len(g95)}
    historia = [h for h in historia if h["f"] != f_iso] + [hoy]
    historia.sort(key=lambda h: h["f"])
    HISTORIA.mkdir(exist_ok=True)
    fichero.write_text(json.dumps(historia, ensure_ascii=False), encoding="utf-8")
    provincias.sort(key=lambda p: p["g95"])
    print(f"  gasolina    {f_iso}: 95 a {hoy['g95']} y gasóleo a {hoy['gasoleo']} ({len(g95)} estaciones)")
    return historia, {"hoy": hoy, "barata": provincias[0], "cara": provincias[-1], "provincias": len(provincias)}


# ---------------------------------------------------------------- sismos

def sismos() -> dict:
    out = {}
    mundo = bajar("proyecciones-terremotos", "sismos-dia.json")
    if mundo and mundo.get("features"):
        fs = [f for f in mundo["features"] if f["properties"].get("mag") is not None]
        mayor = max(fs, key=lambda f: f["properties"]["mag"])
        out["mundo"] = {"total": len(fs), "mag": mayor["properties"]["mag"], "lugar": mayor["properties"].get("place") or "",
                        "fuertes": sum(1 for f in fs if f["properties"]["mag"] >= 5)}
    espana = bajar("proyecciones-sismos", "sismos-1990-3.0.json")
    if espana and espana.get("features"):
        ahora = dt.datetime.now(dt.timezone.utc).timestamp() * 1000
        mes = [f for f in espana["features"] if f["properties"].get("time") and ahora - f["properties"]["time"] <= 30 * 864e5]
        semana = [f for f in mes if ahora - f["properties"]["time"] <= 7 * 864e5]
        ano = [f for f in espana["features"] if f["properties"].get("time") and ahora - f["properties"]["time"] <= 365 * 864e5]
        out["espana"] = {"mes": len(mes), "ano": len(ano)}
        if mes:
            m = max(mes, key=lambda f: f["properties"].get("mag") or 0)
            out["espana"].update({"mag": m["properties"]["mag"], "lugar": m["properties"].get("place") or "",
                                  "fecha": dt.datetime.fromtimestamp(m["properties"]["time"] / 1000, dt.timezone.utc).date().isoformat()})
        out["espana"]["semana4"] = [{"mag": f["properties"]["mag"], "lugar": f["properties"].get("place") or ""}
                                    for f in semana if (f["properties"].get("mag") or 0) >= 4]
    return out


# ---------------------------------------------------------------- HTML

def esc(t) -> str:
    return html.escape(str(t), quote=True)


def spark_svg(valores, subiendo: bool) -> str:
    if len(valores) < 2:
        return ""
    lo, hi = min(valores), max(valores)
    hi = hi if hi > lo else lo + 1
    n = len(valores) - 1
    pts = " ".join(f"{i / n * 100:.1f},{(1 - (v - lo) / (hi - lo)) * 28 + 2:.1f}" for i, v in enumerate(valores))
    return (f'<svg class="hoy-spark {"sube" if subiendo else "baja"}" viewBox="0 0 100 32" preserveAspectRatio="none" aria-hidden="true">'
            f'<polyline points="{pts}"/></svg>')


def chip(s: dict, clave: str, etiqueta: str) -> str:
    v = s["cambios"].get(clave)
    if v is None:
        return ""
    txt = (num(v, 1) + " %") if s["tipo"] == "precio" else (num(v, 2) + " pt")
    if v > 0:
        txt = "+" + txt
    return f'<span class="hoy-chip {"sube" if v > 0 else "baja" if v < 0 else ""}"><small>{etiqueta}</small>{esc(txt)}</span>'


def ficha(s: dict) -> str:
    principal = "d" if s["frecuencia"] == "diaria" else "m" if s["frecuencia"] == "mensual" else "a"
    ref = s["cambios"].get("m") if s["frecuencia"] == "diaria" else s["cambios"].get(principal)
    unidad = "" if s["unidad"] in ("%", "% anual") else " " + s["unidad"]
    valor = num(s["ultimo"], s["dec"]) + ("%" if s["unidad"] in ("%", "% anual") else "") + unidad
    chips = (chip(s, "d", "día") + chip(s, "s", "semana") + chip(s, "m", "mes") + chip(s, "a", "año")) if s["frecuencia"] == "diaria" \
        else (chip(s, "m", "mes") + chip(s, "a", "año")) if s["frecuencia"] == "mensual" else ""
    return (f'<a class="hoy-ficha{" viejo" if not s["fresco"] else ""}" href="{esc(s["url"])}">'
            f'<span class="hoy-nombre">{esc(s["nombre"])}</span>'
            f'<span class="hoy-valor">{esc(valor)}</span>'
            f'{spark_svg(s["spark"], (ref or 0) >= 0)}'
            f'<span class="hoy-chips">{chips}</span>'
            f'<span class="hoy-fecha">{esc(fecha_larga(s["fecha"]))}</span></a>')


def pagina_hoy(resumen: dict, gas: dict | None, sis: dict) -> str:
    series = resumen["series"]
    hoy = dt.date.today()
    dias = ["lunes", "martes", "miércoles", "jueves", "viernes", "sábado", "domingo"]
    titulo_fecha = f"{dias[hoy.weekday()].capitalize()}, {fecha_larga(hoy.isoformat())}"

    destacados = "".join(f'<li><a href="{esc(d["url"])}">{esc(d["texto"])}</a></li>' for d in resumen["destacados"])
    avisos = "".join(f'<li class="nivel-{esc(a["nivel"])}"><a href="{esc(a["url"])}">{esc(a["texto"])}</a></li>' for a in resumen["avisos"])

    grupos = []
    for g in GRUPOS:
        fichas = [ficha(s) for s in series if s["grupo"] == g]
        extra = ""
        if g == "Carburantes" and gas:
            extra = (f'<p class="hoy-nota">La más barata hoy: <strong>{esc(gas["barata"]["nombre"])}</strong> '
                     f'({num(gas["barata"]["g95"], 3)} €/l la 95). La más cara: <strong>{esc(gas["cara"]["nombre"])}</strong> '
                     f'({num(gas["cara"]["g95"], 3)} €/l). Media de {num(gas["hoy"]["estaciones"])} gasolineras.</p>')
        if fichas:
            grupos.append(f'<section class="hoy-grupo"><h2>{esc(g)}</h2><div class="hoy-rejilla">{"".join(fichas)}</div>{extra}</section>')

    tierra = []
    if sis.get("mundo"):
        m = sis["mundo"]
        tierra.append(f'<a class="hoy-ficha" href="{esc(sitio("proyecciones-terremotos"))}"><span class="hoy-nombre">Terremotos en el mundo, 24 h</span>'
                      f'<span class="hoy-valor">{num(m["total"])}</span><span class="hoy-texto">El mayor, de magnitud {num(m["mag"], 1)}: {esc(m["lugar"])}. '
                      f'{num(m["fuertes"])} de magnitud 5 o más.</span></a>')
    if sis.get("espana"):
        e = sis["espana"]
        mayor = f' El mayor, de {num(e["mag"], 1)} el {esc(fecha_larga(e["fecha"]))}: {esc(e["lugar"])}.' if e.get("mag") else ""
        tierra.append(f'<a class="hoy-ficha" href="{esc(sitio("proyecciones-sismos"))}"><span class="hoy-nombre">Sismos de 3 o más en España, 30 días</span>'
                      f'<span class="hoy-valor">{num(e["mes"])}</span><span class="hoy-texto">{num(e["ano"])} en el último año.{mayor}</span></a>')
    if tierra:
        grupos.append(f'<section class="hoy-grupo"><h2>Sismos</h2><div class="hoy-rejilla">{"".join(tierra)}</div></section>')

    descripcion = "Lo más llamativo de los datos públicos de hoy: bolsa, petróleo, euro, bitcoin, bonos, vivienda, gasolina y terremotos, en una sola página."
    return f"""<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
<title>España en datos hoy: bolsa, gasolina, euro, vivienda y más</title>
<meta name="description" content="{esc(descripcion)}">
<link rel="canonical" href="{HUB}hoy/">
<meta property="og:type" content="website">
<meta property="og:title" content="España en datos hoy">
<meta property="og:description" content="{esc(descripcion)}">
<meta property="og:locale" content="es_ES">
<meta property="og:image" content="{HUB}estatico/og.png">
<meta property="og:url" content="{HUB}hoy/">
<meta name="twitter:card" content="summary_large_image">
<meta name="robots" content="index, follow, max-image-preview:large">
<meta name="color-scheme" content="light">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Barlow+Condensed:wght@500;600;700&family=Barlow:wght@400;500;600&display=swap" rel="stylesheet">
<link rel="stylesheet" href="../estatico/estilo.css">
<link rel="stylesheet" href="../estatico/portada.css">
</head>
<body>
<nav class="barra" aria-label="Secciones">
  <a class="marca" href="../">Proyecciones</a>
  <div class="enlaces"><a href="./" aria-current="page">Hoy</a><a href="../comparar/">Comparar</a>{"".join(f'<a href="{esc(sitio(r))}">{esc(t)}</a>' for r, t in MENU_CORTO)}</div>
</nav>
<main class="marco">
<h1>España en datos hoy</h1>
<p class="bajada">{esc(titulo_fecha)}. Lo más llamativo de las once páginas de Proyecciones, con el último dato de cada fuente.</p>
<div id="desde-visita"></div>
<section class="hoy-destacados"><h2>Lo más llamativo</h2><ol>{destacados}</ol></section>
{f'<section class="hoy-avisos"><h2>Avisos</h2><ul>{avisos}</ul></section>' if avisos else ''}
{"".join(grupos)}
<p class="hoy-comparar"><a class="boton" href="../comparar/">Compara series entre sí</a></p>
<footer class="pie">
<p>Generado el {esc(fecha_larga(hoy.isoformat()))} a partir de los datos que guarda cada página. Los cambios son frente al último dato publicado; las series sin datos recientes salen en gris.</p>
</footer>
</main>
<script src="../estatico/avisos.js" data-pagina="hoy" defer></script>
</body>
</html>
"""


MENU_CORTO = [("proyecciones-bolsa", "Bolsa"), ("proyecciones-materias-primas", "Materias primas"), ("proyecciones-divisas", "Divisas"),
              ("proyecciones-bitcoin", "Bitcoin"), ("proyecciones-bonos", "Bonos"), ("proyecciones-vivienda", "Vivienda"),
              ("proyecciones-alquiler", "Alquiler"), ("proyecciones-gasolina", "Gasolina"), ("proyecciones-supermercado", "Supermercado"),
              ("proyecciones-terremotos", "Terremotos"), ("proyecciones-sismos", "Sismos en España")]


# ---------------------------------------------------------------- principal

def recortar(puntos):
    """Para el comparador: diario los últimos tres años y, antes, el último dato de cada mes."""
    if not puntos:
        return []
    corte = (dt.date.fromisoformat(puntos[-1][0]) - dt.timedelta(days=3 * 365)).isoformat()
    viejos, recientes = [p for p in puntos if p[0] < corte], [p for p in puntos if p[0] >= corte]
    por_mes = {}
    for f, v in viejos:
        por_mes[f[:7]] = (f, v)
    return [[f, round(v, 6)] for f, v in list(por_mes.values()) + recientes]


def main() -> None:
    print("Construyendo: portada (hoy, comparar y avisos)\n")
    cfgs = [dict(zip(("id", "repo", "fichero", "nombre", "sujeto", "grupo", "unidad", "tipo", "dec"), s)) for s in SERIES]
    with cf.ThreadPoolExecutor(8) as ex:
        brutos = list(ex.map(lambda c: bajar(c["repo"], c["fichero"]), cfgs))

    (DATOS / "series").mkdir(parents=True, exist_ok=True)
    series = []
    for cfg, bruto in zip(cfgs, brutos):
        puntos = a_puntos(bruto)
        if len(puntos) < 3:
            print(f"  SALTADA     {cfg['id']}")
            continue
        info = analizar(cfg, puntos)
        series.append(info)
        (DATOS / "series" / f"{cfg['id']}.json").write_text(json.dumps({"id": cfg["id"], "puntos": recortar(puntos)}, ensure_ascii=False), encoding="utf-8")
        print(f"  serie       {cfg['id']:<10} {info['fecha']}  {info['ultimo']}")

    historia, gas = gasolina()
    if len(historia) >= 1:
        for clave, nombre, sujeto in (("g95", "Gasolina 95", "La gasolina 95"), ("gasoleo", "Gasóleo A", "El gasóleo")):
            pts = [(h["f"], h[clave]) for h in historia if h.get(clave)]
            cfg = {"id": clave, "repo": "proyecciones-gasolina", "nombre": nombre, "sujeto": sujeto, "grupo": "Carburantes", "unidad": "€/l", "tipo": "precio", "dec": 3}
            info = analizar(cfg, pts) if len(pts) >= 2 else None
            if info is None:
                f, v = pts[-1]
                info = {"id": clave, "nombre": nombre, "sujeto": sujeto, "grupo": "Carburantes", "unidad": "€/l", "tipo": "precio", "dec": 3,
                        "pagina": cfg["repo"], "url": sitio(cfg["repo"]), "frecuencia": "diaria", "fecha": f, "ultimo": v,
                        "cambios": {"d": None, "s": None, "m": None, "a": None}, "alto52": v, "bajo52": v, "maxhist": v,
                        "fresco": True, "spark": [v], "z": {"d": 0, "s": 0, "m": 0}, "puntuacion": 0}
            else:
                # en gasolina, el aviso es por céntimos, que es como se nota en el surtidor
                info["z"] = {"d": 0, "s": 0, "m": 0}
                info["puntuacion"] = 0
                s7 = valor_en(pts, dt.date.fromisoformat(pts[-1][0]) - dt.timedelta(days=7))
                if s7 and abs(pts[-1][1] - s7[1]) >= 0.03:
                    info["puntuacion"] = 2.4 + abs(pts[-1][1] - s7[1]) * 20
                    info["aviso_cent"] = round((pts[-1][1] - s7[1]) * 100, 1)
            series.append(info)
            (DATOS / "series" / f"{clave}.json").write_text(json.dumps({"id": clave, "puntos": [[f, v] for f, v in pts]}, ensure_ascii=False), encoding="utf-8")

    sis = sismos()

    avisos = []
    for s in series:
        avisos += avisos_de(s)
        if s.get("aviso_cent"):
            c = s["aviso_cent"]
            avisos.append({"id": f"{s['id']}-semana-{s['fecha']}", "serie": s["id"], "pagina": s["pagina"], "url": s["url"],
                           "texto": f"{s['sujeto']} {'sube' if c > 0 else 'baja'} {num(abs(c), 1)} céntimos por litro en una semana.",
                           "nivel": "medio", "fecha": s["fecha"], "puntuacion": s["puntuacion"]})
    if sis.get("mundo") and sis["mundo"]["mag"] >= 6.5:
        m = sis["mundo"]
        avisos.append({"id": f"terremoto-{dt.date.today().isoformat()}", "serie": None, "pagina": "proyecciones-terremotos", "url": sitio("proyecciones-terremotos"),
                       "texto": f"Terremoto de magnitud {num(m['mag'], 1)} en las últimas 24 horas: {m['lugar']}.", "nivel": "alto", "fecha": dt.date.today().isoformat(), "puntuacion": 3 + m["mag"] - 6.5})
    for q in (sis.get("espana") or {}).get("semana4", []):
        avisos.append({"id": f"sismo-es-{q['lugar']}-{q['mag']}", "serie": None, "pagina": "proyecciones-sismos", "url": sitio("proyecciones-sismos"),
                       "texto": f"Sismo de magnitud {num(q['mag'], 1)} esta semana en España: {q['lugar']}.", "nivel": "medio", "fecha": dt.date.today().isoformat(), "puntuacion": 2.5})
    avisos.sort(key=lambda a: -a["puntuacion"])
    # como mucho dos avisos por página, para que no se repitan (los bonos se mueven juntos)
    por_pagina = {}
    avisos = [a for a in avisos if por_pagina.setdefault(a["pagina"], []).append(a) or len(por_pagina[a["pagina"]]) <= 2]

    # lo más llamativo: las series que más se salen de lo normal, como mucho una por grupo
    destacados, usados = [], set()
    for s in sorted(series, key=lambda s: -s["puntuacion"]):
        if s["grupo"] in usados or not s["fresco"]:
            continue
        usados.add(s["grupo"])
        texto = frase_destacada(s) if not s.get("aviso_cent") else f"{s['sujeto']} {'sube' if s['aviso_cent'] > 0 else 'baja'} {num(abs(s['aviso_cent']), 1)} céntimos por litro en una semana."
        destacados.append({"serie": s["id"], "url": s["url"], "texto": texto})
        if len(destacados) == 5:
            break
    if gas and len(destacados) < 6:
        destacados.append({"serie": "g95", "url": sitio("proyecciones-gasolina"),
                           "texto": f"Llenar el depósito: la gasolina 95 está a {num(gas['hoy']['g95'], 3)} €/l de media y el gasóleo a {num(gas['hoy']['gasoleo'], 3)} €/l."})
    if sis.get("mundo") and len(destacados) < 7:
        m = sis["mundo"]
        destacados.append({"serie": None, "url": sitio("proyecciones-terremotos"),
                           "texto": f"En las últimas 24 horas ha habido {num(m['total'])} terremotos en el mundo; el mayor, de magnitud {num(m['mag'], 1)}."})

    resumen = {
        "generado": dt.datetime.now(dt.timezone.utc).isoformat(timespec="minutes"),
        "series": series, "avisos": avisos[:12], "destacados": destacados,
        "gasolina": gas, "sismos": sis,
    }
    (DATOS / "resumen.json").write_text(json.dumps(resumen, ensure_ascii=False), encoding="utf-8")
    (DOCS / "hoy").mkdir(exist_ok=True)
    (DOCS / "hoy" / "index.html").write_text(pagina_hoy(resumen, gas, sis), encoding="utf-8")
    print(f"\n  {len(series)} series, {len(avisos)} avisos, {len(destacados)} destacados.\nListo.")


if __name__ == "__main__":
    main()
