import io
import os
import speech_recognition as sr
import whisper
import time
import subprocess
from datetime import datetime, timedelta
from queue import Queue
from tempfile import NamedTemporaryFile
from time import sleep
import gtts
import pygame
import ctypes
import threading
from ollama import chat
import keyboard

# Ensure the script is running in the correct directory
os.chdir(os.path.dirname(os.path.abspath(__file__)))

temp_file = NamedTemporaryFile().name
transcription = ['']
audio_model = whisper.load_model("small")
data_queue = Queue() 
recorder = sr.Recognizer()
recorder.energy_threshold = 500
recorder.dynamic_energy_threshold = False
wake_word = "lumi"
wake_word2 = "lumie"
wake_word3 = "lumia"
wake_word4 = "lummi"
wake_word5 = "lumii"
audio_thread = None
stop_audio_event = threading.Event()
chat_history = []
callado = False

def write_file(data, filename, filetype):
    with open("{}.{}".format(filename, filetype), "a") as file:
        file.write(data)

def listen():  # This method is used within the class
    phrase_time = None
    phrase_timeout = 2
    record_timeout = 10
    last_sample = bytes()
    source = sr.Microphone(sample_rate=16000)
    with source:
        recorder.adjust_for_ambient_noise(source)
        recorder.energy_threshold += 25  # Aumenta la ganancia del micrófono

        def record_callback(_, audio: sr.AudioData) -> None:
            """
            Threaded callback function to recieve audio data when recordings finish.
            audio: An AudioData containing the recorded bytes.
            """
            # Grab the raw bytes and push it into the thread safe queue.
            data = audio.get_raw_data()
            data_queue.put(data)

    #Se deja el microfono escuchando con ayuda de speech_recognition
    recorder.listen_in_background(source, record_callback, phrase_time_limit=record_timeout)
    start = datetime.now()
    while True:
        try:
            now = datetime.now()
            if ((now - start).total_seconds()%18) == 0:
                write_transcript()
            # Pull raw recorded audio from the queue.
            if not data_queue.empty():
                phrase_complete = False
                if phrase_time and now - phrase_time > timedelta(seconds=phrase_timeout):
                    last_sample = bytes()
                    phrase_complete = True
                # This is the last time we received new audio data from the queue.
                phrase_time = now

                while not data_queue.empty():
                    data = data_queue.get()
                    last_sample += data


                audio_data = sr.AudioData(last_sample, source.SAMPLE_RATE, source.SAMPLE_WIDTH)
                wav_data = io.BytesIO(audio_data.get_wav_data())

                with open(temp_file, 'w+b') as f:
                    f.write(wav_data.read())

                result = audio_model.transcribe(temp_file, language='es')
                text = result['text'].strip()

                if phrase_complete:
                    transcription.append(text)
                else:
                    transcription[-1] = text
                
                if wake_word in transcription[-1].lower() or wake_word2 in transcription[-1].lower() or wake_word3 in transcription[-1].lower() or wake_word4 in transcription[-1].lower() or wake_word5 in transcription[-1].lower():
                    # Se activo el asistente
                    pygame.mixer.init()
                    if pygame.mixer.music.get_busy() == True:
                        pygame.mixer.music.stop()
                        pygame.mixer.music.unload()
                    mensaje = transcription[-1].lower()
                    respuesta = accion(mensaje)
                    subprocess.Popen("ollama stop llama3.2")
                    if callado == False:
                        tts(respuesta)
                    print(respuesta)
                
        except KeyboardInterrupt:
            break

def write_transcript():  # This method is used within the class
    print("\n\nTranscripcion:")
    for line in transcription:
        print(line)
        write_file(line, "transcript", "txt")

def accion( texto):  # This method is used within the class
    respuesta = ""
    print(texto)
    if "abre" in texto:
        if "explorador" in texto:
            subprocess.Popen(["explorer"])
            respuesta = "Abro el explorador de archivos"
        elif "steam" in texto:
            subprocess.Popen([r"C:\Program Files (x86)\Steam\steam.exe"])
            respuesta = "Abro steam"
        elif "navegador" in texto:
            subprocess.Popen([r"C:\Program Files\BraveSoftware\Brave-Browser\Application\brave.exe"])
            respuesta = "Abro Brave"
        elif "epic" in texto:
            subprocess.Popen([r"C:\Program Files\Epic Games\Launcher\Portal\Binaries\Win64\EpicGamesLauncher.exe"])
            respuesta = "Abro Epic Games"
        elif "discord" in texto:
            subprocess.Popen([r"C:\Users\loge2\AppData\Local\Discord\Update.exe"])
            respuesta = "Abro Discord"
        elif "visual studio" in texto:
            subprocess.Popen([r"C:\Users\loge2\AppData\Local\Programs\Microsoft VS Code\Code.exe"])
            respuesta = "Abro Visual Studio Code"
        elif "spotify" in texto:
            subprocess.Popen([r"C:\Users\loge2\AppData\Roaming\Spotify\Spotify.exe"])
            respuesta = "Abro Spotify"    
        elif "riot" in texto:
            subprocess.Popen([r"C:\Riot Games\Riot Client\RiotClientServices.exe"])
            respuesta = "Abro Riot Games"
        else:
            respuesta = "No se que abrir"
    elif "bloqueate" in texto:
        ctypes.windll.user32.LockWorkStation()
        respuesta = "Hasta Luego"
    elif "adiós" in texto:
        t = threading.Thread(name='adios', target=cerrar_programa)
        t.daemon = True
        t.start()
        respuesta = "Adios"
    elif "callate" in texto or "cállate" in texto:
        stop_audio()
        respuesta = "Me callo"
    elif "modo callado" in texto:
        if callado == False:
            callado = True
            respuesta = "Modo callado activado"
            tts(respuesta)
        else:
            callado = False
            respuesta = "Modo callado desactivado"
    elif "pausa canción" in texto or "pausa música" in texto or "pausa cancion" in texto or "pausa musica" in texto:
        keyboard.send("play/pause media")
        respuesta = "Pausando reproducción"
    elif "reproduce canción" in texto or "reproduce música" in texto or "reproduce cancion" in texto or "reproduce musica" in texto:
        keyboard.send("play/pause media")
        respuesta = "Reproduciendo"
    elif "siguiente canción" in texto or "siguiente música" in texto or "siguiente cancion" in texto or "siguiente musica" in texto:
        keyboard.send("next track")
        respuesta = "Siguiente canción"
    elif "anterior canción" in texto or "anterior música" in texto or "anterior cancion" in texto or "anterior musica" in texto:
        keyboard.send("previous track")
        keyboard.send("previous track")
        respuesta = "Canción anterior"
    else:
        respuesta = chat_bot(texto)
    return respuesta


def chat_bot(texto):  # This method is used within the class
    chat_history.append({'role': 'user', 'content': texto})
    
    stream = chat(
        model='llama3.2',
        messages=[
            {"role": "system", "content": "Eres una asistenta y te llamas lumi pero te van a llamar de otras formas y no vas a mencionar que te llamen asi"},
            *chat_history
        ],
        stream=True,
    )
    response = ""
    for chunk in stream:
        response += chunk.message.content
    
    chat_history.append({'role': 'assistant', 'content': response})
    return response

def tts( texto):  # This method is used within the class
    # Genera el archivo de audio a partir del texto
    filename = generate_audio_file(texto)
    play_audio_threaded(filename)

def generate_audio_file(texto):
    # LLamada a la API de Google Text to Speech
    if len(texto) > 0:
        tts = gtts.gTTS(texto, lang='es')
        tts.save('audio.mp3')
        return 'audio.mp3'
    else:
        print("No hay comando")
        return None

def play_audio_threaded( filename):  # This method is used within the class
    stop_audio_event.clear()
    audio_thread = threading.Thread(target=play_audio, args=(filename,))
    audio_thread.start()

def play_audio( filename):  # This method is used within the class
    pygame.mixer.music.load(filename)
    pygame.mixer.music.play()
    while pygame.mixer.music.get_busy() == True:
        if stop_audio_event.is_set():
            pygame.mixer.music.stop()
            break
        pygame.time.Clock().tick(10)
    pygame.mixer.music.unload()

def stop_audio():  # This method is used within the class
    if audio_thread and audio_thread.is_alive():
        stop_audio_event.set()
        audio_thread.join()

def play_audio_pygame(filename):
    # Abre el archivo de audio y lo reproduce con pygame
    pygame.mixer.music.load(filename)
    pygame.mixer.music.play()
    while pygame.mixer.music.get_busy() == True:
        pygame.time.Clock().tick(10)
    pygame.mixer.music.unload()

def cerrar_programa():
        time.sleep(2)
        print("Cerrando el programa...")
        subprocess.Popen("ollama stop llama3.2")
        os._exit(0)

def main():
    if os.name == 'nt':  # Check if the OS is Windows
        # Hide the console window
        ctypes.windll.user32.ShowWindow(ctypes.windll.kernel32.GetConsoleWindow(), 0)
    while True:
        try:
            listen()
            write_transcript()
        except KeyboardInterrupt:
            print("Ejecución terminada por el usuario.")
            break

if __name__ == "__main__":
    main()
