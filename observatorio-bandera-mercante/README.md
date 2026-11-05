# Observatorio de Bandera Mercante

Tablero público que muestra qué banderas mueven la carga en aguas argentinas y cuánto cabotaje hacen los buques extranjeros. Se actualiza solo, gratis, con GitHub Pages y GitHub Actions:

| Parte | Fuente | Frecuencia |
|---|---|---|
| Foto del tráfico por bandera (mapa y conteos) | AIS en tiempo real, aisstream.io | Cada hora |
| Mercantes argentinos vs. extranjeros, foto a foto | La misma foto, acumulada en `data/historial.csv` | Cada hora |
| Cabotaje costero con bandera extranjera, últimos 60 días | Global Fishing Watch (unas 72 h de demora) | Cada día, 06:41 hora argentina |
| Serie larga 2012-2025 | Anexo 2 de la ponencia | Fija |
| Tráfico en vivo | Mapa incrustado de VesselFinder | Tiempo real |

## Puesta en marcha (unos 20 minutos, una sola vez)

### 1. Crear las cuentas y las claves
1. **GitHub**: creá una cuenta gratuita en https://github.com.
2. **Global Fishing Watch**: en https://globalfishingwatch.org/our-apis/tokens creá un token **nuevo**. El anterior quedó visible en una captura, así que conviene borrarlo y no usarlo.
3. **aisstream.io**: entrá a https://aisstream.io, iniciá sesión (se puede con la cuenta de GitHub) y creá una API key. Al momento de escribir esto el servicio no cobra; confirmalo al crear la clave.

### 2. Crear el repositorio y subir los archivos
1. En GitHub: **New repository** → nombre `observatorio-bandera-mercante` → **Public** (tiene que ser público para que Pages y Actions sean gratis sin límite de minutos) → **Create repository**.
2. En la página del repositorio vacío: **uploading an existing file** → arrastrá **todo el contenido** de esta carpeta (incluida la carpeta oculta `.github`; si tu explorador no la muestra, activá "mostrar archivos ocultos") → **Commit changes**.

### 3. Cargar las claves como secretos
**Settings → Secrets and variables → Actions → New repository secret**, dos veces:
- Nombre `GFW_TOKEN`, valor: el token de Global Fishing Watch.
- Nombre `AISSTREAM_KEY`, valor: la API key de aisstream.

Las claves quedan cifradas: nunca aparecen en la página pública.

### 4. Permitir que los procesos guarden datos
**Settings → Actions → General → Workflow permissions** → **Read and write permissions** → **Save**.

### 5. Publicar la página
**Settings → Pages** → **Source: Deploy from a branch** → **Branch: main**, carpeta **/ (root)** → **Save**. En uno o dos minutos la página queda en `https://TU-USUARIO.github.io/observatorio-bandera-mercante/`.

### 6. Correr los procesos por primera vez
**Actions** → elegí **Foto horaria del tráfico (AIS)** → **Run workflow**. Repetí con **Cabotaje diario (Global Fishing Watch)** (tarda más: entre 5 y 30 minutos). Cuando terminen en verde, recargá la página. Desde ahí siguen solos.

## Qué hace cada archivo
- `index.html`: la página pública.
- `scripts/snapshot_ais.py`: escucha el AIS 4 minutos sobre cuatro zonas (Paraná y Río de la Plata, costa bonaerense, Patagonia norte y sur), guarda `data/snapshot.json` y suma una fila a `data/historial.csv`.
- `scripts/cabotaje_gfw.py`: busca buques extranjeros con escalas seguidas en dos puertos argentinos y un extremo en la Patagonia, verifica que no hayan pasado por el exterior y guarda `data/cabotaje_reciente.json`.
- `scripts/comun.py`: tabla de banderas por código MID, tipos de buque AIS, zonas y coordenadas de puertos.
- `.github/workflows/`: los dos procesos automáticos.
- `data/*_2012_2025.json`: la serie larga de la ponencia.

## Si algo falla
- **Un proceso termina en rojo**: abrilo en **Actions** y leé el último paso. "Falta el secreto…" significa que el nombre del secreto no coincide. Un "401" indica que el token o la clave son incorrectos.
- **La foto trae pocos buques**: aisstream usa antenas terrestres de voluntarios y hay zonas sin cobertura. Podés escuchar más tiempo cambiando `SEGUNDOS_ESCUCHA` en el workflow (por ejemplo, `env: SEGUNDOS_ESCUCHA: "480"`).
- **El cabotaje sale vacío algún día**: es posible en 60 días con poco tráfico costero, o si Global Fishing Watch todavía no publicó las escalas recientes (72 h de demora).

## Cómo leer los datos
Son movimientos observados, no waivers otorgados: incluyen buques con tratamiento de bandera nacional (Decreto 1010/04, Ley 27.419). La serie oficial de excepciones (art. 6° del Decreto-Ley 19.492/44, Res. ANPyN 41/2025) sólo puede obtenerse de la ANPyN por la Ley 27.275.

Cita sugerida: «Observatorio de Bandera Mercante, elaboración propia sobre AIS (aisstream.io; Global Fishing Watch)».

Ponencia de origen: «Logística fluvial y soberanía económica: la Hidrovía Paraná-Paraguay, la marina mercante argentina y la fuga de divisas por fletes» (Universidad Nacional de Lanús, 2026).
