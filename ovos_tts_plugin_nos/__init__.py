import os
import os.path
import subprocess
from typing import Optional

import requests
from TTS.utils.synthesizer import Synthesizer
from ovos_plugin_manager.templates.tts import TTS
from ovos_tts_plugin_cotovia import CotoviaTTSPlugin
from ovos_utils.log import LOG
from ovos_utils.xdg_utils import xdg_data_home


class NosTTSPlugin(TTS):
    CELTIA = "https://huggingface.co/proxectonos/Nos_TTS-celtia-vits-graphemes/resolve/main/celtia.pth"
    SABELA = "https://huggingface.co/proxectonos/Nos_TTS-sabela-vits-phonemes/resolve/main/sabela.pth"

    def __init__(self, lang="gl-es", config=None):
        config = config or {}
        config["lang"] = lang
        super().__init__(lang=lang, config=config, audio_ext='wav')
        if self.voice == "default":
            self.voice = "celtia"
        self.cotovia = CotoviaTTSPlugin()

    @staticmethod
    def download(url):
        path = f"{xdg_data_home()}/nos_tts_models"
        os.makedirs(path, exist_ok=True)
        # Get the file name from the URL
        file_name = url.split("/")[-1]
        file_path = f"{path}/{file_name}"
        if not os.path.isfile(file_path):
            LOG.info(f"downloading {url}  - this might take a while!")
            # Stream the download in chunks
            with requests.get(url, stream=True) as response:
                response.raise_for_status()  # Check if the request was successful
                with open(file_path, "wb") as f:
                    for chunk in response.iter_content(chunk_size=8192):
                        if chunk:
                            f.write(chunk)
        return file_path

    def phonemize(self, sentence: str) -> str:
        cmd = f'echo "{sentence}" | {self.cotovia.bin} -t -n -S | iconv -f iso88591 -t utf8'
        return subprocess.check_output(cmd, shell=True).decode("utf-8")

    def get_tts(self, sentence, wav_file, voice=None):
        voice = voice or self.voice
        if voice == "sabela":
            synth = self.get_engine(self.SABELA)
            sentence = self.phonemize(sentence)
        else:
            if voice != "celtia":
                LOG.warning(f"invalid voice '{voice}', falling back to default 'celtia'")
            synth = self.get_engine(self.CELTIA)
        wavs = synth.tts(sentence)
        synth.save_wav(wavs, wav_file)
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
    def get_engine(cls, model_path: str, config_path: Optional[str] = None) -> Synthesizer:
        config_path = config_path or model_path.replace(".pth", "_config.json")
        if model_path.startswith("http"):
            model_path = NosTTSPlugin.download(model_path)
        if config_path.startswith("http"):
            config_path = NosTTSPlugin.download(config_path)

        synthesizer = Synthesizer(
            model_path, config_path,
            None, None,
            None, None,
        )
        return synthesizer


if __name__ == "__main__":
    text = "Este é un sistema de conversión de texto a voz en lingua galega baseado en redes neuronais artificiais." \
           "Ten en conta que as funcionalidades incluídas nesta páxina ofrécense unicamente con fins de demostración. Se tes algún comentario, suxestión ou detectas algún problema durante a demostración, ponte en contacto connosco."
    tts = NosTTSPlugin(lang="gl-es")
    tts.get_tts(text, "test2.wav")
