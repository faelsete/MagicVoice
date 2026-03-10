# MagicVoice 🎤

**उच्च गुणवत्ता वाला टेक्स्ट-टू-स्पीच, सरल और तेज़।**

न्यूरल वॉयस का उपयोग करके टेक्स्ट को MP3 ऑडियो में बदलें। कोई पंजीकरण नहीं, कोई सीमा नहीं।

## ✨ विशेषताएं

- **त्वरित रूपांतरण:** छोटे ग्रंथों के लिए। टेक्स्ट पेस्ट करें, आवाज़ चुनें, MP3 डाउनलोड करें।
- **ऑडियोबुक मोड:** लंबे ग्रंथों के लिए। सिस्टम स्वचालित रूप से ब्लॉकों में विभाजित होता है और समानांतर प्रसंस्करण (`pydub`) का उपयोग करके एक एकल MP3 फ़ाइल उत्पन्न करता है।
- **एकाधिक इंजन:** `edge-tts`, `gTTS`, और Azure Cognitive Services (वैकल्पिक) का समर्थन करता है।

## 🚀 स्थापना

```bash
git clone https://github.com/faelsete/MagicVoice.git
cd MagicVoice
pip install -r requirements.txt
python app.py
```

## 📝 लाइसेंस
MIT License. [Rafael Fernandes](https://github.com/faelsete) द्वारा निर्मित।
