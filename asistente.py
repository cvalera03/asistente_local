import io
import os
import speech_recognition as sr
import whisper
from utils import write_file as wf
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

class Asistente:
    def __init__(self, model, record_timeout, phrase_timeout, energy_threshold, wake_word, wake_word2, wake_word3, wake_word4, wake_word5):
        self.temp_file = NamedTemporaryFile().name
        self.transcription = ['']
        self.audio_model = whisper.load_model(model)
        self.phrase_time = None
        self.last_sample = bytes()
        self.data_queue = Queue() 
        self.recorder = sr.Recognizer()
        self.recorder.energy_threshold = energy_threshold
        self.recorder.dynamic_energy_threshold = False
        self.record_timeout = record_timeout
        self.phrase_timeout = phrase_timeout
        self.wake_word = wake_word
        self.wake_word2 = wake_word2
        self.wake_word3 = wake_word3
        self.wake_word4 = wake_word4
        self.wake_word5 = wake_word5
        self.audio_thread = None
        self.stop_audio_event = threading.Event()
        self.chat_history = []
        self.callado = False


    def listen(self):
        self.source = sr.Microphone(sample_rate=16000)
        with self.source:
            self.recorder.adjust_for_ambient_noise(self.source)
            self.recorder.energy_threshold += 25  # Aumenta la ganancia del micrófono

            def record_callback(_, audio: sr.AudioData) -> None:
                """
                Threaded callback function to recieve audio data when recordings finish.
                audio: An AudioData containing the recorded bytes.
                """
                # Grab the raw bytes and push it into the thread safe queue.
                data = audio.get_raw_data()
                self.data_queue.put(data)

        #Se deja el microfono escuchando con ayuda de speech_recognition
        self.recorder.listen_in_background(self.source, record_callback, phrase_time_limit=self.record_timeout)
        start = datetime.utcnow()
        while True:
            try:
                now = datetime.utcnow()
                if ((now - start).total_seconds()%18) == 0:
                    self.write_transcript()
                # Pull raw recorded audio from the queue.
                if not self.data_queue.empty():
                    phrase_complete = False
                    if self.phrase_time and now - self.phrase_time > timedelta(seconds=self.phrase_timeout):
                        self.last_sample = bytes()
                        phrase_complete = True
                    # This is the last time we received new audio data from the queue.
                    self.phrase_time = now

                    while not self.data_queue.empty():
                        data = self.data_queue.get()
                        self.last_sample += data


                    audio_data = sr.AudioData(self.last_sample, self.source.SAMPLE_RATE, self.source.SAMPLE_WIDTH)
                    wav_data = io.BytesIO(audio_data.get_wav_data())

                    with open(self.temp_file, 'w+b') as f:
                        f.write(wav_data.read())

                    result = self.audio_model.transcribe(self.temp_file, language='es')
                    text = result['text'].strip()

                    if phrase_complete:
                        self.transcription.append(text)
                    else:
                        self.transcription[-1] = text
                    
                    if self.wake_word in self.transcription[-1].lower() or self.wake_word2 in self.transcription[-1].lower() or self.wake_word3 in self.transcription[-1].lower() or self.wake_word4 in self.transcription[-1].lower() or self.wake_word5 in self.transcription[-1].lower():
                        # Se activo el asistente
                        pygame.mixer.init()
                        if pygame.mixer.music.get_busy() == True:
                            pygame.mixer.music.stop()
                            pygame.mixer.music.unload()
                        mensaje = self.transcription[-1].lower()
                        respuesta = self.accion(mensaje)
                        subprocess.Popen("ollama stop llama3.2")
                        if self.callado == False:
                            self.tts(respuesta)
                        print(respuesta)
                    
            except KeyboardInterrupt:
                break
    
    def write_transcript(self):
        print("\n\nTranscripcion:")
        for line in self.transcription:
            print(line)
            wf(line, "transcript", "txt")

    def accion(self, texto):
        respuesta = ""
        print(texto)
        if "abre" in texto:
            if "explorador" in texto:
                subprocess.Popen("explorer")
                respuesta = "Abro el explorador de archivos"
            elif "steam" in texto:
                subprocess.Popen(r'"C:\Program Files (x86)\Steam\steam.exe"')
                respuesta = "Abro steam"
                print(respuesta)
            elif "navegador" in texto:
                subprocess.Popen(r'"C:\Program Files\BraveSoftware\Brave-Browser\Application\brave.exe"')
                respuesta = "Abro Brave"
            elif "epic" in texto:
                subprocess.Popen(r'"C:\Program Files\Epic Games\Launcher\Portal\Binaries\Win64\EpicGamesLauncher.exe"')
                respuesta = "Abro Epic Games"
            elif "discord" in texto:
                subprocess.Popen(r'"C:\Users\loge2\AppData\Local\Discord\Update.exe"')
                respuesta = "Abro Discord"
            elif "visual studio" in texto:
                subprocess.Popen(r'"C:\Users\loge2\AppData\Local\Programs\Microsoft VS Code\Code.exe"')
                respuesta = "Abro Visual Studio Code"
            elif "spotify" in texto:
                subprocess.Popen(r'"C:\Users\loge2\AppData\Roaming\Spotify\Spotify.exe"')
                respuesta = "Abro Spotify"     
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
            self.stop_audio()
            respuesta = "Me callo"
        elif "modo callado" in texto:
            if self.callado == False:
                self.callado = True
                respuesta = "Modo callado activado"
                self.tts(respuesta)
            else:
                self.callado = False
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
            respuesta = self.chat_bot(texto)
        return respuesta
        

    def chat_bot(self, texto):
        self.chat_history.append({'role': 'user', 'content': texto})
        
        stream = chat(
            model='llama3.2',
            messages=[
                {"role": "system", "content": "Eres una asistenta y te llamas lumi pero te van a llamar de otras formas y no vas a mencionar que te llamen asi"},
                *self.chat_history
            ],
            stream=True,
        )
        response = ""
        for chunk in stream:
            response += chunk.message.content
        
        self.chat_history.append({'role': 'assistant', 'content': response})
        return response

    def tts(self, texto):
        # Genera el archivo de audio a partir del texto
        filename = self.generate_audio_file(texto)
        self.play_audio_threaded(filename)

    def generate_audio_file(self, texto):
        # LLamada a la API de Google Text to Speech
        if len(texto) > 0:
            tts = gtts.gTTS(texto, lang='es')
            tts.save('audio.mp3')
            return 'audio.mp3'
        else:
            print("No hay comando")
            return None

    def play_audio_threaded(self, filename):
        self.stop_audio_event.clear()
        self.audio_thread = threading.Thread(target=self.play_audio, args=(filename,))
        self.audio_thread.start()

    def play_audio(self, filename):
        pygame.mixer.music.load(filename)
        pygame.mixer.music.play()
        while pygame.mixer.music.get_busy() == True:
            if self.stop_audio_event.is_set():
                pygame.mixer.music.stop()
                break
            pygame.time.Clock().tick(10)
        pygame.mixer.music.unload()

    def stop_audio(self):
        if self.audio_thread and self.audio_thread.is_alive():
            self.stop_audio_event.set()
            self.audio_thread.join()

    def play_audio_pygame(self, filename):
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
