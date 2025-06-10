# Asistente Virtual Local
Proyecto para poder correr un asistente virtual de manera local o mediante Gemini. Integra distintos modelos de machine learning para poder brindar distintas funcionalidades.
Actualmente el asistente corre en local sin necesidad de internet con un modelo de LLM basico para su uso. Se puede cambiar por cualquiera de Ollama.
Si decides integrarlo con Gemini no sera necesario ollama.

# Requisitos

Para instalar dependencias ejecutar:
```
pip install -r requirements.txt
```
Instalar aplicación [`Ollama`](https://ollama.com/) y ejecutar este comando en terminal:
```
ollama run llama3.2
```

Una vez dentro del repositorio usar:
```
python main.py
```

Whisper también requiere la herramienta de línea de comandos [`ffmpeg`](https://ffmpeg.org/) para ser instalado en su sistema, está disponible en la mayoría de los administradores de paquetes:

```
# on Ubuntu or Debian
sudo apt update && sudo apt install ffmpeg

# on Arch Linux
sudo pacman -S ffmpeg

# on MacOS using Homebrew (https://brew.sh/)
brew install ffmpeg

# on Windows using Chocolatey (https://chocolatey.org/)
choco install ffmpeg

# on Windows using Scoop (https://scoop.sh/)
scoop install ffmpeg
```

Para mas información sobre Whisper visita: https://github.com/openai/whisper

# Características

- **Transcripción de voz en tiempo real:** Utiliza Whisper para convertir tu voz a texto de manera rápida y precisa, permitiendo interacción natural.
- **Activación por palabra clave:** El asistente permanece en escucha pasiva y solo responde cuando detecta palabras clave como "lumi", "lumie", "lumia", etc., evitando respuestas accidentales.
- **Interfaz gráfica moderna y personalizable:** Basada en Tkinter, con diseño intuitivo, soporte para modo claro y oscuro, y botones interactivos.
- **Selección de modelo de IA:** Puedes elegir entre modelos LLM locales (Ollama, como llama3.2, phi3, gemma, qwen, granite, deepseek, etc.) o el modelo Gemini de Google, según tus necesidades y recursos.
- **Soporte para múltiples modelos de Whisper:** Elige el modelo de reconocimiento de voz que mejor se adapte a tu equipo (tiny, base, small, medium, large, turbo).
- **Ejecución en segundo plano y minimización a bandeja:** El asistente puede ejecutarse discretamente en la bandeja del sistema, permitiendo que sigas trabajando sin interrupciones.
- **Gestión avanzada de aplicaciones:** Desde la interfaz puedes agregar, editar, eliminar y abrir tus aplicaciones favoritas con comandos de voz o texto.
- **Control multimedia local:** Controla la reproducción de música o videos en tu equipo con comandos de voz (play, pausa, siguiente, anterior).
- **Consulta del clima:** Pregunta por la temperatura o el clima de tu ciudad y obtén la información actualizada mediante OpenWeatherMap.
- **Chatbot conversacional:** Interactúa con el asistente mediante texto o voz, con historial de contexto para mantener conversaciones naturales.
- **Modo callado y silenciamiento:** Puedes pedirle que guarde silencio temporalmente o activar el "modo callado" para que no hable hasta que lo desactives.
- **Configuración persistente:** Todas las opciones y preferencias se guardan automáticamente y se cargan al iniciar el asistente.
- **Manejo avanzado de errores:** Los errores se registran en un archivo de log y se notifican de forma clara al usuario.
- **Integración web:** Incluye un servidor Flask para exponer una API y servir una webapp local.
- **Cierre seguro:** El asistente puede cerrarse de forma controlada, liberando recursos y deteniendo procesos asociados.

## Comandos de voz disponibles

Puedes interactuar con el asistente usando los siguientes comandos de voz (también funcionan por texto):

- **"abre [nombre de app]"**: Abre la aplicación que hayas configurado previamente. Ejemplo: "abre chrome".
- **"bloqueate"**: Bloquea la sesión de Windows.
- **"pausa"**: Pausa o reanuda la reproducción multimedia.
- **"reproduce"**: Inicia o reanuda la reproducción multimedia.
- **"siguiente"**: Pasa a la siguiente canción o pista.
- **"anterior"**: Vuelve a la canción o pista anterior.
- **"duermete"** o **"apagate"**: Apaga el equipo inmediatamente.
- **"adiós"**: Cierra el asistente de forma segura.
- **"callate"** o **"cállate"**: Silencia la voz del asistente temporalmente.
- **"modo callado"**: Activa o desactiva el modo callado, en el que el asistente no responde con voz.
- **"temperatura"**: Informa sobre el clima y la temperatura actual de la ciudad configurada.

Además, cualquier otra frase o pregunta será respondida por el chatbot integrado, ya sea usando el modelo local o Gemini, según tu configuración.

# Objetivos
- [X] Transcripción en tiempo real 
- [X] Detectar palabra clave para que el asistente sepa que se le esta hablando y ejecutar acciones
- [X] Interfaz
- [X] Opciones de mas modelos
- [X] Correr en segundo plano
- [X] Añadir lista de aplicaciones
- [X] Conectarlo a un chatbot
- [X] Control de multimedia local

# Créditos y aportaciones
Lista de repositorios y recursos consultados o usados para este asistente virtual. 
* Base del proyecto. [Github Puigalex](https://github.com/puigalex/asistente_local)
* Implementación con mejoras para correr Whisper cercano a en tiempo real. [Github Davase](https://github.com/davabase/whisper_real_time)
