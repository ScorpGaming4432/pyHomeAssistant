# pyHomeAssistant

## Overview

This is a local project using open source solutions for a terminal Home Assistant app.

## Usage / Installation

```bash
git clone https://github.com/ScorpGaming4432/pyHomeAssistant.git
cd pyHomeAssistant
pip install -r requirements.txt
```

```bash
clang++ -std=C++17 ./mic-wav/audio_device.cpp ./mic-wav/wav.cpp -o audio_device
```



> (for now `new_main.py` is the only one working, but main.py will be updated soon)

## OS tested

### Windows

* [x] Windows 11
* [ ] Windows 10
* [ ] Windows 8
* [ ] Windows >7

### Linux* [ ] Ubuntu 22.04

* [ ] Ubuntu 20.04
* [ ] Debian 12
* [ ] Debian 11
* [ ] Fedora 38
* [ ] Fedora 37
* [ ] Arch Linux

### MacOS

* [ ] MacOS 14 Sonoma
* [ ] MacOS 13 Ventura
* [ ] MacOS 12 Monterey

## Features

* Voice control and readaloud for Home Assistant using Whisper and eSpeakNG with Mistune. (easily replaceable with other TTS engines)
* Terminal interface using Rich for a better TUI user experience.
* Easily switchable Ollama compatible models.
* Easy to extend and customize with Python.

## Dependencies

* Python 3.13
* rich
* ollama
* whisper
* eSpeakNG
* mistune
