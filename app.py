"""
TTS Rapidim - Aplicação Flask Principal
Sistema de Text-to-Speech com vozes Azure (Edge TTS) e Google (gTTS)
"""

import os
import uuid
import asyncio
import tempfile
import shutil
from pathlib import Path
from datetime import datetime
from flask import Flask, render_template, request, jsonify, send_file
from threading import Thread
from dataclasses import asdict

from text_splitter import TextSplitter, split_text
from tts_engines import tts_manager, TTSManager
from audio_processor import audio_processor, AudioProcessor


app = Flask(__name__)
app.config['SECRET_KEY'] = os.urandom(24)

# Diretório para arquivos temporários de áudio
AUDIO_DIR = Path(tempfile.gettempdir()) / "tts_rapidim"
AUDIO_DIR.mkdir(exist_ok=True)

# Jobs em processamento (em produção usaria Redis ou similar)
jobs = {}


class TTSJob:
    """Representa um job de processamento TTS"""
    
    def __init__(self, job_id: str, blocks: list, engine: str, voice_id: str, 
                 force_language: str = None):
        self.job_id = job_id
        self.blocks = blocks
        self.engine = engine
        self.voice_id = voice_id
        self.force_language = force_language
        
        self.status = "pending"  # pending, processing, completed, error
        self.progress = 0
        self.total_blocks = len(blocks)
        self.processed_blocks = 0
        self.audio_files = []
        self.final_audio = None
        self.error = None
        self.created_at = datetime.now()
    
    def to_dict(self):
        return {
            'job_id': self.job_id,
            'status': self.status,
            'progress': self.progress,
            'total_blocks': self.total_blocks,
            'processed_blocks': self.processed_blocks,
            'final_audio': self.final_audio,
            'error': self.error
        }


def run_async(coro):
    """Executa coroutine em nova thread com event loop"""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


def process_job_async(job: TTSJob):
    """Processa job TTS em background"""
    run_async(_process_job(job))


async def _process_job(job: TTSJob):
    """Processa os blocos de texto e gera áudios"""
    try:
        print(f"\n[JOB {job.job_id[:8]}] Iniciando processamento...")
        print(f"  Engine: {job.engine}")
        print(f"  Voice: {job.voice_id}")
        print(f"  Blocos: {job.total_blocks}")
        
        job.status = "processing"
        job_dir = AUDIO_DIR / job.job_id
        job_dir.mkdir(exist_ok=True)
        print(f"  Diretório: {job_dir}")
        
        manager = TTSManager()
        
        for i, block in enumerate(job.blocks):
            # Se o job já estiver marcado como erro por outra thread ou verificação, para
            if job.status == "error":
                break

            text_preview = block['content'][:50] + "..." if len(block['content']) > 50 else block['content']
            print(f"\n  [Bloco {i+1}/{job.total_blocks}] {text_preview}")
            
            # Gera áudio para este bloco
            output_path = str(job_dir / f"block_{i:04d}.mp3")
            
            try:
                result = await manager.synthesize(
                    text=block['content'],
                    engine_name=job.engine,
                    voice_id=job.voice_id,
                    output_path=output_path,
                    force_language=job.force_language
                )
                
                if result.success:
                    # Verifica se o arquivo foi realmente criado
                    if os.path.exists(output_path) and os.path.getsize(output_path) > 0:
                        job.audio_files.append(output_path)
                        print(f"    ✓ Áudio gerado: {os.path.getsize(output_path)} bytes")
                    else:
                        error_msg = f"Arquivo de áudio vazio ou não criado para o bloco {i+1}"
                        print(f"    ✗ {error_msg}")
                        job.error = error_msg
                        job.status = "error"
                        break # Aborta processamento
                else:
                    error_msg = f"Erro ao sintetizar bloco {i+1}: {result.error}"
                    print(f"    ✗ {error_msg}")
                    job.error = error_msg
                    job.status = "error"
                    break # Aborta processamento
                    
            except Exception as block_error:
                error_msg = f"Exceção no bloco {i+1}: {str(block_error)}"
                print(f"    ✗ {error_msg}")
                job.error = error_msg
                job.status = "error"
                break # Aborta processamento
            
            job.processed_blocks = i + 1
            job.progress = int((job.processed_blocks / job.total_blocks) * 100)
        
        # Só prossegue para concatenação se NÃO houve erro
        if job.status != "error":
            print(f"\n  Áudios gerados: {len(job.audio_files)}/{job.total_blocks}")
            
            # Concatena todos os áudios
            if job.audio_files:
                processor = AudioProcessor(str(job_dir))
                final_path = str(job_dir / "final_output.mp3")
                
                print(f"  Concatenando áudios...")
                merge_result = processor.merge_audio_files_ffmpeg(
                    job.audio_files,
                    final_path,
                    gap_ms=300  # 300ms de pausa entre blocos
                )
                
                if merge_result.success:
                    if os.path.exists(final_path) and os.path.getsize(final_path) > 0:
                        job.final_audio = final_path
                        job.status = "completed"
                        print(f"  ✓ Áudio final: {os.path.getsize(final_path)} bytes")
                        print(f"[JOB {job.job_id[:8]}] CONCLUÍDO!")
                    else:
                        job.error = "Erro crítico: Arquivo final vazio."
                        job.status = "error"
                else:
                    job.error = merge_result.error
                    job.status = "error"
                    print(f"  ✗ Erro na concatenação: {merge_result.error}")
            else:
                job.error = "Nenhum áudio válido foi gerado. Tente outra voz."
                job.status = "error"
                print(f"[JOB {job.job_id[:8]}] ERRO: Nenhum áudio foi gerado")
        else:
            print(f"[JOB {job.job_id[:8]}] Processamento abortado devido a erro.")
            
    except Exception as e:
        import traceback
        job.error = f"Erro interno: {str(e)}"
        job.status = "error"
        print(f"[JOB {job.job_id[:8]}] EXCEÇÃO GERAL: {str(e)}")
        traceback.print_exc()


# ============ ROTAS ============

@app.route('/')
def index():
    """Página principal"""
    return render_template('index.html')


@app.route('/api/voices')
def get_voices():
    """Retorna todas as vozes disponíveis"""
    voices = tts_manager.get_voices_grouped()
    return jsonify(voices)


@app.route('/api/split-text', methods=['POST'])
def split_text_api():
    """Divide texto em blocos de 2500 caracteres"""
    data = request.json
    text = data.get('text', '')
    max_chars = data.get('max_chars', 2500)
    
    if not text:
        return jsonify({'error': 'Texto não fornecido'}), 400
    
    result = split_text(text, max_chars)
    
    # Converte para dict serializável
    blocks = []
    for block in result.blocks:
        blocks.append({
            'id': block.id,
            'content': block.content,
            'char_count': block.char_count,
            'warnings': block.warnings,
            'start_pos': block.start_pos,
            'end_pos': block.end_pos
        })
    
    return jsonify({
        'blocks': blocks,
        'total_chars': result.total_chars,
        'total_blocks': result.total_blocks
    })


@app.route('/api/process', methods=['POST'])
def process_text():
    """Inicia processamento TTS dos blocos"""
    data = request.json
    
    blocks = data.get('blocks', [])
    engine = data.get('engine', 'edge')
    voice_id = data.get('voice_id', 'pt-BR-FranciscaNeural')
    force_language = data.get('force_language')  # Para vozes multilingual
    
    if not blocks:
        return jsonify({'error': 'Nenhum bloco fornecido'}), 400
    
    # Cria job
    job_id = str(uuid.uuid4())
    job = TTSJob(job_id, blocks, engine, voice_id, force_language)
    jobs[job_id] = job
    
    # Inicia processamento em background
    thread = Thread(target=process_job_async, args=(job,))
    thread.start()
    
    return jsonify({
        'job_id': job_id,
        'status': 'started',
        'total_blocks': len(blocks)
    })


@app.route('/api/status/<job_id>')
def get_status(job_id):
    """Retorna status de um job"""
    job = jobs.get(job_id)
    
    if not job:
        return jsonify({'error': 'Job não encontrado'}), 404
    
    return jsonify(job.to_dict())


@app.route('/api/download/<job_id>')
def download_audio(job_id):
    """Download do áudio final"""
    job = jobs.get(job_id)
    
    if not job:
        return jsonify({'error': 'Job não encontrado'}), 404
    
    if job.status != 'completed':
        return jsonify({'error': 'Job ainda não foi concluído'}), 400
    
    if not job.final_audio or not os.path.exists(job.final_audio):
        return jsonify({'error': 'Arquivo de áudio não encontrado'}), 404
    
    # Gera nome amigável para download
    filename = f"tts_audio_{datetime.now().strftime('%Y%m%d_%H%M%S')}.mp3"
    
    return send_file(
        job.final_audio,
        mimetype='audio/mpeg',
        as_attachment=True,
        download_name=filename
    )


@app.route('/api/cleanup/<job_id>', methods=['DELETE'])
def cleanup_job(job_id):
    """Remove arquivos temporários de um job"""
    job = jobs.get(job_id)
    
    if job:
        job_dir = AUDIO_DIR / job_id
        if job_dir.exists():
            shutil.rmtree(job_dir)
        del jobs[job_id]
    
    return jsonify({'status': 'cleaned'})


if __name__ == '__main__':
    print("""
╔════════════════════════════════════════════════════════════╗
║                    TTS Rapidim v1.0                        ║
║      Text-to-Speech com Azure Edge TTS e Google TTS        ║
╠════════════════════════════════════════════════════════════╣
║  Acesse: http://localhost:5000                             ║
║  Pressione Ctrl+C para encerrar                            ║
╚════════════════════════════════════════════════════════════╝
    """)
    app.run(debug=True, port=5000)
