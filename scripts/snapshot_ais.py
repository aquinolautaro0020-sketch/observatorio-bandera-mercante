"""Foto horaria de los buques en aguas argentinas (AIS en tiempo real vía aisstream.io).

Se conecta al stream unos minutos, guarda la última posición de cada buque y su bandera
(por el código MID del MMSI) y escribe:
  data/snapshot.json   -> buques presentes ahora (lo dibuja el mapa de la página)
  data/historial.csv   -> una fila por corrida con los conteos (serie que crece sola)
Requiere la variable de entorno AISSTREAM_KEY (secreto del repositorio).
"""
import asyncio, csv, json, os, sys, time
from datetime import datetime, timezone
from pathlib import Path

import websockets

sys.path.insert(0, str(Path(__file__).parent))
from comun import bandera_por_mmsi, tipo_ais  # noqa: E402

RAIZ = Path(__file__).resolve().parent.parent
URL = "wss://stream.aisstream.io/v0/stream"
SEGUNDOS = int(os.environ.get("SEGUNDOS_ESCUCHA", "540"))  # los datos de tipo llegan cada ~6 min
TIPOS = RAIZ / "data" / "tipos_conocidos.json"
# Cajas [[lat, lon], [lat, lon]] sobre aguas argentinas: Paraná y Río de la Plata, costa bonaerense, Patagonia norte y sur
CAJAS = [
    [[-27.0, -61.5], [-35.2, -56.8]],
    [[-35.2, -63.0], [-41.5, -56.0]],
    [[-41.5, -66.5], [-48.5, -58.0]],
    [[-48.5, -70.0], [-55.5, -62.0]],
]


async def escuchar(clave, segundos):
    buques = {}
    fin = time.time() + segundos
    async with websockets.connect(URL, open_timeout=30, ping_interval=20) as ws:
        await ws.send(json.dumps({
            "APIKey": clave,
            "BoundingBoxes": CAJAS,
            "FilterMessageTypes": ["PositionReport", "ShipStaticData", "StandardClassBPositionReport"],
        }))
        while time.time() < fin:
            try:
                crudo = await asyncio.wait_for(ws.recv(), timeout=max(1, fin - time.time()))
            except asyncio.TimeoutError:
                break
            except websockets.exceptions.ConnectionClosed as e:
                if buques:
                    break
                sys.exit(f"aisstream cerró la conexión antes de enviar datos (código {e.code}: {e.reason or 'sin detalle'}). "
                         "Revisá que el secreto AISSTREAM_KEY tenga la clave correcta.")
            msg = json.loads(crudo)
            if isinstance(msg, dict) and msg.get("error"):
                sys.exit(f"aisstream rechazó la conexión: {msg['error']}. Revisá el secreto AISSTREAM_KEY.")
            procesar(msg, buques)
    return buques


def procesar(msg, buques):
    meta = msg.get("MetaData") or {}
    mmsi = str(meta.get("MMSI") or "")
    if not mmsi:
        return
    b = buques.setdefault(mmsi, {"mmsi": mmsi, "bandera": bandera_por_mmsi(mmsi), "tipo": "Sin dato"})
    nombre = (meta.get("ShipName") or "").strip()
    if nombre:
        b["nombre"] = nombre
    tipo = msg.get("MessageType")
    cuerpo = (msg.get("Message") or {}).get(tipo) or {}
    if tipo == "ShipStaticData":
        b["tipo"] = tipo_ais(cuerpo.get("Type"))
        if cuerpo.get("ImoNumber"):
            b["imo"] = cuerpo.get("ImoNumber")
        if cuerpo.get("Destination"):
            b["destino"] = str(cuerpo.get("Destination")).strip()
    else:
        lat = meta.get("latitude", cuerpo.get("Latitude"))
        lon = meta.get("longitude", cuerpo.get("Longitude"))
        if lat is not None and lon is not None:
            b["lat"], b["lon"] = round(float(lat), 4), round(float(lon), 4)
            b["velocidad"] = cuerpo.get("Sog")
            b["hora_utc"] = meta.get("time_utc")


def completar_tipos(buques):
    """Usa y actualiza la memoria de tipos de buque (MMSI -> tipo) entre corridas."""
    try:
        conocidos = json.loads(TIPOS.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        conocidos = {}
    for mmsi, b in buques.items():
        if b["tipo"] != "Sin dato":
            conocidos[mmsi] = b["tipo"]
        elif mmsi in conocidos:
            b["tipo"] = conocidos[mmsi]
    TIPOS.parent.mkdir(exist_ok=True)
    TIPOS.write_text(json.dumps(conocidos, ensure_ascii=False, sort_keys=True), encoding="utf-8")


def resumir(buques, ahora):
    con_pos = [b for b in buques.values() if "lat" in b]
    mercantes = [b for b in con_pos if b["tipo"] in ("Carga", "Tanque")]
    arg = [b for b in mercantes if b["bandera"] == "ARG"]
    ext = [b for b in mercantes if b["bandera"] not in ("ARG", "S/D")]
    por_bandera = {}
    for b in mercantes:
        por_bandera[b["bandera"]] = por_bandera.get(b["bandera"], 0) + 1
    return {
        "generado_utc": ahora,
        "segundos_escucha": SEGUNDOS,
        "totales": {"buques_con_posicion": len(con_pos), "mercantes": len(mercantes),
                    "sin_tipo_identificado": sum(1 for b in con_pos if b["tipo"] == "Sin dato"),
                    "mercantes_bandera_argentina": len(arg), "mercantes_bandera_extranjera": len(ext)},
        "por_bandera": dict(sorted(por_bandera.items(), key=lambda kv: -kv[1])),
        "buques": sorted(con_pos, key=lambda b: (b["tipo"] not in ("Carga", "Tanque"), b["bandera"] == "ARG")),
    }


def guardar(resumen):
    (RAIZ / "data").mkdir(exist_ok=True)
    (RAIZ / "data" / "snapshot.json").write_text(json.dumps(resumen, ensure_ascii=False), encoding="utf-8")
    hist = RAIZ / "data" / "historial.csv"
    nuevo = not hist.exists()
    t = resumen["totales"]
    with hist.open("a", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        if nuevo:
            w.writerow(["fecha_utc", "buques_con_posicion", "mercantes", "mercantes_bandera_argentina", "mercantes_bandera_extranjera"])
        w.writerow([resumen["generado_utc"], t["buques_con_posicion"], t["mercantes"],
                    t["mercantes_bandera_argentina"], t["mercantes_bandera_extranjera"]])


def main():
    clave = os.environ.get("AISSTREAM_KEY", "").strip()
    if not clave:
        sys.exit("Falta el secreto AISSTREAM_KEY: crealo en Settings → Secrets and variables → Actions, con ese nombre exacto.")
    ahora = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    try:
        buques = asyncio.run(escuchar(clave, SEGUNDOS))
    except (OSError, asyncio.TimeoutError, websockets.exceptions.InvalidStatusCode, websockets.exceptions.InvalidHandshake) as e:
        sys.exit(f"No se pudo conectar con aisstream.io ({type(e).__name__}: {e}). Si se repite, revisá la clave o el estado del servicio.")
    if not buques:
        print("Aviso: aisstream no envió ningún buque en la ventana de escucha; se guarda una foto vacía.")
    completar_tipos(buques)
    resumen = resumir(buques, ahora)
    guardar(resumen)
    print(json.dumps(resumen["totales"], ensure_ascii=False))


if __name__ == "__main__":
    main()
