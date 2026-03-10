# MagicVoice 🎤

**Texto para áudio de alta qualidade, simples e rápido.**

Transforme textos em áudio MP3 usando vozes neurais. Sem cadastro, sem limites, sem complicação.

![Python](https://img.shields.io/badge/Python-3.9+-blue.svg)
![Flask](https://img.shields.io/badge/Flask-2.3+-green.svg)
![License](https://img.shields.io/badge/License-MIT-yellow.svg)

## ✨ Funcionalidades

- **Conversão Rápida:** Para textos curtos até 9 minutos de áudio. Cole o texto, escolha a voz, baixe o MP3.
- **Modo Audiolivro:** Para textos longos. O sistema divide automaticamente em blocos otimizados e gera um único arquivo MP3 usando processamento paralelo (`pydub`).
- **Múltiplos Motores:** Suporta `edge-tts`, `gTTS` e Azure Cognitive Services (opcional).
- **Suporte Multilíngue:** Vozes de alta qualidade em Português, Inglês, Espanhol e opções multilíngues.

## 🚀 Instalação

### Windows / Linux / macOS

```bash
# Clone o repositório
git clone https://github.com/faelsete/MagicVoice.git
cd MagicVoice

# Instale as dependências
pip install -r requirements.txt

# Execute a aplicação
python app.py
```

Acesse: `http://localhost:5000`

## 📖 Como Usar

1. Cole seu texto.
2. Escolha o idioma e a voz.
3. Clique em "Gerar Áudio".
4. Baixe seu MP3.

## 📝 Licença

MIT License - use livremente.
Criado por [Rafael Fernandes](https://github.com/faelsete).
