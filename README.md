# Kler

Asistente de escritorio para Windows, con activación local por voz, conversación con Gemini, Ollama u OpenRouter y herramientas opcionales.

## Instalación

1. Instala Python 3.12 o 3.11 de 64 bits.
2. Ejecuta `Instalar_Kler.bat`. Crea el entorno, instala las versiones fijadas y descarga el modelo de voz Vosk.
3. Abre `Iniciar Kler Beta.vbs` y entra en **Ajustes** para seleccionar proveedor, micrófono y altavoz.

Instalación manual:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt -c constraints.txt
.\.venv\Scripts\python.exe download_vosk.py
.\.venv\Scripts\python.exe main.py
```

Los componentes de Telegram, notificaciones de Windows y metadatos públicos de TikTok se instalan por separado:

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements-optional.txt -c constraints.txt
```

## Voz y conversación

- Di **Kler** o **oye Kler**. La detección del nombre funciona localmente, aunque el proveedor esté desconectado.
- El modelo español transcribe el nombre aproximadamente como «claire» o «clear»; un detector limitado a esas pronunciaciones lo reconoce sin exigir que la transcripción general escriba Kler.
- El audio anterior a la activación se conserva durante tres segundos para mantener órdenes como «Kler, abre Spotify».
- **Insert** despierta a Kler y detiene la respuesta actual. El botón de micrófono permite silenciar la captura; los cambios visuales nunca quitan ese silencio.
- También puedes escribir órdenes. «Abre Spotify» y «qué hora es» se procesan localmente.
- Tras 20 segundos sin actividad vuelve a esperar el nombre; este plazo se puede ajustar.
- Gemini recibe audio en tiempo real. Ollama y OpenRouter usan transcripción local Vosk y voz instalada en Windows.
- Ollama requiere un servidor y un modelo ya instalados. Si el modelo no admite herramientas, conserva la conversación y las órdenes locales sencillas; comunica esa limitación al modelo.

La precisión depende del micrófono, el ruido, la pronunciación y el modelo de reconocimiento. La aplicación no anuncia una latencia garantizada.

## Herramientas

**Ajustes → Herramientas** permite activar solo las funciones que usas. Se anuncian hasta 21 herramientas por defecto en lugar de cargar todo el catálogo. Los módulos de acciones se importan cuando se necesitan.

Hay operaciones reales para archivos, Git, búsqueda web, conocimiento local, preferencias, tareas y recordatorios. Los resultados de servicios externos requieren conexión y credenciales; los fallos se muestran como errores, no como confirmaciones de éxito.

### Recordatorios y automatizaciones

- Admiten fecha y hora (`date: YYYY-MM-DD`, `time: HH:MM`) o plazos como `10m` y `2h`.
- Se guardan en SQLite, junto con notas y tareas del panel.
- Se ejecutan mientras Kler está abierto. Los avisos pendientes se recuperan al volver a abrirlo.
- Una tarea que se interrumpió durante su ejecución se marca para revisión y no se repite automáticamente.
- Las reglas por frase ejecutan acciones reales; los horarios y recurrencias se gestionan con `scheduler`.
- Las tareas simultáneas y las colas de audio tienen límites.

### Google

Para Gmail, Calendar y Drive:

1. Crea un cliente OAuth de tipo **aplicación de escritorio** y habilita las API necesarias en tu proyecto de Google.
2. Guarda el archivo del cliente en `config/google_credentials.json`.
3. Usa los botones **Conectar Gmail / Calendar / Drive** en Ajustes → Herramientas.
4. Autoriza tu cuenta en el navegador y activa las herramientas correspondientes.

Los tokens se guardan por API en `config/google_tokens/`, excluidos de Git. No se incluye ninguna cuenta ni credencial en el proyecto.

Referencia de autorización: [Google Workspace Python quickstart](https://developers.google.com/workspace/drive/api/quickstart/python).

### Otras integraciones

- **Investigación en segundo plano:** requiere OpenRouter configurado o el proveedor Ollama; permanece fuera del catálogo si falta esa configuración.
- **Imágenes:** requiere una clave Gemini y un modelo de imágenes habilitado para tu cuenta; devuelve las rutas de los archivos que realmente se generaron.
- **Mapas y vuelos:** abren búsquedas reales en el navegador; no inventan rutas, precios ni disponibilidad.
- **Redes sociales:** guardan borradores y abren la plataforma para que los revises y publiques. No confirman publicaciones que no se han enviado.
- **Hogar:** usa Home Assistant con URL y token configurados en Ajustes.
- **TikTok:** obtiene los metadatos públicos que el servicio permita; los campos ausentes no se estiman.
- **ARCA:** la emisión fiscal está deshabilitada porque no hay un backend fiscal autenticado.
- **Código generado:** desactivado por defecto. Un subproceso con límite de tiempo no proporciona aislamiento del sistema; si lo habilitas, ejecuta código con tus permisos.

## Diagnóstico y pruebas

El botón de historial muestra mensajes y errores. `kler.log` rota automáticamente. Los indicadores de respuesta y herramientas muestran tiempos medidos; el clima permanece vacío hasta consultar datos reales. El orbe reduce su frecuencia en espera y se pausa cuando la ventana está oculta.

En Ajustes → Herramientas, **Comprobar instalación** revisa proveedor, modelo de voz y entrada de audio sin mostrar claves.

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
.\.venv\Scripts\python.exe -m pip check
```

Las pruebas usan cuentas, proveedores y dispositivos simulados, junto con almacenamiento y repositorios Git temporales. No envían correos, publican contenido ni graban el micrófono.

## Datos locales

Las claves, los tokens OAuth, la memoria y la base de datos se conservan localmente y están excluidos del repositorio. Los servicios en la nube reciben el contenido de las solicitudes que se les envía. Las notas del panel y los recordatorios no requieren un servicio en la nube.
