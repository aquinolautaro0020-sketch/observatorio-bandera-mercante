"""Cabotaje costero con bandera extranjera en los últimos 60 días (Global Fishing Watch, ~72 h de demora).

Misma metodología que el anexo 2 de la ponencia:
  1. Escalas en puertos del litoral argentino (buques de carga).
  2. Tramo doméstico: escala ARG seguida de otra escala ARG distinta, ≤ 12 días, buque de bandera extranjera.
  3. Verificación con el historial mundial del buque (descarta escalas intermedias en el exterior).
  4. Se conservan los tramos con un extremo en la Patagonia.
Escribe data/cabotaje_reciente.json. Requiere la variable de entorno GFW_TOKEN (secreto del repositorio).
"""
import json, os, sys, time
from datetime import datetime, timedelta, timezone
from pathlib import Path

import requests

sys.path.insert(0, str(Path(__file__).parent))
from comun import PATAGONIA, coordenadas, zona  # noqa: E402

RAIZ = Path(__file__).resolve().parent.parent
BASE = "https://gateway.api.globalfishingwatch.org/v3"
DS = "public-global-port-visits-events:latest"
DIAS = int(os.environ.get("DIAS_VENTANA", "60"))
CONF_MIN, MAX_DIAS, LIMIT = 3, 12, 200
POLIGONO = {"type": "Polygon", "coordinates": [[[-69.5, -56.0], [-53.0, -56.0], [-53.0, -22.0], [-69.5, -22.0], [-69.5, -56.0]]]}


def sesion(token):
    s = requests.Session()
    s.headers.update({"Authorization": f"Bearer {token}", "Content-Type": "application/json"})
    return s


def pedir(s, metodo, url, **kw):
    for intento in range(6):
        try:
            r = s.request(metodo, url, timeout=180, **kw)
        except requests.RequestException:
            time.sleep(5 * (intento + 1)); continue
        if r.status_code in (200, 201):
            return r.json()
        if r.status_code == 429 or r.status_code >= 500:
            time.sleep(min(60, 5 * 2 ** intento)); continue
        raise RuntimeError(f"{r.status_code}: {r.text[:300]}")
    raise RuntimeError("La API de Global Fishing Watch no respondió")


def eventos(s, cuerpo):
    out, off = [], 0
    while True:
        js = pedir(s, "POST", f"{BASE}/events", params={"limit": LIMIT, "offset": off}, json=cuerpo)
        ent = js.get("entries") or []
        out.extend(ent)
        nxt = js.get("nextOffset")
        if not ent or not nxt or nxt <= off:
            return out
        off = nxt


def aplanar(ev):
    pv = ev.get("port_visit") or ev.get("portVisit") or {}
    a = pv.get("intermediateAnchorage") or pv.get("startAnchorage") or pv.get("endAnchorage") or {}
    v = ev.get("vessel") or {}
    return {"id": ev.get("id"), "inicio": ev.get("start"), "fin": ev.get("end"), "buque_id": v.get("id"),
            "mmsi": str(v.get("ssvid") or ""), "nombre": v.get("name"), "bandera": v.get("flag"),
            "tipo": (v.get("type") or "").upper(), "conf": pv.get("confidence") or 0,
            "puerto_id": a.get("id"), "puerto": a.get("name") or a.get("topDestination"), "pais": a.get("flag")}


def extranjero(e):
    if e["bandera"]:
        return e["bandera"].upper() != "ARG"
    return not e["mmsi"].startswith("701")


def tramos(escalas):
    por_buque = {}
    for e in escalas:
        if (e["conf"] or 0) >= CONF_MIN and e["inicio"]:
            por_buque.setdefault(e["buque_id"], []).append(e)
    out = []
    for lista in por_buque.values():
        lista.sort(key=lambda e: e["inicio"])
        for a, b in zip(lista, lista[1:]):
            if a["pais"] != "ARG" or b["pais"] != "ARG" or a["puerto_id"] == b["puerto_id"] or not extranjero(a):
                continue
            dias = (datetime.fromisoformat(b["inicio"].replace("Z", "+00:00")) - datetime.fromisoformat((a["fin"] or a["inicio"]).replace("Z", "+00:00"))).total_seconds() / 86400
            zo, zd = zona(a["puerto"]), zona(b["puerto"])
            if 0 <= dias <= MAX_DIAS and "Sin zona" not in (zo, zd) and (zo in PATAGONIA or zd in PATAGONIA) and "FISHING" not in a["tipo"] and "PASSENGER" not in a["tipo"]:
                out.append({"buque_id": a["buque_id"], "nombre": a["nombre"], "mmsi": a["mmsi"], "bandera": a["bandera"] or "S/D",
                            "origen": a["puerto"], "destino": b["puerto"], "salida": a["fin"], "llegada": b["inicio"], "dias": round(dias, 2)})
    return out


def main():
    token = os.environ.get("GFW_TOKEN", "").strip()
    if not token:
        sys.exit("Falta el secreto GFW_TOKEN.")
    s = sesion(token)
    hoy = datetime.now(timezone.utc).date()
    fin = hoy - timedelta(days=3)          # GFW publica con ~72 h de demora
    ini = fin - timedelta(days=DIAS)
    cuerpo = {"datasets": [DS], "startDate": ini.isoformat(), "endDate": fin.isoformat(), "geometry": POLIGONO}
    filtro = None
    for op in (["cargo", "bunker", "other"], ["CARGO", "BUNKER", "OTHER"]):
        try:
            pedir(s, "POST", f"{BASE}/events", params={"limit": 1, "offset": 0}, json={**cuerpo, "vesselTypes": op})
            filtro = op
            break
        except RuntimeError:
            pass
    if filtro:
        cuerpo["vesselTypes"] = filtro
    escalas = [aplanar(e) for e in eventos(s, cuerpo)]
    prelim = tramos(escalas)
    sospechosos = sorted({t["buque_id"] for t in prelim})
    hist = []
    for i in range(0, len(sospechosos), 20):
        hist += [aplanar(e) for e in eventos(s, {"datasets": [DS], "startDate": (ini - timedelta(days=15)).isoformat(),
                                                    "endDate": fin.isoformat(), "vessels": sospechosos[i:i + 20]})]
    confirmados = tramos(hist) if hist else []
    rutas = {}
    for t in confirmados:
        k = (t["origen"], t["destino"])
        r = rutas.setdefault(k, {"origen": t["origen"], "destino": t["destino"], "tramos": 0, "buques": set()})
        r["tramos"] += 1
        r["buques"].add(t["buque_id"])
    rutas_out = []
    for r in rutas.values():
        lo_o, lo_d = coordenadas(r["origen"]), coordenadas(r["destino"])
        rutas_out.append({"origen": r["origen"], "destino": r["destino"], "tramos": r["tramos"], "buques": len(r["buques"]),
                          "lat_o": lo_o[0], "lon_o": lo_o[1], "lat_d": lo_d[0], "lon_d": lo_d[1]})
    buques = {}
    for t in confirmados:
        b = buques.setdefault(t["buque_id"], {"nombre": t["nombre"], "mmsi": t["mmsi"], "bandera": t["bandera"], "tramos": 0})
        b["tramos"] += 1
    salida = {
        "generado_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "ventana": {"desde": ini.isoformat(), "hasta": fin.isoformat(), "dias": DIAS},
        "nota": "Global Fishing Watch publica las escalas con unas 72 horas de demora.",
        "totales": {"escalas_descargadas": len(escalas), "tramos_costeros": len(confirmados), "buques_extranjeros": len(buques),
                    "buques_recurrentes_4_o_mas": sum(1 for b in buques.values() if b["tramos"] >= 4)},
        "buques": sorted(buques.values(), key=lambda b: -b["tramos"]),
        "rutas": sorted(rutas_out, key=lambda r: -r["tramos"]),
        "tramos": sorted(confirmados, key=lambda t: t["llegada"] or "", reverse=True)[:500],
    }
    (RAIZ / "data").mkdir(exist_ok=True)
    (RAIZ / "data" / "cabotaje_reciente.json").write_text(json.dumps(salida, ensure_ascii=False), encoding="utf-8")
    print(json.dumps(salida["totales"], ensure_ascii=False))


def estado(ok, detalle):
    (RAIZ / "data").mkdir(exist_ok=True)
    (RAIZ / "data" / "estado_cabotaje.json").write_text(json.dumps({
        "ok": ok, "detalle": detalle, "fecha_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")},
        ensure_ascii=False, indent=1), encoding="utf-8")


if __name__ == "__main__":
    try:
        main()
        estado(True, "Cálculo completo")
    except SystemExit as e:
        estado(False, str(e))
        print(f"::error title=Cabotaje diario::{e}")
        raise
    except Exception as e:  # noqa: BLE001  se informa cualquier falla, con su tipo
        msg = f"{type(e).__name__}: {e}"
        if "401" in msg:
            msg += " — revisá el secreto GFW_TOKEN (copiá el token con el botón de copiar)."
        estado(False, msg)
        print(f"::error title=Cabotaje diario::{msg}")
        sys.exit(1)
