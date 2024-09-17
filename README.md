## Description

OVOS TTS plugin for [NOS TTS](https://tts.nos.gal/)

## Install

`pip install ovos-tts-plugin-nos`

To use the `'sabela'` voice you also need to install `cotovia`, follow the steps in [ovos-tts-plugin-cotovia](https://github.com/OpenVoiceOS/ovos-tts-plugin-cotovia)

## Configuration

valid voices are  `'celtia'` and  `'sabela'`

```json
  "tts": {
    "module": "ovos-tts-plugin-nos",
    "ovos-tts-plugin-nos": {
      "voice": "celtia"
    }
  }
 
```

If using voice `sabela`, `bin` can be used to set a path to the `cotovia` executable (default `/usr/bin/cotovia`)

```json
  "tts": {
    "module": "ovos-tts-plugin-nos",
    "ovos-tts-plugin-nos": {
      "voice": "sabela",
      "bin": "/usr/bin/cotovia"
    }
   }
 
```


## Credits

<img src="img.png" width="128"/>

> This plugin was funded by the Ministerio para la Transformación Digital y de la Función Pública and Plan de Recuperación, Transformación y Resiliencia - Funded by EU – NextGenerationEU within the framework of the project ILENIA with reference 2022/TL22/00215337

<img src="img_1.png" width="64"/>

> This research was funded by [Proxecto Nós](https://github.com/proxectonos) - “The Nós project: Galician in the society and economy of Artificial Intelligence”, resulting from the agreement 2021-CP080 between the Xunta de Galicia and the University of Santiago de Compostela, and thanks to the Investigo program, within the National Recovery, Transformation and Resilience Plan, within the framework of the European Recovery Fund (NextGenerationEU).
