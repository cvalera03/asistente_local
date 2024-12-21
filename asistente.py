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

class Asistente:
    def __init__(self, model, record_timeout, phrase_timeout, energy_threshold, wake_word):
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
        self.audio_thread = None
        self.stop_audio_event = threading.Event()
        self.chat_history = []

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
                    
                    if self.wake_word in self.transcription[-1].lower():
                        # Se activo el asistente
                        pygame.mixer.init()
                        if pygame.mixer.music.get_busy() == True:
                            pygame.mixer.music.stop()
                            pygame.mixer.music.unload()
                        mensaje = self.transcription[-1].lower().replace(self.wake_word, "")
                        respuesta = self.accion(mensaje)
                        subprocess.Popen("ollama stop llama3.2")
                        print(respuesta)
                        self.tts(respuesta)
                    
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
        if "steam" in texto:
            subprocess.Popen(r'"C:\Program Files (x86)\Steam\steam.exe"')
            respuesta = "Abro steam"
        elif "notas" in texto:
            subprocess.Popen("notepad.exe")
            respuesta = "Abro notepad"
        elif "bloqueate" in texto:
            ctypes.windll.user32.LockWorkStation()
            respuesta = "Hasta Luego"
        elif "adiós" in texto:
            t = threading.Thread(name='adios', target=cerrar_programa)
            t.daemon = True
            t.start()
            respuesta = "Adios"
        elif "callate" in texto:
            self.stop_audio()
            respuesta = "Me callo"
        else:
            respuesta = self.chat_bot(texto)
        return respuesta

    def chat_bot(self, texto):
        self.chat_history.append({'role': 'user', 'content': texto})
        
        stream = chat(
            model='llama3.2',
            messages=[
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
