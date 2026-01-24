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

# Limpa diretório ao iniciar (evita confusão com jobs antigos)
if AUDIO_DIR.exists():
    try:
        shutil.rmtree(AUDIO_DIR)
        print("[Startup] Diretório temp limpo")
    except:
        pass
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
    
    def save_checkpoint(self, job_dir: Path):
        """Salva checkpoint do job para permitir resume"""
        checkpoint_file = job_dir / "checkpoint.json"
        try:
            checkpoint_data = {
                'job_id': self.job_id,
                'engine': self.engine,
                'voice_id': self.voice_id,
                'force_language': self.force_language,
                'status': self.status,
                'progress': self.progress,
                'total_blocks': self.total_blocks,
                'processed_blocks': self.processed_blocks,
                'audio_files': self.audio_files,
                'created_at': self.created_at.isoformat()
            }
            with open(checkpoint_file, 'w', encoding='utf-8') as f:
                import json
                json.dump(checkpoint_data, f, indent=2)
        except Exception as e:
            print(f"[Checkpoint] Aviso: Falha ao salvar: {e}")
    
    @staticmethod
    def load_checkpoint(job_dir: Path, blocks: list):
        """Carrega checkpoint existente se houver"""
        checkpoint_file = job_dir / "checkpoint.json"
        if checkpoint_file.exists():
            try:
                import json
                with open(checkpoint_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                print(f"[Checkpoint] Encontrado! {data['processed_blocks']}/{data['total_blocks']} blocos já gerados")
                return data
            except Exception as e:
                print(f"[Checkpoint] Erro ao carregar: {e}")
        return None
    
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
    """Processa os blocos de texto e gera áudios em paralelo"""
    try:
        print(f"\n[JOB {job.job_id[:8]}] Iniciando processamento...")
        print(f"  Engine: {job.engine}")
        print(f"  Voice: {job.voice_id}")
        print(f"  Blocos: {job.total_blocks}")
        
        job.status = "processing"
        job_dir = AUDIO_DIR / job.job_id
        job_dir.mkdir(exist_ok=True)
        print(f"  Diretório: {job_dir}")
        
        # Tenta carregar checkpoint existente
        checkpoint = TTSJob.load_checkpoint(job_dir, job.blocks)
        if checkpoint:
            job.audio_files = checkpoint.get('audio_files', [])
            job.processed_blocks = checkpoint.get('processed_blocks', 0)
            print(f"  [Checkpoint] Retomando do bloco {job.processed_blocks + 1}")
        
        # IMPORTANTE: Usa o tts_manager global (que tem as credenciais configuradas)
        # NÃO criar TTSManager() novo aqui pois perde as credenciais!
        
        # Configuração de paralelização
        MAX_WORKERS = 3  # Processa 3 blocos simultâneos
        semaphore = asyncio.Semaphore(MAX_WORKERS)
        
        async def process_single_block(i, block):
            """Processa um único bloco com retry e semáforo"""
            async with semaphore:  # Limita concorrência
                # Pula blocos já processados (checkpoint)
                output_path = str(job_dir / f"block_{i:04d}.mp3")
                if os.path.exists(output_path) and os.path.getsize(output_path) > 1000:
                    if output_path not in job.audio_files:
                        job.audio_files.append(output_path)
                        job.processed_blocks += 1
                    print(f"\n  [Bloco {i+1}/{job.total_blocks}] ✓ Já existe (pulado)")
                    return True

                text_preview = block['content'][:50] + "..." if len(block['content']) > 50 else block['content']
                print(f"\n  [Bloco {i+1}/{job.total_blocks}] {text_preview}")
                
                # Retry automático (até 3 tentativas)
                max_retries = 3
                retry_count = 0
                
                while retry_count < max_retries:
                    try:
                        result = await tts_manager.synthesize(
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
                                job.processed_blocks += 1
                                print(f"    ✓ Áudio gerado: {os.path.getsize(output_path)} bytes")
                                
                                # Salva checkpoint a cada bloco
                                job.save_checkpoint(job_dir)
                                return True
                            else:
                                raise Exception("Arquivo vazio ou não criado")
                        else:
                            raise Exception(result.error or "Erro desconhecido")
                            
                    except asyncio.TimeoutError:
                        retry_count += 1
                        if retry_count < max_retries:
                            wait_time = 2 ** retry_count
                            print(f"    ⚠ Timeout! Tentativa {retry_count}/{max_retries}. Aguardando {wait_time}s...")
                            await asyncio.sleep(wait_time)
                        else:
                            error_msg = f"Timeout após {max_retries} tentativas no bloco {i+1}"
                            print(f"    ✗ {error_msg}")
                            job.error = error_msg
                            job.status = "error"
                            job.save_checkpoint(job_dir)
                            return False
                            
                    except Exception as e:
                        retry_count += 1
                        if retry_count < max_retries:
                            print(f"    ⚠ Erro: {str(e)}. Tentativa {retry_count}/{max_retries}...")
                            await asyncio.sleep(2)
                        else:
                            error_msg = f"Erro ao sintetizar bloco {i+1}: {str(e)}"
                            print(f"    ✗ {error_msg}")
                            job.error = error_msg
                            job.status = "error"
                            job.save_checkpoint(job_dir)
                            return False
                
                return False
        
        # Processa todos os blocos em paralelo
        tasks = [process_single_block(i, block) for i, block in enumerate(job.blocks)]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Verifica se todos foram bem-sucedidos
        if job.status != "error" and all(r is True for r in results if isinstance(r, bool)):
            job.progress = 100
        
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
    
    # Credenciais Azure (opcional)
    azure_config = data.get('azure_config')
    print(f"[DEBUG] Engine: {engine}, azure_config: {azure_config is not None}")
    if azure_config and engine == 'azure':
        print(f"[DEBUG] Configurando Azure: region={azure_config.get('region')}, key=***{azure_config.get('apiKey', '')[-4:] if azure_config.get('apiKey') else 'NONE'}")
        azure_engine = tts_manager.get_engine('azure')
        azure_engine.set_credentials(
            api_key=azure_config.get('apiKey'),
            region=azure_config.get('region', 'eastus')
        )
    
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
