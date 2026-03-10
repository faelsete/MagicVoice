# MagicVoice 🎤

**High-quality Text-to-Speech (TTS) conversion, simple and fast.**

Transform text into MP3 audio using neural voices. No registration, no limits, no complications.

![Python](https://img.shields.io/badge/Python-3.9+-blue.svg)
![Flask](https://img.shields.io/badge/Flask-2.3+-green.svg)
![License](https://img.shields.io/badge/License-MIT-yellow.svg)

## ✨ Features

- **Fast Conversion:** For short texts up to 9 minutes of audio. Paste the text, choose the voice, download the MP3.
- **Audiobook Mode:** For long texts. The system automatically divides the text into optimized blocks and generates a single MP3 file using parallel processing (`pydub`).
- **Multiple Engines:** Supports `edge-tts`, `gTTS`, and Azure Cognitive Services (optional).
- **Multi-language Support:** High-quality voices in English, Portuguese, Spanish, and Multilingual options.

## 🚀 Installation

### Windows / Linux / macOS

```bash
# Clone the repository
git clone https://github.com/faelsete/MagicVoice.git
cd MagicVoice

# Install dependencies
pip install -r requirements.txt

# Run the application
python app.py
```

Access: `http://localhost:5000`

## 📖 How to Use

1. Paste your text.
2. Choose language and voice.
3. Click "Generate Audio".
4. Download your MP3.

## 🎙️ Available Voices

- **English:** Guy, Jenny, Aria
- **Portuguese:** Antônio, Francisca, Thalita
- **Spanish:** Jorge, Dalia
- **Multilingual:** Ava, Andrew, Emma, Brian

## 🔒 Security

This application runs locally. If you choose to use the Azure integration, provide your API key in the configuration. We ensure no API keys or sensitive data are hardcoded in the public repository.

## 📝 License

MIT License - use freely.
Created by [Rafael Fernandes](https://github.com/faelsete).
