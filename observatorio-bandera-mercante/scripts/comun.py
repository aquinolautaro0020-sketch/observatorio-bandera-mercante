"""Tablas y funciones compartidas por los scripts del observatorio."""

# Código MID (primeros 3 dígitos del MMSI) -> bandera ISO-3. Lista de la UIT, banderas más frecuentes en la región.
MID = {}
_tabla = {
    "ARG": ["701"], "BRA": ["710"], "BOL": ["720"], "CHL": ["725"], "COL": ["730"], "ECU": ["735"],
    "PRY": ["755"], "PER": ["760"], "URY": ["770"], "VEN": ["775"],
    "PAN": ["351", "352", "353", "354", "355", "356", "357", "370", "371", "372", "373", "374"],
    "LBR": ["636", "637"], "MHL": ["538"], "MLT": ["215", "229", "248", "249", "256"],
    "CYP": ["209", "210", "212"], "BHS": ["308", "309", "311"], "ATG": ["304", "305"],
    "HKG": ["477"], "SGP": ["563", "564", "565", "566"], "GRC": ["237", "239", "240", "241"],
    "PRT": ["255", "263"], "NOR": ["257", "258", "259"], "NLD": ["244", "245", "246"],
    "DEU": ["211", "218"], "DNK": ["219", "220"], "ESP": ["224", "225"], "FRA": ["226", "227", "228"],
    "GBR": ["232", "233", "234", "235"], "GIB": ["236"], "ITA": ["247"], "BEL": ["205"], "IRL": ["250"],
    "ISL": ["251"], "LUX": ["253"], "POL": ["261"], "SWE": ["265", "266"], "FIN": ["230"], "FRO": ["231"],
    "TUR": ["271"], "UKR": ["272"], "RUS": ["273"], "BLZ": ["312"], "BRB": ["314"], "CAN": ["316"],
    "CYM": ["319"], "KNA": ["341"], "MEX": ["345"], "USA": ["338", "366", "367", "368", "369"],
    "VCT": ["375", "376", "377"], "SAU": ["403"], "CHN": ["412", "413", "414"], "TWN": ["416"],
    "IND": ["419"], "IRN": ["422"], "JPN": ["431", "432"], "KOR": ["440", "441"], "ARE": ["470", "471"],
    "AUS": ["503"], "NZL": ["512"], "COK": ["518"], "IDN": ["525"], "MYS": ["533"], "PHL": ["548"],
    "THA": ["567"], "TUV": ["572"], "VNM": ["574"], "VUT": ["576", "577"], "ZAF": ["601"],
    "COM": ["620"], "SLE": ["667"], "TGO": ["671"],
}
for iso, mids in _tabla.items():
    for m in mids:
        MID[m] = iso


def bandera_por_mmsi(mmsi):
    s = str(mmsi or "")
    if len(s) != 9:
        return "S/D"
    return MID.get(s[:3], "OTR")


def tipo_ais(codigo):
    """Tipo de buque según el código AIS (ShipType)."""
    try:
        c = int(codigo)
    except (TypeError, ValueError):
        return "Sin dato"
    if 70 <= c <= 79:
        return "Carga"
    if 80 <= c <= 89:
        return "Tanque"
    if 60 <= c <= 69:
        return "Pasajeros"
    if c == 30:
        return "Pesquero"
    if c in (31, 32, 52):
        return "Remolque / empuje"
    return "Otro"


# Zonas portuarias (mismas reglas que el anexo 2 de la ponencia)
ZONAS = {
    "Patagonia petrolera": ["CALETA OLIVIA", "COMODORO", "PUNTA LOYOLA", "CALETA CORDOVA", "RIO GALLEGOS", "SAN JULIAN"],
    "Patagonia / Tierra del Fuego": ["USHUAIA", "RIO GRANDE", "MADRYN", "SAN ANTONIO", "DESEADO", "PUNTA QUILLA", "SANTA CRUZ"],
    "Sur bonaerense": ["BAHIA BLANCA", "WHITE", "ROSALES", "GALVAN", "NECOCHEA", "QUEQUEN", "MAR DEL PLATA"],
    "Río de la Plata": ["BUENOS AIRES", "DOCK SUD", "LA PLATA", "ENSENADA", "BERISSO"],
    "Up-River / Paraná": ["ROSARIO", "SAN LORENZO", "TIMBUES", "SAN MARTIN", "SAN NICOLAS", "VILLA CONSTITUCION",
                          "RAMALLO", "SAN PEDRO", "ZARATE", "CAMPANA", "ESCOBAR", "DIAMANTE", "SANTA FE", "PARANA",
                          "BARRANQUERAS", "CORRIENTES", "ARROYO SECO", "LIMA", "IBICUY", "CONCEPCION", "POSADAS"],
}
PATAGONIA = {"Patagonia petrolera", "Patagonia / Tierra del Fuego"}


def zona(nombre):
    n = (nombre or "").upper()
    for z, claves in ZONAS.items():
        if any(c in n for c in claves):
            return z
    return "Sin zona"


PUERTOS = [("DOCK SUD", -34.64, -58.34), ("BUENOS AIRES", -34.59, -58.37), ("LA PLATA", -34.86, -57.89),
           ("ENSENADA", -34.86, -57.89), ("CAMPANA", -34.17, -58.95), ("ZARATE", -34.10, -59.02), ("ESCOBAR", -34.28, -58.77),
           ("SAN PEDRO", -33.68, -59.65), ("RAMALLO", -33.48, -60.00), ("SAN NICOLAS", -33.33, -60.21),
           ("VILLA CONSTITUCION", -33.24, -60.32), ("ARROYO SECO", -33.15, -60.50), ("ROSARIO", -32.95, -60.63),
           ("SAN LORENZO", -32.74, -60.72), ("TIMBUES", -32.66, -60.75), ("SAN MARTIN", -32.70, -60.73),
           ("SANTA FE", -31.65, -60.70), ("DIAMANTE", -32.06, -60.65), ("PARANA", -31.73, -60.53),
           ("BARRANQUERAS", -27.48, -58.93), ("CORRIENTES", -27.47, -58.84), ("CONCEPCION", -32.48, -58.23),
           ("MAR DEL PLATA", -38.04, -57.53), ("QUEQUEN", -38.58, -58.70), ("NECOCHEA", -38.58, -58.70),
           ("BAHIA BLANCA", -38.79, -62.27), ("WHITE", -38.79, -62.27), ("GALVAN", -38.78, -62.30),
           ("ROSALES", -38.93, -62.07), ("SAN ANTONIO", -40.80, -64.88), ("MADRYN", -42.77, -65.03),
           ("COMODORO", -45.86, -67.47), ("CALETA CORDOVA", -45.72, -67.37), ("CALETA OLIVIA", -46.44, -67.52),
           ("DESEADO", -47.75, -65.90), ("SAN JULIAN", -49.31, -67.72), ("PUNTA QUILLA", -50.12, -68.42),
           ("SANTA CRUZ", -50.12, -68.42), ("PUNTA LOYOLA", -51.61, -69.03), ("RIO GALLEGOS", -51.62, -69.21),
           ("RIO GRANDE", -53.79, -67.70), ("USHUAIA", -54.81, -68.30)]


def coordenadas(nombre):
    n = (nombre or "").upper()
    for k, la, lo in PUERTOS:
        if k in n:
            return la, lo
    return None, None
