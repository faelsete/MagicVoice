"""
TTS Engines Module - Motores de Text-to-Speech (Edge TTS e Google TTS)
Suporta português BR, inglês US, espanhol latino, francês e multilingual
"""

import asyncio
import tempfile
import os
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import List, Optional, Dict
from pathlib import Path

import edge_tts
from gtts import gTTS


@dataclass
class Voice:
    """Representa uma voz disponível"""
    id: str
    name: str
    language: str
    language_code: str
    gender: str
    engine: str
    is_multilingual: bool = False


@dataclass
class TTSResult:
    """Resultado da síntese de voz"""
    success: bool
    audio_path: Optional[str]
    error: Optional[str]
    duration_seconds: float = 0


class TTSEngine(ABC):
    """Interface base para motores TTS"""
    
    @abstractmethod
    async def synthesize(self, text: str, voice_id: str, output_path: str, 
                         force_language: Optional[str] = None) -> TTSResult:
        """Sintetiza texto para áudio"""
        pass
    
    @abstractmethod
    def get_voices(self) -> List[Voice]:
        """Retorna lista de vozes disponíveis"""
        pass


class EdgeTTSEngine(TTSEngine):
    """Motor Edge TTS (Microsoft Azure Neural Voices - Gratuito)"""
    
    # Vozes disponíveis por idioma
    VOICES = {
        'pt-BR': [
            Voice('pt-BR-FranciscaNeural', 'Francisca', 'Português (Brasil)', 'pt-BR', 'Female', 'edge'),
            Voice('pt-BR-AntonioNeural', 'Antônio', 'Português (Brasil)', 'pt-BR', 'Male', 'edge'),
            Voice('pt-BR-ThalitaNeural', 'Thalita', 'Português (Brasil)', 'pt-BR', 'Female', 'edge'),
        ],
        'en-US': [
            Voice('en-US-JennyNeural', 'Jenny', 'English (US)', 'en-US', 'Female', 'edge'),
            Voice('en-US-GuyNeural', 'Guy', 'English (US)', 'en-US', 'Male', 'edge'),
            Voice('en-US-AriaNeural', 'Aria', 'English (US)', 'en-US', 'Female', 'edge'),
            Voice('en-US-DavisNeural', 'Davis', 'English (US)', 'en-US', 'Male', 'edge'),
        ],
        'es-MX': [
            Voice('es-MX-DaliaNeural', 'Dalia', 'Español (México)', 'es-MX', 'Female', 'edge'),
            Voice('es-MX-JorgeNeural', 'Jorge', 'Español (México)', 'es-MX', 'Male', 'edge'),
        ],
        'es-AR': [
            Voice('es-AR-ElenaNeural', 'Elena', 'Español (Argentina)', 'es-AR', 'Female', 'edge'),
            Voice('es-AR-TomasNeural', 'Tomas', 'Español (Argentina)', 'es-AR', 'Male', 'edge'),
        ],
        'fr-FR': [
            Voice('fr-FR-DeniseNeural', 'Denise', 'Français (France)', 'fr-FR', 'Female', 'edge'),
            Voice('fr-FR-HenriNeural', 'Henri', 'Français (France)', 'fr-FR', 'Male', 'edge'),
        ],
        'multilingual': [
            Voice('en-US-AvaMultilingualNeural', 'Ava Multilingual', 'Multilingual', 'multilingual', 'Female', 'edge', True),
            Voice('en-US-AndrewMultilingualNeural', 'Andrew Multilingual', 'Multilingual', 'multilingual', 'Male', 'edge', True),
            Voice('en-US-EmmaMultilingualNeural', 'Emma Multilingual', 'Multilingual', 'multilingual', 'Female', 'edge', True),
            Voice('en-US-BrianMultilingualNeural', 'Brian Multilingual', 'Multilingual', 'multilingual', 'Male', 'edge', True),
            Voice('en-US-JennyMultilingualNeural', 'Jenny Multilingual', 'Multilingual', 'multilingual', 'Female', 'edge', True),
            Voice('en-US-RyanMultilingualNeural', 'Ryan Multilingual', 'Multilingual', 'multilingual', 'Male', 'edge', True),
        ]
    }
    
    def get_voices(self) -> List[Voice]:
        """Retorna todas as vozes disponíveis"""
        voices = []
        for lang_voices in self.VOICES.values():
            voices.extend(lang_voices)
        return voices
    
    def get_voices_by_language(self, language_code: str) -> List[Voice]:
        """Retorna vozes de um idioma específico"""
        return self.VOICES.get(language_code, [])
    
    async def synthesize(self, text: str, voice_id: str, output_path: str,
                         force_language: Optional[str] = None) -> TTSResult:
        """
        Sintetiza texto usando Edge TTS.
        
        Args:
            text: Texto para sintetizar
            voice_id: ID da voz (ex: 'pt-BR-FranciscaNeural')
            output_path: Caminho para salvar o áudio
            force_language: Força idioma específico para vozes multilingual (SSML)
        """
        import asyncio
        
        try:
            print(f"    [EdgeTTS] Iniciando síntese: {voice_id}", flush=True)
            print(f"    [EdgeTTS] Texto: {len(text)} chars", flush=True)
            
            # Se força idioma, usa SSML
            if force_language:
                ssml_text = self._create_ssml(text, voice_id, force_language)
                communicate = edge_tts.Communicate(ssml_text, voice_id)
            else:
                communicate = edge_tts.Communicate(text, voice_id)
            
            # Timeout de 60 segundos para evitar hang infinito
            print(f"    [EdgeTTS] Conectando ao servidor Microsoft...", flush=True)
            await asyncio.wait_for(communicate.save(output_path), timeout=60.0)
            
            print(f"    [EdgeTTS] ✓ Síntese concluída", flush=True)
            
            return TTSResult(
                success=True,
                audio_path=output_path,
                error=None
            )
            
        except asyncio.TimeoutError:
            error_msg = "Timeout de 60s ao conectar com servidor Microsoft"
            print(f"    [EdgeTTS] ✗ {error_msg}", flush=True)
            return TTSResult(
                success=False,
                audio_path=None,
                error=error_msg
            )
        except Exception as e:
            print(f"    [EdgeTTS] ✗ Erro: {str(e)}", flush=True)
            return TTSResult(
                success=False,
                audio_path=None,
                error=str(e)
            )
    
    def _create_ssml(self, text: str, voice_id: str, language: str) -> str:
        """
        Cria SSML para forçar idioma em vozes multilingual.
        Isso "trava o sotaque" como no Balabolka.
        """
        # Escapa caracteres especiais XML
        text = text.replace('&', '&amp;')
        text = text.replace('<', '&lt;')
        text = text.replace('>', '&gt;')
        text = text.replace('"', '&quot;')
        text = text.replace("'", '&apos;')
        
        ssml = f'''<speak version="1.0" xmlns="http://www.w3.org/2001/10/synthesis" xml:lang="{language}">
    <voice name="{voice_id}">
        <lang xml:lang="{language}">
            {text}
        </lang>
    </voice>
</speak>'''
        return ssml


class GoogleTTSEngine(TTSEngine):
    """Motor Google TTS (gTTS - Gratuito)"""
    
    VOICES = {
        'pt-BR': [Voice('pt-BR', 'Google BR', 'Português (Brasil)', 'pt-BR', 'Neutral', 'google')],
        'en-US': [Voice('en-US', 'Google US', 'English (US)', 'en-US', 'Neutral', 'google')],
        'es-MX': [Voice('es-MX', 'Google MX', 'Español (México)', 'es-MX', 'Neutral', 'google')],
        'es-ES': [Voice('es-ES', 'Google ES', 'Español (España)', 'es-ES', 'Neutral', 'google')],
        'fr-FR': [Voice('fr-FR', 'Google FR', 'Français (France)', 'fr-FR', 'Neutral', 'google')],
    }
    
    def get_voices(self) -> List[Voice]:
        """Retorna todas as vozes disponíveis"""
        voices = []
        for lang_voices in self.VOICES.values():
            voices.extend(lang_voices)
        return voices
    
    async def synthesize(self, text: str, voice_id: str, output_path: str,
                         force_language: Optional[str] = None) -> TTSResult:
        """
        Sintetiza texto usando Google TTS.
        
        Args:
            text: Texto para sintetizar
            voice_id: Código do idioma (ex: 'pt-BR')
            output_path: Caminho para salvar o áudio
            force_language: Não usado no gTTS (já é baseado em idioma)
        """
        try:
            # gTTS usa códigos de idioma simples
            lang = voice_id.split('-')[0]  # 'pt-BR' -> 'pt'
            tld = 'com.br' if 'BR' in voice_id else 'com'
            
            # Executa em thread separada (gTTS é síncrono)
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(
                None,
                self._synthesize_sync,
                text, lang, tld, output_path
            )
            
            return TTSResult(
                success=True,
                audio_path=output_path,
                error=None
            )
            
        except Exception as e:
            return TTSResult(
                success=False,
                audio_path=None,
                error=str(e)
            )
    
    def _synthesize_sync(self, text: str, lang: str, tld: str, output_path: str):
        """Síntese síncrona do gTTS"""
        tts = gTTS(text=text, lang=lang, tld=tld)
        tts.save(output_path)


class TTSManager:
    """Gerenciador de motores TTS"""
    
    def __init__(self):
        self.engines: Dict[str, TTSEngine] = {
            'edge': EdgeTTSEngine(),
            'google': GoogleTTSEngine()
        }
    
    def get_engine(self, engine_name: str) -> TTSEngine:
        """Retorna um motor TTS pelo nome"""
        if engine_name not in self.engines:
            raise ValueError(f"Motor TTS '{engine_name}' não encontrado. Disponíveis: {list(self.engines.keys())}")
        return self.engines[engine_name]
    
    def get_all_voices(self) -> Dict[str, List[Voice]]:
        """Retorna todas as vozes de todos os motores"""
        all_voices = {}
        for engine_name, engine in self.engines.items():
            all_voices[engine_name] = engine.get_voices()
        return all_voices
    
    def get_voices_grouped(self) -> Dict[str, Dict[str, List[dict]]]:
        """Retorna vozes agrupadas por engine e idioma (para JSON)"""
        result = {}
        
        for engine_name, engine in self.engines.items():
            result[engine_name] = {}
            voices = engine.get_voices()
            
            for voice in voices:
                lang = voice.language_code
                if lang not in result[engine_name]:
                    result[engine_name][lang] = []
                
                result[engine_name][lang].append({
                    'id': voice.id,
                    'name': voice.name,
                    'language': voice.language,
                    'gender': voice.gender,
                    'is_multilingual': voice.is_multilingual
                })
        
        return result
    
    async def synthesize(self, text: str, engine_name: str, voice_id: str, 
                         output_path: str, force_language: Optional[str] = None) -> TTSResult:
        """Sintetiza texto usando o motor e voz especificados"""
        engine = self.get_engine(engine_name)
        return await engine.synthesize(text, voice_id, output_path, force_language)


# Instância global
tts_manager = TTSManager()


# Teste rápido
if __name__ == "__main__":
    async def test():
        manager = TTSManager()
        
        # Lista vozes
        print("=== Vozes Disponíveis ===")
        for engine_name, voices in manager.get_all_voices().items():
            print(f"\n{engine_name.upper()}:")
            for voice in voices:
                ml = " (Multilingual)" if voice.is_multilingual else ""
                print(f"  - {voice.id}: {voice.name} ({voice.language}){ml}")
        
        # Teste de síntese
        print("\n=== Teste de Síntese ===")
        
        # Edge TTS
        result = await manager.synthesize(
            "Olá, este é um teste do sistema de texto para fala.",
            "edge",
            "pt-BR-FranciscaNeural",
            "test_edge.mp3"
        )
        print(f"Edge TTS: {'✓ Sucesso' if result.success else '✗ Erro: ' + result.error}")
        
        # Edge TTS com idioma forçado (multilingual)
        result = await manager.synthesize(
            "Este texto em português será lido pela voz multilingual.",
            "edge",
            "en-US-JennyMultilingualNeural",
            "test_multilingual.mp3",
            force_language="pt-BR"
        )
        print(f"Edge TTS Multilingual: {'✓ Sucesso' if result.success else '✗ Erro: ' + result.error}")
        
        # Google TTS
        result = await manager.synthesize(
            "Olá, este é um teste do Google TTS.",
            "google",
            "pt-BR",
            "test_google.mp3"
        )
        print(f"Google TTS: {'✓ Sucesso' if result.success else '✗ Erro: ' + result.error}")
    
    asyncio.run(test())
