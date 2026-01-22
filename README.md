# TTS Rapidim 🎤

**Text-to-Speech gratuito e de alta qualidade com Microsoft Edge TTS e Google TTS.**

Uma aplicação web simples e eficiente para converter textos longos em áudio MP3, usando vozes neurais da Microsoft (Azure) e Google - sem custo, sem limites, sem API key.

![Python](https://img.shields.io/badge/Python-3.9+-blue.svg)
![Flask](https://img.shields.io/badge/Flask-2.3+-green.svg)
![License](https://img.shields.io/badge/License-MIT-yellow.svg)

## ✨ Funcionalidades

- **Vozes Neurais de Alta Qualidade** - Microsoft Edge TTS (Azure Neural Voices)
- **Múltiplos Idiomas** - Português, Inglês, Espanhol, Francês
- **Vozes Multilíngues** - Falam qualquer idioma com sotaque natural
- **Corte Inteligente** - Divide textos longos automaticamente em blocos de até 2500 caracteres
- **Editor de Blocos** - Edite, adicione ou remova blocos antes de processar
- **Concatenação Automática** - Junta todos os blocos em um único arquivo MP3
- **100% Gratuito** - Sem limites de uso, sem API keys

## 🚀 Instalação

### Pré-requisitos

- Python 3.9 ou superior
- FFmpeg instalado no sistema

### Instalação Rápida

```bash
# Clone o repositório
git clone https://github.com/seu-usuario/tts-rapidim.git
cd tts-rapidim

# Crie um ambiente virtual (recomendado)
python -m venv .venv
.venv\Scripts\activate  # Windows
# source .venv/bin/activate  # Linux/Mac

# Instale as dependências
pip install -r requirements.txt
```

### Instalação FFmpeg (Windows)

1. Baixe o FFmpeg: https://ffmpeg.org/download.html
2. Extraia e adicione a pasta `bin` ao PATH do sistema

## 📖 Uso

### Iniciar o Servidor

**Windows:**
```bash
iniciar.bat
```

**Linux/Mac:**
```bash
python app.py
```

Acesse: http://localhost:5000

### Como Usar

1. Cole seu texto na área de entrada
2. Clique em "Cortar Texto em Blocos"
3. Revise os blocos (edite se necessário)
4. Selecione a voz desejada
5. Clique em "Processar Áudio"
6. Baixe seu MP3!

## 🎙️ Vozes Disponíveis

### Português (Brasil)
- Francisca (Feminina)
- Antônio (Masculino)
- Thalita (Feminina)

### Inglês (EUA)
- Jenny, Aria (Femininas)
- Guy, Davis (Masculinos)

### Multilíngues
- Ava, Emma, Jenny (Femininas)
- Andrew, Brian, Ryan (Masculinos)

## 📁 Estrutura do Projeto

```
tts-rapidim/
├── app.py              # Servidor Flask principal
├── tts_engines.py      # Motores TTS (Edge, Google)
├── audio_processor.py  # Processamento e concatenação de áudio
├── text_splitter.py    # Divisão inteligente de texto
├── iniciar.bat         # Script de inicialização (Windows)
├── requirements.txt    # Dependências Python
├── static/
│   ├── app.js          # Frontend JavaScript
│   └── style.css       # Estilos CSS
└── templates/
    └── index.html      # Interface HTML
```

## 🛠️ Tecnologias

- **Backend:** Flask, Python 3.9+
- **TTS:** edge-tts (Microsoft), gTTS (Google)
- **Áudio:** PyDub, FFmpeg
- **Frontend:** HTML5, CSS3, JavaScript

## 📝 Licença

Este projeto está licenciado sob a [MIT License](LICENSE).

## 🤝 Contribuindo

Contribuições são bem-vindas! Sinta-se à vontade para abrir issues ou pull requests.

---

Feito com ❤️ para a comunidade brasileira.
