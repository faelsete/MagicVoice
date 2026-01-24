"""
Audio Processor Module - Concatena arquivos de áudio e exporta MP3 final
"""

import os
import tempfile
from pathlib import Path
from typing import List, Optional
from dataclasses import dataclass

from pydub import AudioSegment


@dataclass
class AudioFile:
    """Representa um arquivo de áudio"""
    path: str
    block_id: int
    duration_ms: int = 0


@dataclass
class MergeResult:
    """Resultado da concatenação de áudios"""
    success: bool
    output_path: Optional[str]
    total_duration_ms: int
    error: Optional[str]


class AudioProcessor:
    """Processador de áudio para concatenação e conversão"""
    
    def __init__(self, output_dir: str = None):
        self.output_dir = output_dir or tempfile.gettempdir()
        os.makedirs(self.output_dir, exist_ok=True)
    
    def get_duration(self, audio_path: str) -> int:
        """Retorna duração do áudio em milissegundos"""
        try:
            audio = AudioSegment.from_file(audio_path)
            return len(audio)
        except Exception:
            return 0
    
    def merge_audio_files(self, audio_files: List[str], output_path: str,
                          gap_ms: int = 500, format: str = "mp3") -> MergeResult:
        """
        Concatena múltiplos arquivos de áudio em um único arquivo.
        
        Args:
            audio_files: Lista de caminhos dos arquivos de áudio (em ordem)
            output_path: Caminho para salvar o áudio final
            gap_ms: Intervalo de silêncio entre blocos (em ms)
            format: Formato de saída (mp3, wav, etc)
        
        Returns:
            MergeResult com informações do resultado
        """
        if not audio_files:
            return MergeResult(
                success=False,
                output_path=None,
                total_duration_ms=0,
                error="Nenhum arquivo de áudio fornecido"
            )
        
        try:
            # Inicia com silêncio vazio
            combined = AudioSegment.empty()
            silence = AudioSegment.silent(duration=gap_ms)
            
            for i, audio_path in enumerate(audio_files):
                if not os.path.exists(audio_path):
                    print(f"Aviso: Arquivo não encontrado: {audio_path}")
                    continue
                
                # Carrega o áudio
                audio = AudioSegment.from_file(audio_path)
                
                # Adiciona ao combinado
                if i > 0:
                    combined += silence  # Adiciona silêncio entre blocos
                combined += audio
            
            if len(combined) == 0:
                return MergeResult(
                    success=False,
                    output_path=None,
                    total_duration_ms=0,
                    error="Nenhum áudio válido para concatenar"
                )
            
            # Exporta para MP3
            combined.export(
                output_path,
                format=format,
                bitrate="192k",
                tags={
                    'title': 'TTS Rapidim Audio',
                    'artist': 'TTS Rapidim',
                    'album': 'Text to Speech'
                }
            )
            
            return MergeResult(
                success=True,
                output_path=output_path,
                total_duration_ms=len(combined),
                error=None
            )
            
        except Exception as e:
            return MergeResult(
                success=False,
                output_path=None,
                total_duration_ms=0,
                error=str(e)
            )
    
    def merge_audio_files_ffmpeg(self, audio_files: List[str], output_path: str,
                                  gap_ms: int = 500) -> MergeResult:
        """
        Concatena múltiplos arquivos de áudio usando ffmpeg diretamente.
        Versão robusta com melhor tratamento de erros para Windows.
        """
        import subprocess
        import tempfile
        
        if not audio_files:
            return MergeResult(
                success=False,
                output_path=None,
                total_duration_ms=0,
                error="Nenhum arquivo de áudio fornecido"
            )
        
        # Se só tem 1 arquivo, copia diretamente
        if len(audio_files) == 1:
            import shutil
            try:
                shutil.copy(audio_files[0], output_path)
                return MergeResult(
                    success=True,
                    output_path=output_path,
                    total_duration_ms=0,
                    error=None
                )
            except Exception as e:
                return MergeResult(
                    success=False,
                    output_path=None,
                    total_duration_ms=0,
                    error=f"Erro ao copiar arquivo único: {str(e)}"
                )
        
        # Múltiplos arquivos - usa ffmpeg concat
        list_file_path = None
        try:
            # Valida arquivos existentes
            valid_files = []
            for audio_path in audio_files:
                if os.path.exists(audio_path):
                    valid_files.append(audio_path)
                else:
                    print(f"    [FFmpeg] AVISO: Arquivo faltando: {audio_path}", flush=True)
            
            if not valid_files:
                return MergeResult(
                    success=False,
                    output_path=None,
                    total_duration_ms=0,
                    error="Nenhum arquivo válido encontrado para concatenar"
                )
            
            print(f"    [FFmpeg] Concatenando {len(valid_files)} arquivos válidos...", flush=True)
            
            # Cria arquivo de lista temporário
            # IMPORTANTE: use mode='w', encoding='utf-8', delete=False
            with tempfile.NamedTemporaryFile(mode='w', encoding='utf-8', suffix='.txt', delete=False) as list_file:
                list_file_path = list_file.name
                for audio_path in valid_files:
                    # Normaliza path para Windows e converte para forward slashes (ffmpeg prefere)
                    normalized_path = os.path.abspath(audio_path).replace('\\', '/')
                    # Escapa aspas simples
                    escaped_path = normalized_path.replace("'", "'\\\\''")
                    list_file.write(f"file '{escaped_path}'\n")
            
            # Comando ffmpeg usando concat demuxer
            cmd = [
                "ffmpeg", "-y",
                "-f", "concat",
                "-safe", "0",
                "-i", list_file_path,
                "-c", "copy",
                output_path
            ]
            
            # Executa ffmpeg com timeout de 5 minutos
            print(f"    [FFmpeg] Executando comando...", flush=True)
            result = subprocess.run(
                cmd, 
                capture_output=True, 
                text=True, 
                timeout=300,  # 5 minutos
                errors='replace'  # Trata encoding errors
            )
            
            # Limpa arquivo temporário
            if list_file_path and os.path.exists(list_file_path):
                os.unlink(list_file_path)
            
            # Verifica sucesso
            if result.returncode == 0 and os.path.exists(output_path) and os.path.getsize(output_path) > 0:
                size = os.path.getsize(output_path)
                print(f"    [FFmpeg] ✓ Arquivo final: {size / 1024 / 1024:.2f} MB", flush=True)
                return MergeResult(
                    success=True,
                    output_path=output_path,
                    total_duration_ms=0,
                    error=None
                )
            else:
                # Captura erro (limita a 1000 chars)
                error_msg = result.stderr[:1000] if result.stderr else "FFmpeg falhou sem mensagem"
                print(f"    [FFmpeg] ✗ returncode={result.returncode}", flush=True)
                print(f"    [FFmpeg] ✗ Erro: {error_msg[:200]}", flush=True)
                return MergeResult(
                    success=False,
                    output_path=None,
                    total_duration_ms=0,
                    error=f"FFmpeg error (code {result.returncode}): {error_msg[:300]}"
                )
                
        except subprocess.TimeoutExpired:
            error_msg = "FFmpeg timeout - arquivo muito grande (>5min de processamento)"
            print(f"    [FFmpeg] ✗ {error_msg}", flush=True)
            if list_file_path and os.path.exists(list_file_path):
                os.unlink(list_file_path)
            return MergeResult(
                success=False,
                output_path=None,
                total_duration_ms=0,
                error=error_msg
            )
        except Exception as e:
            error_msg = f"Exceção em merge_audio_files_ffmpeg: {type(e).__name__}: {str(e)}"
            print(f"    [FFmpeg] ✗ {error_msg}", flush=True)
            if list_file_path and os.path.exists(list_file_path):
                try:
                    os.unlink(list_file_path)
                except:
                    pass
            return MergeResult(
                success=False,
                output_path=None,
                total_duration_ms=0,
                error=error_msg
            )
    
    def convert_to_mp3(self, input_path: str, output_path: str = None,
                       bitrate: str = "192k") -> Optional[str]:
        """
        Converte um arquivo de áudio para MP3.
        
        Args:
            input_path: Caminho do arquivo de entrada
            output_path: Caminho de saída (opcional)
            bitrate: Bitrate do MP3
        
        Returns:
            Caminho do arquivo MP3 ou None se falhar
        """
        try:
            if output_path is None:
                output_path = str(Path(input_path).with_suffix('.mp3'))
            
            audio = AudioSegment.from_file(input_path)
            audio.export(output_path, format="mp3", bitrate=bitrate)
            
            return output_path
        except Exception as e:
            print(f"Erro ao converter para MP3: {e}")
            return None
    
    def normalize_audio(self, audio_path: str, target_dbfs: float = -20.0) -> bool:
        """
        Normaliza o volume do áudio para um nível consistente.
        
        Args:
            audio_path: Caminho do arquivo de áudio
            target_dbfs: Nível de volume alvo em dBFS
        
        Returns:
            True se sucesso, False se falhar
        """
        try:
            audio = AudioSegment.from_file(audio_path)
            
            # Calcula a diferença necessária
            change_in_dbfs = target_dbfs - audio.dBFS
            
            # Aplica a normalização
            normalized = audio.apply_gain(change_in_dbfs)
            
            # Sobrescreve o arquivo
            normalized.export(audio_path, format=Path(audio_path).suffix[1:])
            
            return True
        except Exception as e:
            print(f"Erro ao normalizar áudio: {e}")
            return False
    
    def get_audio_info(self, audio_path: str) -> dict:
        """Retorna informações sobre um arquivo de áudio"""
        try:
            audio = AudioSegment.from_file(audio_path)
            
            return {
                'path': audio_path,
                'duration_ms': len(audio),
                'duration_formatted': self._format_duration(len(audio)),
                'channels': audio.channels,
                'sample_rate': audio.frame_rate,
                'size_bytes': os.path.getsize(audio_path)
            }
        except Exception as e:
            return {
                'path': audio_path,
                'error': str(e)
            }
    
    def _format_duration(self, ms: int) -> str:
        """Formata duração de ms para MM:SS"""
        seconds = ms // 1000
        minutes = seconds // 60
        seconds = seconds % 60
        return f"{minutes:02d}:{seconds:02d}"


# Instância global
audio_processor = AudioProcessor()


# Teste rápido
if __name__ == "__main__":
    processor = AudioProcessor()
    
    # Teste com arquivos de exemplo (se existirem)
    test_files = ["test_edge.mp3", "test_google.mp3"]
    existing_files = [f for f in test_files if os.path.exists(f)]
    
    if existing_files:
        print("=== Teste de Concatenação ===")
        result = processor.merge_audio_files(
            existing_files,
            "test_combined.mp3",
            gap_ms=500
        )
        
        if result.success:
            print(f"✓ Sucesso! Arquivo: {result.output_path}")
            print(f"  Duração total: {processor._format_duration(result.total_duration_ms)}")
            
            info = processor.get_audio_info(result.output_path)
            print(f"  Canais: {info.get('channels')}")
            print(f"  Sample rate: {info.get('sample_rate')}")
        else:
            print(f"✗ Erro: {result.error}")
    else:
        print("Nenhum arquivo de teste encontrado. Execute tts_engines.py primeiro.")
