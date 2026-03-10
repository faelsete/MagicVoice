# MagicVoice 🎤

**Conversión de texto a voz de alta calidad, simple y rápida.**

Transforma texto en audio MP3 usando voces neuronales. Sin registro, sin límites, sin complicaciones.

## ✨ Características

- **Conversión Rápida:** Para textos cortos de hasta 9 minutos. Pega el texto, elige la voz, descarga el MP3.
- **Modo Audiolibro:** Para textos largos. El sistema divide automáticamente en bloques optimizados y genera un solo archivo MP3 usando procesamiento paralelo (`pydub`).
- **Múltiples Motores:** Soporta `edge-tts`, `gTTS` y Azure Cognitive Services (opcional).

## 🚀 Instalación

```bash
git clone https://github.com/faelsete/MagicVoice.git
cd MagicVoice
pip install -r requirements.txt
python app.py
```

## 📝 Licencia
MIT License. Creado por [Rafael Fernandes](https://github.com/faelsete).
