from utils import read_file
from asistente import Asistente

CONFIG_PARAMS = read_file("config", "yaml")

def main():

    model = CONFIG_PARAMS["stt"]["model_size"]
    record_timeout = CONFIG_PARAMS["stt"]["recording_time"]
    phrase_timeout = CONFIG_PARAMS["stt"]["silence_break"]
    energy_threshold = CONFIG_PARAMS["stt"]["sensibility"]
    wake_word = CONFIG_PARAMS["asistente"]["wake_word"]
    wake_word2 = CONFIG_PARAMS["asistente"]["wake_word2"]
    wake_word3 = CONFIG_PARAMS["asistente"]["wake_word3"]
    wake_word4 = CONFIG_PARAMS["asistente"]["wake_word4"]
    wake_word5 = CONFIG_PARAMS["asistente"]["wake_word5"]

    va = Asistente(model, record_timeout, phrase_timeout, energy_threshold, wake_word, wake_word2, wake_word3, wake_word4, wake_word5)
    va.listen()
    va.write_transcript()

if __name__ == "__main__":
    main()