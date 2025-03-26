import os
import os.path
import platform
import re
import subprocess
from shutil import which
from typing import Dict

import requests
from ovos_plugin_manager.templates.tts import TTS
from ovos_utils.log import LOG
from ovos_utils.xdg_utils import xdg_data_home
from quebra_frases import sentence_tokenize

from ovos_tts_plugin_nos.vits_onnx import VitsOnnxInference


class NosTTSPlugin(TTS):
    CELTIA = "Jarbas/proxectonos-celtia-vits-graphemes-onnx"
    SABELA = "Jarbas/proxectonos-sabela-vits-phonemes-onnx"
    VOICE2ENGINE: Dict[str, VitsOnnxInference] = {}

    def __init__(self, config=None):
        """
        Initialize the Nos TTS plugin for Galician text-to-speech synthesis.
        
        Parameters:
            config (dict, optional): Configuration dictionary for the TTS plugin. 
                Defaults to an empty dictionary if not provided.
        
        Behavior:
            - Sets the language to Galician (gl-ES)
            - Uses the default voice "celtia" if no specific voice is selected
            - Initializes a Cotovia TTS plugin for phonemization
            - Pre-downloads the selected voice model during initialization
        """
        config = config or {}
        config["lang"] = "gl-ES"
        super().__init__(config=config, audio_ext='wav')
        if self.voice == "default":
            self.voice = "celtia"
        self.cotovia_bin = self.config.get("cotovia") or self.find_cotovia()
        # pre-download voices on init if needed
        self.get_engine(self.voice)

    @staticmethod
    def find_cotovia() -> str:
        path = which("cotovia") or f"{os.path.dirname(__file__)}/cotovia_{platform.machine()}"
        if os.path.isfile(path):
            return path
        return "/usr/bin/cotovia"

    @staticmethod
    def download(voice: str):
        """
        Download the specified Galician TTS voice model and configuration files.
        
        This method downloads the model.onnx and config.json files for either the "celtia" or "sabela" Galician TTS voices from Hugging Face, storing them in the user's local data directory.
        
        Parameters:
            voice (str): The voice to download. Must be either "celtia" or "sabela".
        
        Raises:
            AssertionError: If the voice is not "celtia" or "sabela".
            requests.exceptions.RequestException: If there are issues downloading the files.
        
        Notes:
            - Creates a directory in the user's XDG data home path for storing models
            - Downloads model files only if they do not already exist locally
            - Streams the model.onnx download in chunks to handle large files efficiently
        """
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

    def cotovia_phonemize(self, sentence: str) -> str:
        """
        Converts a given sentence into phonemes using the Cotovia TTS binary.
        
        Processes the input sentence through a command-line phonemization tool, applying multiple regular expression transformations to clean and normalize the phonetic representation.
        
        Parameters:
            sentence (str): The input text to be phonemized
        
        Returns:
            str: A cleaned and normalized phonetic representation of the input sentence
        
        Notes:
            - Uses subprocess to execute the Cotovia TTS binary
            - Applies multiple regex substitutions to improve punctuation and spacing
            - Converts text from ISO-8859-1 to UTF-8 encoding
        """
        cmd = f'echo "{sentence}" | {self.cotovia_bin} -t -n -S | iconv -f iso88591 -t utf8'
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
        """
        Synthesize text to speech for the Galician language with optional voice selection and text preprocessing.
        
        Preprocesses the input sentence by converting currency and temperature symbols to their spoken Galician equivalents. For the "sabela" voice, tokenizes the sentence to improve synthesis naturalness.
        
        Parameters:
            sentence (str): The text to be converted to speech
            wav_file (str): Path where the output audio file will be saved
            lang (str, optional): Language code (defaults to None)
            voice (str, optional): Voice model to use, defaults to the instance's default voice
        
        Returns:
            tuple: A tuple containing the path to the generated WAV file and None for phonemes
        
        Notes:
            - Supports special preprocessing for currency (€, M€) and temperature (ºC) symbols
            - Uses sentence tokenization for more natural speech synthesis with the "sabela" voice
        """
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
            sentence = ". ".join([self.cotovia_phonemize(s)
                                  for s in sentence_tokenize(sentence)])

        tts = self.get_engine(voice)
        tts.synth(sentence, wav_file)
        return (wav_file, None)  # No phonemes

    @property
    def available_languages(self) -> set:
        """
        Return the set of languages supported by the Nos TTS plugin.
        
        Returns:
            set: A set containing the Galician language code "gl-es", indicating support for Galician (Spain).
        """
        return {"gl-es"}

    @classmethod
    def get_engine(cls, voice: str = "celtia") -> VitsOnnxInference:
        """
        Retrieve or initialize a VitsOnnxInference engine for a specific Galician TTS voice.
        
        This class method manages a cache of TTS engines, downloading the model if necessary and
        creating a new VitsOnnxInference instance for the specified voice.
        
        Parameters:
            voice (str, optional): The voice model to retrieve. Defaults to "celtia".
                                    Must be either "celtia" or "sabela".
        
        Returns:
            VitsOnnxInference: A cached or newly initialized TTS inference engine for the specified voice.
        
        Raises:
            AssertionError: If an unsupported voice is provided.
        """
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
