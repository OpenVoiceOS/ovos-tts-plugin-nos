> **This repository is archived. No further updates will be made.**
>
> The NOS/Proxecto Nós Galician voices have been absorbed into [phoonnx](https://github.com/TigreGotico/phoonnx), a unified ONNX TTS plugin. Migrate using the guide below.

# ovos-tts-plugin-nos → phoonnx migration

## Install

```bash
pip install phoonnx
```

For the cotovia-phonemized voices (`sabela`, `icia`, `iago`, `paulo`, `brais-cotovia`, `celtia-cotovia`), `cotovia` must be available in your base OS — same requirement as before. Follow the install steps in [ovos-tts-plugin-cotovia](https://github.com/OpenVoiceOS/ovos-tts-plugin-cotovia).

## Voice mapping

| Old voice | phoonnx voice id | Phonemizer |
|-----------|-----------------|------------|
| `celtia` | `proxectonos/celtia` | graphemes (no cotovia needed) |
| `sabela` | `proxectonos/sabela-cotovia` | cotovia |
| `icia` | `proxectonos/icia-cotovia` | cotovia |
| — | `proxectonos/brais` | graphemes (no cotovia needed) |
| — | `proxectonos/brais-cotovia` | cotovia |
| — | `proxectonos/celtia-cotovia` | cotovia |
| — | `proxectonos/paulo-cotovia` | cotovia |
| — | `proxectonos/iago-cotovia` | cotovia |

`proxectonos/celtia` and `proxectonos/brais` are recommended for systems without cotovia installed.

## Configuration mapping

**Before:**
```json
"tts": {
  "module": "ovos-tts-plugin-nos",
  "ovos-tts-plugin-nos": {
    "voice": "celtia"
  }
}
```

**After:**
```json
"tts": {
  "module": "ovos-tts-plugin-phoonnx",
  "ovos-tts-plugin-phoonnx": {
    "voice": "proxectonos/celtia"
  }
}
```

For a cotovia voice:
```json
"tts": {
  "module": "ovos-tts-plugin-phoonnx",
  "ovos-tts-plugin-phoonnx": {
    "voice": "proxectonos/sabela-cotovia"
  }
}
```

### Auto-select by language

Set your OVOS language to `gl-ES` and leave `voice` unset — phoonnx will select a Galician voice automatically.

## Voice catalogue

All available Galician voices (and every other supported voice) are listed in [VOICES.md](https://github.com/TigreGotico/phoonnx/blob/dev/VOICES.md) — that is the canonical reference for voice IDs to use in your config.

## Credits

This plugin was developed by [TigreGotico](https://tigregotico.pt) for OpenVoiceOS under the ILENIA project.

<img src="img.png" width="128"/>

> This plugin was funded by the Ministerio para la Transformación Digital y de la Función Pública and Plan de Recuperación, Transformación y Resiliencia - Funded by EU – NextGenerationEU within the framework of the project [ILENIA](https://proyectoilenia.es) with reference 2022/TL22/00215337

<img src="img_1.png" width="64"/>

> This research was funded by [Proxecto Nós](https://github.com/proxectonos) — "The Nós project: Galician in the society and economy of Artificial Intelligence", resulting from the agreement 2021-CP080 between the Xunta de Galicia and the University of Santiago de Compostela, and thanks to the Investigo program, within the National Recovery, Transformation and Resilience Plan, within the framework of the European Recovery Fund (NextGenerationEU).
