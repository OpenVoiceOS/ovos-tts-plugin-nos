# minimal onnx inference extracted from coqui-tts
import json
import re
from typing import Callable, List
from ovos_utils.log import LOG
import numpy as np
import onnxruntime as ort
import scipy

# Regular expression matching whitespace:
_whitespace_re = re.compile(r"\s+")


class Graphemes:
    """🐸
        Characters are ordered as follows ```[PAD, EOS, BOS, BLANK, CHARACTERS, PUNCTUATIONS]```.

        If you need a custom order, you need to define inherit from this class and override the ```_create_vocab``` method.

        Args:
            characters (str):
                Main set of characters to be used in the vocabulary.

            punctuations (str):
                Characters to be treated as punctuation.

            pad (str):
                Special padding character that would be ignored by the model.

            eos (str):
                End of the sentence character.

            bos (str):
                Beginning of the sentence character.

            blank (str):
                Optional character used between characters by some models for better prosody.

            is_unique (bool):
                Remove duplicates from the provided characters. Defaults to True.
    el
            is_sorted (bool):
                Sort the characters in alphabetical order. Only applies to `self.characters`. Defaults to True.
    """

    def __init__(
            self,
            characters: str = None,
            punctuations: str = None,
            pad: str = None,
            eos: str = None,
            bos: str = None,
            blank: str = "<BLNK>",
            is_unique: bool = False,
            is_sorted: bool = True,
    ) -> None:
        self._characters = characters
        self._punctuations = punctuations
        self._pad = pad
        self._eos = eos
        self._bos = bos
        self._blank = blank
        self.is_unique = is_unique
        self.is_sorted = is_sorted
        self._create_vocab()

    @property
    def pad_id(self) -> int:
        return self.char_to_id(self.pad) if self.pad else len(self.vocab)

    @property
    def blank_id(self) -> int:
        return self.char_to_id(self.blank) if self.blank else len(self.vocab)

    @property
    def eos_id(self) -> int:
        return self.char_to_id(self.eos) if self.eos else len(self.vocab)

    @property
    def bos_id(self) -> int:
        return self.char_to_id(self.bos) if self.bos else len(self.vocab)

    @property
    def characters(self):
        return self._characters

    @characters.setter
    def characters(self, characters):
        self._characters = characters
        self._create_vocab()

    @property
    def punctuations(self):
        return self._punctuations

    @punctuations.setter
    def punctuations(self, punctuations):
        self._punctuations = punctuations
        self._create_vocab()

    @property
    def pad(self):
        return self._pad

    @pad.setter
    def pad(self, pad):
        self._pad = pad
        self._create_vocab()

    @property
    def eos(self):
        return self._eos

    @eos.setter
    def eos(self, eos):
        self._eos = eos
        self._create_vocab()

    @property
    def bos(self):
        return self._bos

    @bos.setter
    def bos(self, bos):
        self._bos = bos
        self._create_vocab()

    @property
    def blank(self):
        return self._blank

    @blank.setter
    def blank(self, blank):
        self._blank = blank
        self._create_vocab()

    @property
    def vocab(self):
        return self._vocab

    @vocab.setter
    def vocab(self, vocab):
        self._vocab = vocab
        self._char_to_id = {char: idx for idx, char in enumerate(self.vocab)}
        self._id_to_char = {
            idx: char for idx, char in enumerate(self.vocab)  # pylint: disable=unnecessary-comprehension
        }

    @property
    def num_chars(self):
        return len(self._vocab)

    def _create_vocab(self):
        self._vocab = [self._pad] + list(self._punctuations) + list(self._characters) + [self._blank]
        self._char_to_id = {char: idx for idx, char in enumerate(self.vocab)}
        # pylint: disable=unnecessary-comprehension
        self._id_to_char = {idx: char for idx, char in enumerate(self.vocab)}

    def char_to_id(self, char: str) -> int:
        try:
            return self._char_to_id[char]
        except KeyError as e:
            raise KeyError(f" [!] {repr(char)} is not in the vocabulary.") from e

    def id_to_char(self, idx: int) -> str:
        return self._id_to_char[idx]


class TTSTokenizer:
    """🐸TTS tokenizer to convert input characters to token IDs.

    Token IDs for OOV chars are discarded but those are stored in `self.not_found_characters` for later.

    Args:
        characters (Characters):
            A Characters object to use for character-to-ID and ID-to-character mappings.

        text_cleaner (callable):
            A function to pre-process the text before tokenization and phonemization. Defaults to None.
    """

    def __init__(
            self,
            text_cleaner: Callable = None,
            characters: Graphemes = None,
            add_blank: bool = False,
            use_eos_bos=False,
    ):
        self.text_cleaner = text_cleaner
        self.add_blank = add_blank
        self.use_eos_bos = use_eos_bos
        self.characters = characters
        self.not_found_characters = []

    @property
    def characters(self):
        return self._characters

    @characters.setter
    def characters(self, new_characters):
        self._characters = new_characters
        self.pad_id = self.characters.char_to_id(self.characters.pad) if self.characters.pad else None
        self.blank_id = self.characters.char_to_id(self.characters.blank) if self.characters.blank else None

    def encode(self, text: str) -> List[int]:
        """Encodes a string of text as a sequence of IDs."""
        token_ids = []
        for char in text:
            try:
                idx = self.characters.char_to_id(char)
                token_ids.append(idx)
            except KeyError:
                # discard but store not found characters
                if char not in self.not_found_characters:
                    self.not_found_characters.append(char)
                    LOG.debug(text)
                    LOG.warning(f" [!] Character {repr(char)} not found in the vocabulary. Discarding it.")
        return token_ids

    def text_to_ids(self, text: str) -> List[int]:  # pylint: disable=unused-argument
        """Converts a string of text to a sequence of token IDs.

        Args:
            text(str):
                The text to convert to token IDs.

        1. Text normalization
        3. Add blank char between characters
        4. Add BOS and EOS characters
        5. Text to token IDs
        """
        if self.text_cleaner is not None:
            text = self.text_cleaner(text)
        text = self.encode(text)
        if self.add_blank:
            text = self.intersperse_blank_char(text)
        if self.use_eos_bos:
            text = self.pad_with_bos_eos(text)
        return text

    def pad_with_bos_eos(self, char_sequence: List[int]):
        """Pads a sequence with the special BOS and EOS characters."""
        return [self.characters.bos_id] + list(char_sequence) + [self.characters.eos_id]

    def intersperse_blank_char(self, char_sequence: List[int]):
        """Intersperses the blank character between characters in a sequence.
        """
        result = [self.characters.blank_id] * (len(char_sequence) * 2 + 1)
        result[1::2] = char_sequence
        return result


class VitsOnnxInference:
    def __init__(self, onnx_model_path: str, config_path: str, cuda=False):
        self.config = {}
        if config_path:
            with open(config_path) as f:
                self.config = json.load(f)
        providers = [
            "CPUExecutionProvider"
            if cuda is False
            else ("CUDAExecutionProvider", {"cudnn_conv_algo_search": "DEFAULT"})
        ]
        sess_options = ort.SessionOptions()
        self.onnx_sess = ort.InferenceSession(
            onnx_model_path,
            sess_options=sess_options,
            providers=providers,
        )

        _pad = self.config.get("characters", {}).get("pad", "_")
        _punctuations = self.config.get("characters", {}).get("punctuations", "!\"(),-.:;?\u00a1\u00bf ")
        _letters = self.config.get("characters", {}).get("characters",
                                                         "ABCDEFGHIJKLMNOPQRSTUVXYZabcdefghijklmnopqrstuvwxyz\u00c1\u00c9\u00cd\u00d3\u00da\u00e1\u00e9\u00ed\u00f1\u00f3\u00fa\u00fc")

        vocab = Graphemes(characters=_letters,
                          punctuations=_punctuations,
                          pad=_pad)

        self.tokenizer = TTSTokenizer(
            text_cleaner=self.normalize_text,
            characters=vocab,
            add_blank=self.config.get("add_blank", True),
            use_eos_bos=False,
        )

    @staticmethod
    def normalize_text(text: str) -> str:
        """Basic pipeline that lowercases and collapses whitespace without transliteration."""
        text = text.lower()
        text = text.replace(";", ",")
        text = text.replace("-", " ")
        text = text.replace(":", ",")
        text = re.sub(r"[\<\>\(\)\[\]\"]+", "", text)
        text = re.sub(_whitespace_re, " ", text).strip()
        return text

    def inference_onnx(self, text: str):
        """ONNX inference"""
        x = np.asarray(
            self.tokenizer.text_to_ids(text),
            dtype=np.int64,
        )[None, :]

        x_lengths = np.array([x.shape[1]], dtype=np.int64)

        scales = np.array(
            [self.config.get("inference_noise_scale", 0.667),
             self.config.get("length_scale", 1.0),
             self.config.get("inference_noise_scale_dp", 1.0), ],
            dtype=np.float32,
        )
        input_params = {"input": x, "input_lengths": x_lengths, "scales": scales}

        audio = self.onnx_sess.run(
            ["output"],
            input_params,
        )
        return audio[0][0]

    @staticmethod
    def save_wav(wav: np.ndarray, path: str, sample_rate: int = 16000) -> None:
        """Save float waveform to a file using Scipy.

        Args:
            wav (np.ndarray): Waveform with float values in range [-1, 1] to save.
            path (str): Path to a output file.
        """
        wav_norm = wav * (32767 / max(0.01, np.max(np.abs(wav))))
        wav_norm = wav_norm.astype(np.int16)
        scipy.io.wavfile.write(path, sample_rate, wav_norm)

    def synth(self, text: str, path: str):
        wavs = self.inference_onnx(text)
        self.save_wav(wavs[0], path, self.config.get("sample_rate", 16000))
