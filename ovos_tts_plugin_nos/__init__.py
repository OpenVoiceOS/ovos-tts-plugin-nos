import os
import os.path
import re
import subprocess
from typing import Dict

import requests
from ovos_plugin_manager.templates.tts import TTS
from ovos_tts_plugin_cotovia import CotoviaTTSPlugin
from ovos_tts_plugin_nos.vits_onnx import VitsOnnxInference
from ovos_utils.log import LOG
from ovos_utils.xdg_utils import xdg_data_home
from quebra_frases import sentence_tokenize


class NosTTSPlugin(TTS):
    CELTIA = "Jarbas/proxectonos-celtia-vits-graphemes-onnx"
    SABELA = "Jarbas/proxectonos-sabela-vits-phonemes-onnx"
    VOICE2ENGINE: Dict[str, VitsOnnxInference] = {}

    def __init__(self, config=None):
        config = config or {}
        config["lang"] = "gl-ES"
        super().__init__(config=config, audio_ext='wav')
        if self.voice == "default":
            self.voice = "celtia"
        self.cotovia = CotoviaTTSPlugin(config=config)
        # pre-download voices on init if needed
        self.get_engine(self.voice)

    @staticmethod
    def download(voice: str):
        assert voice in ["celtia", "sabela"]

        path = f"{xdg_data_home()}/nos_tts_models/{voice}"
        os.makedirs(path, exist_ok=True)

        voice_id = NosTTSPlugin.CELTIA if voice == "celtia" else NosTTSPlugin.SABELA

        if not os.path.isfile(f"{path}/model.onnx"):
            LOG.info(f"downloading {voice_id}  - this might take a while!")
            # Stream the download in chunks
            with requests.get(f"https://huggingface.co/{voice_id}/resolve/main/model.onnx", stream=True) as response:
                response.raise_for_status()  # Check if the request was successful
                with open(f"{path}/model.onnx", "wb") as f:
                    for chunk in response.iter_content(chunk_size=8192):
                        if chunk:
                            f.write(chunk)
        if not os.path.isfile(f"{path}/config.json"):
            with open(f"{path}/config.json", "wb") as f:
                f.write(requests.get(f"https://huggingface.co/{voice_id}/resolve/main/config.json").content)

    def phonemize(self, sentence: str) -> str:
        cmd = f'echo "{sentence}" | {self.cotovia.bin} -t -n -S | iconv -f iso88591 -t utf8'
        str_ext = subprocess.check_output(cmd, shell=True).decode("utf-8")

        ## fix punctuation in cotovia output - from official inference script

        # substitute ' ·\n' by ...
        str_ext = re.sub(r" ·", r"...", str_ext)

        # remove spaces before , . ! ? ; : ) ] of the extended string
        str_ext = re.sub(r"\s+([.,!?;:)\]])", r"\1", str_ext)

        # remove spaces after ( [ ¡ ¿ of the extended string
        str_ext = re.sub(r"([\(\[¡¿])\s+", r"\1", str_ext)

        # remove unwanted spaces between quotations marks
        str_ext = re.sub(r'"\s*([^"]*?)\s*"', r'"\1"', str_ext)

        # substitute '- text -' to '-text-'
        str_ext = re.sub(r"-\s*([^-]*?)\s*-", r"-\1-", str_ext)

        # remove initial question marks
        str_ext = re.sub(r"[¿¡]", r"", str_ext)

        # eliminate extra spaces
        str_ext = re.sub(r"\s+", r" ", str_ext)

        str_ext = re.sub(r"(\d+)\s*-\s*(\d+)", r"\1 \2", str_ext)

        ### - , ' and () by commas
        # substitute '- text -' to ', text,'
        str_ext = re.sub(r"(\w+)\s+-([^-]*?)-\s+([^-]*?)", r"\1, \2, ", str_ext)

        # substitute ' - ' by ', '
        str_ext = re.sub(r"(\w+[!\?]?)\s+-\s*", r"\1, ", str_ext)

        # substitute ' ( text )' to ', text,'
        str_ext = re.sub(r"(\w+)\s*\(\s*([^\(\)]*?)\s*\)", r"\1, \2,", str_ext)

        return str_ext

    def get_tts(self, sentence, wav_file, lang=None, voice=None):
        voice = voice or self.voice
        ## minor text preprocessing - taken from official inference script
        # substitute ' M€' by 'millóns de euros' and 'somewordM€' by 'someword millóns de euros'
        sentence = re.sub(r"(\w+)\s*M€", r"\1 millóns de euros", sentence)

        # substitute ' €' by 'euros' and 'someword€' by 'someword euros'
        sentence = re.sub(r"(\w+)\s*€", r"\1 euros", sentence)

        # substitute ' ºC' by 'graos centígrados' and 'somewordºC' by 'someword graos centígrados'
        sentence = re.sub(r"(\w+)\s*ºC", r"\1 graos centígrados", sentence)

        if voice == "sabela":
            # preserve sentence boundaries to make the synth more natural
            sentence = ". ".join([self.phonemize(s) for s in sentence_tokenize(sentence)])

        tts = self.get_engine(voice)
        tts.synth(sentence, wav_file)
        return (wav_file, None)  # No phonemes

    @property
    def available_languages(self) -> set:
        """Return languages supported by this TTS implementation in this state
        This property should be overridden by the derived class to advertise
        what languages that engine supports.
        Returns:
            set: supported languages
        """
        return {"gl-es"}

    @classmethod
    def get_engine(cls, voice: str = "celtia") -> VitsOnnxInference:
        if voice not in cls.VOICE2ENGINE:
            cls.download(voice)  # only if missing
            model_path = f"{xdg_data_home()}/nos_tts_models/{voice}/model.onnx"
            config_path = f"{xdg_data_home()}/nos_tts_models/{voice}/config.json"
            cls.VOICE2ENGINE[voice] = VitsOnnxInference(model_path, config_path)
        return cls.VOICE2ENGINE[voice]


if __name__ == "__main__":
    text = "Este é un sistema de conversión de texto a voz en lingua galega baseado en redes neuronais artificiais. Ten en conta que as funcionalidades incluídas nesta páxina ofrécense unicamente con fins de demostración. Se tes algún comentario, suxestión ou detectas algún problema durante a demostración, ponte en contacto connosco."
    tts = NosTTSPlugin({"voice": "sabela"})
    tts.get_tts(text, "test.wav")
