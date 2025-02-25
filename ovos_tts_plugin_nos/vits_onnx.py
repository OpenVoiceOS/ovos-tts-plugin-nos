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
        """
        Initialize a Graphemes instance with character sets and vocabulary configuration.

        Parameters:
            characters (str, optional): A string of characters to include in the vocabulary. Defaults to None.
            punctuations (str, optional): A string of punctuation characters to include. Defaults to None.
            pad (str, optional): A padding token. Defaults to None.
            eos (str, optional): End-of-sequence token. Defaults to None.
            bos (str, optional): Beginning-of-sequence token. Defaults to None.
            blank (str, optional): Blank token used in tokenization. Defaults to "<BLNK>".
            is_unique (bool, optional): Whether to ensure unique characters in the vocabulary. Defaults to False.
            is_sorted (bool, optional): Whether to sort the characters in the vocabulary. Defaults to True.

        Attributes:
            _characters (str): Stored characters for vocabulary creation
            _punctuations (str): Stored punctuation characters
            _pad (str): Padding token
            _eos (str): End-of-sequence token
            _bos (str): Beginning-of-sequence token
            _blank (str): Blank token
            is_unique (bool): Flag for unique character requirement
            is_sorted (bool): Flag for character sorting

        Notes:
            - Calls _create_vocab() to generate the vocabulary after initialization
            - Allows flexible configuration of character sets and special tokens
        """
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
        """
        Returns the ID for the padding character.

        If a padding character is defined, returns its corresponding ID from the vocabulary.
        If no padding character is specified, returns the length of the vocabulary as a default padding ID.

        Returns:
            int: The ID of the padding character or the vocabulary length
        """
        return self.char_to_id(self.pad) if self.pad else len(self.vocab)

    @property
    def blank_id(self) -> int:
        """
        Returns the ID of the blank token in the vocabulary.

        If a blank token is defined, returns its corresponding ID using char_to_id method.
        If no blank token is specified, returns the length of the current vocabulary as a default blank token ID.

        Returns:
            int: The ID of the blank token or the next available vocabulary index
        """
        return self.char_to_id(self.blank) if self.blank else len(self.vocab)

    @property
    def eos_id(self) -> int:
        """
        Returns the ID for the end-of-sentence (EOS) token.

        If an EOS token is defined, returns its corresponding character ID from the vocabulary.
        If no EOS token is defined, returns the length of the vocabulary as a default ID.

        Returns:
            int: The ID of the end-of-sentence token or the vocabulary length
        """
        return self.char_to_id(self.eos) if self.eos else len(self.vocab)

    @property
    def bos_id(self) -> int:
        """
        Returns the ID for the beginning-of-sequence (BOS) token.

        If a BOS token is defined, returns its corresponding vocabulary ID.
        If no BOS token is specified, returns the length of the current vocabulary,
        which represents a default/fallback ID for the beginning-of-sequence marker.

        Returns:
            int: The vocabulary ID for the beginning-of-sequence token
        """
        return self.char_to_id(self.bos) if self.bos else len(self.vocab)

    @property
    def characters(self):
        """
        Get the set of characters in the vocabulary.

        Returns:
            str: A string containing all characters in the vocabulary.
        """
        return self._characters

    @characters.setter
    def characters(self, characters):
        """
        Set the characters for the vocabulary and regenerate the vocabulary.

        This method allows updating the character set for the Graphemes instance and automatically
        rebuilds the internal vocabulary mapping based on the new characters.

        Parameters:
            characters (str): A string containing the characters to be used in the vocabulary.

        Side Effects:
            - Updates the internal `_characters` attribute
            - Calls `_create_vocab()` to rebuild the vocabulary mappings
        """
        self._characters = characters
        self._create_vocab()

    @property
    def punctuations(self):
        """
        Get the set of punctuation characters used in the vocabulary.

        Returns:
            str: A string containing all punctuation characters defined for the grapheme set.
        """
        return self._punctuations

    @punctuations.setter
    def punctuations(self, punctuations):
        """
        Set the punctuation characters for the vocabulary and recreate the vocabulary.

        This method allows updating the punctuation characters used in the Graphemes vocabulary. After setting the new punctuation characters, it triggers the recreation of the vocabulary to incorporate the updated punctuation set.

        Parameters:
            punctuations (str): A string containing punctuation characters to be included in the vocabulary.
        """
        self._punctuations = punctuations
        self._create_vocab()

    @property
    def pad(self):
        """
        Returns the padding token ID for the grapheme vocabulary.

        Returns:
            int: The ID of the padding token used in the vocabulary.
        """
        return self._pad

    @pad.setter
    def pad(self, pad):
        """
        Set the padding character and recreate the vocabulary.

        This method allows updating the padding character for the Graphemes instance
        and triggers a vocabulary recreation to incorporate the new padding character.

        Parameters:
            pad (str): The padding character to be used in the vocabulary.
        """
        self._pad = pad
        self._create_vocab()

    @property
    def eos(self):
        """
        Returns the end-of-sentence (EOS) token ID.

        Returns:
            int: The ID representing the end-of-sentence token in the vocabulary.
        """
        return self._eos

    @eos.setter
    def eos(self, eos):
        """
        Set the end-of-sentence (EOS) token and recreate the vocabulary.

        This method allows updating the end-of-sentence token for the Graphemes instance and triggers a vocabulary reconstruction to incorporate the new token.

        Parameters:
            eos (str): The new end-of-sentence token to be used in the vocabulary.
        """
        self._eos = eos
        self._create_vocab()

    @property
    def bos(self):
        """
        Returns the beginning-of-sequence (BOS) token ID.

        Returns:
            int: The ID representing the beginning of a sequence in the character vocabulary.
        """
        return self._bos

    @bos.setter
    def bos(self, bos):
        """
        Set the beginning-of-sentence (BOS) token and recreate the vocabulary.

        This method allows updating the beginning-of-sentence token for the Graphemes instance and triggers a vocabulary reconstruction to incorporate the new token.

        Parameters:
            bos (str): The token to be used as the beginning-of-sentence marker.
        """
        self._bos = bos
        self._create_vocab()

    @property
    def blank(self):
        """
        Returns the blank token used in the grapheme vocabulary.

        Returns:
            str: The blank token symbol, typically representing a pause or silence in the character set.
        """
        return self._blank

    @blank.setter
    def blank(self, blank):
        """
        Set the blank token and recreate the vocabulary.

        This method allows updating the blank token used in the Graphemes vocabulary and triggers a recreation of the vocabulary with the new blank token.

        Parameters:
            blank (str): The new blank token to be used in the vocabulary. Typically a special character or string representing a blank/pause.

        Side Effects:
            - Updates the internal blank token attribute
            - Calls `_create_vocab()` to regenerate the vocabulary with the new blank token
        """
        self._blank = blank
        self._create_vocab()

    @property
    def vocab(self):
        """
        Returns the vocabulary dictionary mapping characters to their unique integer IDs.

        Returns:
            dict: A dictionary where keys are characters and values are their corresponding integer IDs.
        """
        return self._vocab

    @vocab.setter
    def vocab(self, vocab):
        """
        Create vocabulary mappings from a given list of characters.

        This method initializes two internal dictionaries:
        - `_char_to_id`: Maps characters to their unique integer indices
        - `_id_to_char`: Maps integer indices back to their corresponding characters

        Parameters:
            vocab (list): A list of characters defining the vocabulary

        Side Effects:
            - Sets `self._vocab` to the input vocabulary
            - Creates `self._char_to_id` dictionary for character-to-index mapping
            - Creates `self._id_to_char` dictionary for index-to-character mapping
        """
        self._vocab = vocab
        self._char_to_id = {char: idx for idx, char in enumerate(self.vocab)}
        self._id_to_char = {
            idx: char for idx, char in enumerate(self.vocab)  # pylint: disable=unnecessary-comprehension
        }

    @property
    def num_chars(self):
        """
        Returns the total number of characters in the vocabulary.

        Returns:
            int: The number of unique characters in the vocabulary.
        """
        return len(self._vocab)

    def _create_vocab(self):
        """
        Create the vocabulary and character-to-ID mappings for the Graphemes class.

        This method initializes the vocabulary by combining padding, punctuation, characters, and blank tokens
        in a specific order. It creates two dictionaries:
        - `_char_to_id`: Maps characters to their unique integer indices
        - `_id_to_char`: Maps integer indices back to their corresponding characters

        The vocabulary order is:
        1. Padding token
        2. Punctuation characters
        3. Regular characters
        4. Blank token

        Returns:
            None. Populates internal `_vocab`, `_char_to_id`, and `_id_to_char` attributes.
        """
        self._vocab = [self._pad] + list(self._punctuations) + list(self._characters) + [self._blank]
        self._char_to_id = {char: idx for idx, char in enumerate(self.vocab)}
        # pylint: disable=unnecessary-comprehension
        self._id_to_char = {idx: char for idx, char in enumerate(self.vocab)}

    def char_to_id(self, char: str) -> int:
        """
        Convert a character to its corresponding integer ID in the vocabulary.

        Parameters:
            char (str): A single character to convert to its vocabulary ID.

        Returns:
            int: The integer ID associated with the input character.

        Raises:
            KeyError: If the input character is not present in the vocabulary.

        Example:
            graphemes = Graphemes(characters='abcdef')
            id_of_a = graphemes.char_to_id('a')  # Returns 0
            graphemes.char_to_id('z')  # Raises KeyError
        """
        try:
            return self._char_to_id[char]
        except KeyError as e:
            raise KeyError(f" [!] {repr(char)} is not in the vocabulary.") from e

    def id_to_char(self, idx: int) -> str:
        """
        Convert a token ID to its corresponding character.

        Parameters:
            idx (int): The integer ID of the token to convert.

        Returns:
            str: The character corresponding to the given token ID.

        Raises:
            KeyError: If the provided index is not found in the vocabulary mapping.

        Example:
            graphemes = Graphemes()
            char = graphemes.id_to_char(5)  # Returns the character at index 5 in the vocabulary
        """
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
        """
        Initialize a TTSTokenizer with optional text cleaning, character vocabulary, and tokenization settings.

        Parameters:
            text_cleaner (Callable, optional): A function to preprocess and clean input text before tokenization.
            characters (Graphemes, optional): A Graphemes object defining the character vocabulary for tokenization.
            add_blank (bool, default=False): Whether to intersperse blank tokens between character tokens during encoding.
            use_eos_bos (bool, default=False): Whether to add beginning and end of sequence tokens to the token sequence.

        Attributes:
            text_cleaner (Callable): Text preprocessing function.
            add_blank (bool): Flag to insert blank tokens between characters.
            use_eos_bos (bool): Flag to add start and end sequence tokens.
            characters (Graphemes): Character vocabulary for token mapping.
            not_found_characters (List[str]): Tracks characters not found in the vocabulary during tokenization.
        """
        self.text_cleaner = text_cleaner
        self.add_blank = add_blank
        self.use_eos_bos = use_eos_bos
        self.characters = characters
        self.not_found_characters = []

    @property
    def characters(self):
        """
        Get the set of characters in the vocabulary.

        Returns:
            str: A string containing all characters in the vocabulary.
        """
        return self._characters

    @characters.setter
    def characters(self, new_characters):
        """
        Set the characters configuration and update special token IDs.

        This method updates the internal character configuration and recalculates the IDs for padding and blank tokens based on the new character set.

        Parameters:
            new_characters (Graphemes): A Graphemes object representing the character vocabulary to be used.

        Side Effects:
            - Updates the internal `_characters` attribute
            - Recalculates `pad_id` and `blank_id` based on the new character set
        """
        self._characters = new_characters
        self.pad_id = self.characters.char_to_id(self.characters.pad) if self.characters.pad else None
        self.blank_id = self.characters.char_to_id(self.characters.blank) if self.characters.blank else None

    def encode(self, text: str) -> List[int]:
        """
        Encode a string of text into a sequence of token IDs based on the character vocabulary.

        This method converts each character in the input text to its corresponding token ID. Characters not found in the vocabulary are discarded and logged as warnings.

        Parameters:
            text (str): The input text to be tokenized.

        Returns:
            List[int]: A list of token IDs representing the input text.

        Notes:
            - Out-of-vocabulary characters are silently discarded.
            - Unique out-of-vocabulary characters are tracked and logged with a debug message.
            - Warnings are generated for characters not found in the vocabulary.

        Raises:
            No explicit exceptions are raised during the encoding process.
        """
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
        """
        Convert text to a sequence of token IDs with optional preprocessing.

        Applies a series of transformations to the input text:
        1. Optionally cleans the text using a provided text cleaner function
        2. Encodes the text into token IDs
        3. Optionally inserts blank characters between tokens
        4. Optionally adds beginning and end of sequence tokens

        Parameters:
            text (str): Input text to be converted to token IDs

        Returns:
            List[int]: A sequence of token IDs after applying configured transformations

        Notes:
            - Uses self.text_cleaner for optional text preprocessing
            - Supports optional blank character insertion
            - Supports optional beginning and end of sequence token padding
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
        """
        Pad a character sequence with beginning-of-sequence (BOS) and end-of-sequence (EOS) tokens.

        Parameters:
            char_sequence (List[int]): A list of character token IDs to be padded.

        Returns:
            List[int]: A new list with BOS token prepended and EOS token appended to the original sequence.

        Example:
            tokenizer = TTSTokenizer(...)
            sequence = [10, 20, 30]
            padded_sequence = tokenizer.pad_with_bos_eos(sequence)
            # Result might be: [BOS_TOKEN_ID, 10, 20, 30, EOS_TOKEN_ID]
        """
        return [self.characters.bos_id] + list(char_sequence) + [self.characters.eos_id]

    def intersperse_blank_char(self, char_sequence: List[int]):
        """
        Intersperses the blank character between characters in a sequence.

        This method creates a new sequence where the blank character is inserted between each original character, effectively expanding the input sequence with blank tokens.

        Parameters:
            char_sequence (List[int]): A list of character IDs to be interspersed with blank tokens.

        Returns:
            List[int]: A new sequence with blank tokens inserted between each original character,
                       with blank tokens at the beginning and end of the sequence.

        Example:
            If char_sequence is [5, 10, 15] and blank_id is 0, the result will be:
            [0, 5, 0, 10, 0, 15, 0]
        """
        result = [self.characters.blank_id] * (len(char_sequence) * 2 + 1)
        result[1::2] = char_sequence
        return result


class VitsOnnxInference:
    def __init__(self, onnx_model_path: str, config_path: str, cuda=False):
        """
        Initialize a VITS ONNX inference session with model and configuration.
        
        Parameters:
            onnx_model_path (str): Path to the ONNX model file for text-to-speech inference
            config_path (str): Path to the JSON configuration file containing model settings
            cuda (bool, optional): Flag to enable CUDA GPU acceleration. Defaults to False.
        
        Attributes:
            config (dict): Configuration dictionary loaded from the config file
            onnx_sess (onnx.InferenceSession): ONNX runtime inference session
            tokenizer (TTSTokenizer): Tokenizer configured with character vocabulary and text cleaning
        
        Notes:
            - Configures ONNX runtime providers based on CUDA availability
            - Loads character configurations for vocabulary creation
            - Initializes a Graphemes vocabulary and TTSTokenizer
            - Supports optional GPU acceleration with CUDA
        """
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
        """
        Normalize input text by applying a series of transformations.
        
        This method performs text normalization by:
        - Converting text to lowercase
        - Replacing semicolons and colons with commas
        - Replacing hyphens with spaces
        - Removing special characters like angle brackets, parentheses, and quotation marks
        - Collapsing multiple whitespaces into a single space
        - Stripping leading and trailing whitespaces
        
        Parameters:
            text (str): The input text to be normalized
        
        Returns:
            str: A normalized version of the input text with simplified punctuation and whitespace
        """
        text = text.lower()
        text = text.replace(";", ",")
        text = text.replace("-", " ")
        text = text.replace(":", ",")
        text = re.sub(r"[\<\>\(\)\[\]\"]+", "", text)
        text = re.sub(_whitespace_re, " ", text).strip()
        return text

    def inference_onnx(self, text: str):
        """
        Perform ONNX model inference to generate audio from tokenized text.
        
        Converts input text into token IDs and runs the ONNX model to synthesize speech audio.
        
        Parameters:
            text (str): Input text to be converted into speech
        
        Returns:
            numpy.ndarray: Generated audio waveform from the ONNX model inference
        
        Notes:
            - Tokenizes input text using the configured tokenizer
            - Applies noise and length scaling parameters from configuration
            - Runs ONNX session with prepared input parameters
            - Returns the first audio waveform from the model output
        """
        x = np.asarray(
            self.tokenizer.text_to_ids(text),
            dtype=np.int64,
        )[None, :]

        x_lengths = np.array([x.shape[1]], dtype=np.int64)

        scales = np.array(
            [self.config.get("inference_noise_scale", 0.667),
             self.config.get("length_scale", 1.0),
             self.config.get("inference_noise_scale_dp", 1.0)],
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
        """
        Save a float waveform to a WAV file with normalization.
        
        Parameters:
            wav (np.ndarray): Audio waveform with float values in the range [-1, 1]
            path (str): Destination file path for the output WAV file
            sample_rate (int, optional): Audio sampling rate in Hz. Defaults to 16000.
        
        Notes:
            - Normalizes the waveform to 16-bit integer range before saving
            - Prevents division by zero by adding a small threshold
            - Uses scipy.io.wavfile for writing the WAV file
        """
        wav_norm = wav * (32767 / max(0.01, np.max(np.abs(wav))))
        wav_norm = wav_norm.astype(np.int16)
        scipy.io.wavfile.write(path, sample_rate, wav_norm)

    def synth(self, text: str, path: str):
        """
        Synthesize speech from input text and save the generated audio to a file.
        
        This method performs text-to-speech synthesis by converting the input text to an audio waveform
        and saving it to the specified file path.
        
        Parameters:
            text (str): The input text to be converted to speech.
            path (str): The file path where the generated audio will be saved.
        
        Note:
            - Uses the configured sample rate from the model configuration, defaulting to 16000 Hz if not specified.
            - Generates audio using the ONNX inference method and saves the first generated waveform.
        """
        wavs = self.inference_onnx(text)
        self.save_wav(wavs[0], path, self.config.get("sample_rate", 16000))
