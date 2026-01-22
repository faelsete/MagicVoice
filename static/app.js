/**
 * TTS Rapidim - Frontend JavaScript
 * Editor de blocos interativo com drag-and-drop
 */

// ============ STATE ============

let voices = {};
let blocks = [];
let currentJobId = null;
let pollInterval = null;
let blocksExpanded = false; // Estado de expansão dos blocos

// ============ INITIALIZATION ============

document.addEventListener('DOMContentLoaded', async () => {
    // Carrega vozes disponíveis
    await loadVoices();

    // Event listeners
    document.getElementById('inputText').addEventListener('input', updateCharCount);
    document.getElementById('engineSelect').addEventListener('change', updateVoiceOptions);
    document.getElementById('languageSelect').addEventListener('change', updateVoiceOptions);
    document.getElementById('languageSelect').addEventListener('change', toggleMultilingualOptions);

    // Inicializa
    updateCharCount();
    toggleMultilingualOptions();
});

// ============ VOICES ============

async function loadVoices() {
    try {
        const response = await fetch('/api/voices');
        voices = await response.json();
        updateVoiceOptions();
    } catch (error) {
        console.error('Erro ao carregar vozes:', error);
    }
}

function updateVoiceOptions() {
    const engine = document.getElementById('engineSelect').value;
    const language = document.getElementById('languageSelect').value;
    const voiceSelect = document.getElementById('voiceSelect');

    voiceSelect.innerHTML = '';

    if (voices[engine] && voices[engine][language]) {
        voices[engine][language].forEach(voice => {
            const option = document.createElement('option');
            option.value = voice.id;
            option.textContent = `${voice.gender === 'Female' ? '👩' : voice.gender === 'Male' ? '👨' : '🔊'} ${voice.name}`;
            voiceSelect.appendChild(option);
        });
    } else {
        // Fallback
        const option = document.createElement('option');
        option.value = language;
        option.textContent = '🔊 Voz padrão';
        voiceSelect.appendChild(option);
    }
}

function toggleMultilingualOptions() {
    const language = document.getElementById('languageSelect').value;
    const multiOptions = document.getElementById('multilingualOptions');

    if (language === 'multilingual') {
        multiOptions.style.display = 'flex';
    } else {
        multiOptions.style.display = 'none';
    }
}

// ============ TEXT SPLITTING ============

function updateCharCount() {
    const text = document.getElementById('inputText').value;
    document.getElementById('charCount').textContent = text.length.toLocaleString();
}

async function splitText() {
    const text = document.getElementById('inputText').value.trim();

    if (!text) {
        alert('Por favor, cole um texto para converter.');
        return;
    }

    try {
        const response = await fetch('/api/split-text', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ text, max_chars: 2500 })
        });

        const data = await response.json();

        if (data.error) {
            alert('Erro: ' + data.error);
            return;
        }

        blocks = data.blocks;
        renderBlocks();

        // Mostra step 2
        document.getElementById('step2').classList.remove('hidden');
        document.getElementById('step2').scrollIntoView({ behavior: 'smooth' });

        // Atualiza stats
        document.getElementById('blockStats').textContent =
            `${data.total_blocks} blocos • ${data.total_chars.toLocaleString()} caracteres`;

    } catch (error) {
        console.error('Erro ao dividir texto:', error);
        alert('Erro ao processar texto: ' + error.message);
    }
}

// ============ BLOCK EDITOR ============

function renderBlocks() {
    const container = document.getElementById('blocksContainer');
    container.innerHTML = '';

    blocks.forEach((block, index) => {
        const card = createBlockCard(block, index);
        container.appendChild(card);
    });

    initDragAndDrop();

    // Reseta o estado de expansão
    blocksExpanded = false;
    const btn = document.getElementById('toggleExpandBtn');
    if (btn) btn.textContent = '📖 Expandir Blocos';
}

function createBlockCard(block, index) {
    const card = document.createElement('div');
    card.className = 'block-card';
    card.draggable = true;
    card.dataset.index = index;

    const hasWarnings = block.warnings && block.warnings.length > 0;

    card.innerHTML = `
        <div class="block-header">
            <span class="block-number">Bloco ${index + 1}</span>
            <span class="block-chars">${block.char_count.toLocaleString()} / 2500 caracteres</span>
            <div class="block-actions">
                <button onclick="editBlock(${index})" title="Editar">✏️</button>
                <button onclick="duplicateBlock(${index})" title="Duplicar">📋</button>
                <button onclick="deleteBlock(${index})" title="Remover">🗑️</button>
            </div>
        </div>
        <div class="block-content" id="content-${index}" onclick="toggleExpand(${index})">
            ${escapeHtml(block.content)}
        </div>
        ${hasWarnings ? `
        <div class="block-warnings">
            ${block.warnings.map(w => `<div class="warning-item">${w}</div>`).join('')}
        </div>
        ` : ''}
    `;

    return card;
}

function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

function toggleExpand(index) {
    const content = document.getElementById(`content-${index}`);
    content.classList.toggle('expanded');
}

function toggleExpandAll() {
    blocksExpanded = !blocksExpanded;
    const btn = document.getElementById('toggleExpandBtn');

    // Atualiza todos os blocos
    const allContents = document.querySelectorAll('.block-content');
    allContents.forEach(content => {
        if (blocksExpanded) {
            content.classList.add('expanded');
        } else {
            content.classList.remove('expanded');
        }
    });

    // Atualiza texto do botão
    if (blocksExpanded) {
        btn.textContent = '📕 Retrair Blocos';
    } else {
        btn.textContent = '📖 Expandir Blocos';
    }
}

function editBlock(index) {
    const block = blocks[index];
    const card = document.querySelector(`.block-card[data-index="${index}"]`);
    const contentDiv = card.querySelector('.block-content');

    // Substitui por textarea
    const currentContent = block.content;
    contentDiv.outerHTML = `
        <textarea class="block-textarea" id="edit-${index}" 
            onblur="saveBlock(${index})">${escapeHtml(currentContent)}</textarea>
    `;

    const textarea = document.getElementById(`edit-${index}`);
    textarea.focus();
    textarea.setSelectionRange(textarea.value.length, textarea.value.length);
}

function saveBlock(index) {
    const textarea = document.getElementById(`edit-${index}`);
    if (!textarea) return;

    const newContent = textarea.value.trim();
    blocks[index].content = newContent;
    blocks[index].char_count = newContent.length;

    // Re-render blocks
    renderBlocks();
}

function addBlock() {
    const newBlock = {
        id: blocks.length + 1,
        content: 'Novo bloco - clique para editar',
        char_count: 30,
        warnings: [],
        start_pos: 0,
        end_pos: 0
    };

    blocks.push(newBlock);
    renderBlocks();

    // Edita o novo bloco automaticamente
    setTimeout(() => editBlock(blocks.length - 1), 100);
}

function deleteBlock(index) {
    if (blocks.length <= 1) {
        alert('Você precisa ter pelo menos um bloco.');
        return;
    }

    if (confirm('Remover este bloco?')) {
        blocks.splice(index, 1);
        // Renumera
        blocks.forEach((b, i) => b.id = i + 1);
        renderBlocks();
    }
}

function duplicateBlock(index) {
    const block = { ...blocks[index] };
    block.id = blocks.length + 1;
    blocks.splice(index + 1, 0, block);
    // Renumera
    blocks.forEach((b, i) => b.id = i + 1);
    renderBlocks();
}

function resetBlocks() {
    if (confirm('Recortar o texto original novamente?')) {
        splitText();
    }
}

// ============ DRAG AND DROP ============

function initDragAndDrop() {
    const cards = document.querySelectorAll('.block-card');

    cards.forEach(card => {
        card.addEventListener('dragstart', handleDragStart);
        card.addEventListener('dragend', handleDragEnd);
        card.addEventListener('dragover', handleDragOver);
        card.addEventListener('dragenter', handleDragEnter);
        card.addEventListener('dragleave', handleDragLeave);
        card.addEventListener('drop', handleDrop);
    });
}

let draggedIndex = null;

function handleDragStart(e) {
    draggedIndex = parseInt(e.target.dataset.index);
    e.target.classList.add('dragging');
    e.dataTransfer.effectAllowed = 'move';
}

function handleDragEnd(e) {
    e.target.classList.remove('dragging');
    document.querySelectorAll('.block-card').forEach(card => {
        card.classList.remove('drag-over');
    });
}

function handleDragOver(e) {
    e.preventDefault();
    e.dataTransfer.dropEffect = 'move';
}

function handleDragEnter(e) {
    e.preventDefault();
    e.target.closest('.block-card')?.classList.add('drag-over');
}

function handleDragLeave(e) {
    e.target.closest('.block-card')?.classList.remove('drag-over');
}

function handleDrop(e) {
    e.preventDefault();
    const targetCard = e.target.closest('.block-card');
    if (!targetCard) return;

    const targetIndex = parseInt(targetCard.dataset.index);

    if (draggedIndex !== null && draggedIndex !== targetIndex) {
        // Reordena
        const [movedBlock] = blocks.splice(draggedIndex, 1);
        blocks.splice(targetIndex, 0, movedBlock);

        // Renumera
        blocks.forEach((b, i) => b.id = i + 1);
        renderBlocks();
    }

    draggedIndex = null;
}

// ============ PROCESSING ============

async function processBlocks() {
    if (blocks.length === 0) {
        alert('Nenhum bloco para processar.');
        return;
    }

    const engine = document.getElementById('engineSelect').value;
    const voiceId = document.getElementById('voiceSelect').value;

    // Verifica se é multilingual com sotaque travado
    let forceLanguage = null;
    const language = document.getElementById('languageSelect').value;
    if (language === 'multilingual' && document.getElementById('lockAccent').checked) {
        forceLanguage = document.getElementById('forceLanguage').value;
    }

    try {
        // === RESET COMPLETO DA ÁREA DE PROCESSAMENTO ===
        resetProcessingArea();

        // Mostra step 3
        document.getElementById('step3').classList.remove('hidden');
        document.getElementById('step3').scrollIntoView({ behavior: 'smooth' });

        // Renderiza fila
        renderQueue();

        // Inicia processamento
        const response = await fetch('/api/process', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                blocks,
                engine,
                voice_id: voiceId,
                force_language: forceLanguage
            })
        });

        const data = await response.json();

        if (data.error) {
            alert('Erro: ' + data.error);
            return;
        }

        currentJobId = data.job_id;
        isAudioReady = false; // Flag global para controle

        // Inicia polling de status
        startPolling();

    } catch (error) {
        console.error('Erro ao processar:', error);
        alert('Erro ao iniciar processamento: ' + error.message);
    }
}

// Flag para rastrear se o áudio está pronto
let isAudioReady = false;

function resetProcessingArea() {
    // Esconde completamente a área de download
    const downloadArea = document.getElementById('downloadArea');
    downloadArea.classList.add('hidden');

    // Desabilita o botão de download
    const downloadBtn = document.getElementById('downloadBtn');
    downloadBtn.disabled = true;

    // Limpa o player de áudio
    const audioPlayer = document.getElementById('audioPlayer');
    audioPlayer.src = '';
    audioPlayer.load();

    // Reset da barra de progresso
    document.getElementById('progressFill').style.width = '0%';
    document.getElementById('progressPercent').textContent = '0%';
    document.getElementById('progressText').textContent = 'Iniciando...';

    // Limpa a fila
    document.getElementById('queueList').innerHTML = '';

    // Reset da flag
    isAudioReady = false;
}

function renderQueue() {
    const queueList = document.getElementById('queueList');
    queueList.innerHTML = '';

    blocks.forEach((block, index) => {
        const item = document.createElement('div');
        item.className = 'queue-item';
        item.id = `queue-${index}`;
        item.innerHTML = `
            <span class="queue-status">⏳</span>
            <span class="queue-text">Bloco ${index + 1}: ${block.content.substring(0, 50)}...</span>
        `;
        queueList.appendChild(item);
    });
}

function startPolling() {
    if (pollInterval) clearInterval(pollInterval);

    pollInterval = setInterval(async () => {
        try {
            const response = await fetch(`/api/status/${currentJobId}`);
            const status = await response.json();

            updateProgress(status);

            // Só finaliza quando status for DEFINITIVAMENTE completed ou error
            if (status.status === 'completed') {
                clearInterval(pollInterval);
                pollInterval = null;

                // Aguarda um momento para garantir que o arquivo foi salvo
                setTimeout(() => {
                    showDownload();
                }, 500);

            } else if (status.status === 'error') {
                clearInterval(pollInterval);
                pollInterval = null;
                alert('Erro no processamento: ' + status.error);
            }
        } catch (error) {
            console.error('Erro ao verificar status:', error);
        }
    }, 1000);
}

function updateProgress(status) {
    // Atualiza barra de progresso
    const progress = Math.min(status.progress, 99); // Nunca mostra 100% até showDownload
    document.getElementById('progressFill').style.width = `${progress}%`;
    document.getElementById('progressPercent').textContent = `${progress}%`;

    if (status.status === 'processing') {
        document.getElementById('progressText').textContent =
            `Processando bloco ${status.processed_blocks} de ${status.total_blocks}...`;
    }

    // Atualiza itens da fila
    for (let i = 0; i < blocks.length; i++) {
        const item = document.getElementById(`queue-${i}`);
        if (!item) continue;

        const statusSpan = item.querySelector('.queue-status');

        if (i < status.processed_blocks) {
            item.classList.add('completed');
            item.classList.remove('processing');
            statusSpan.textContent = '✅';
        } else if (i === status.processed_blocks && status.status === 'processing') {
            item.classList.add('processing');
            statusSpan.textContent = '🔄';
        }
    }
}

function showDownload() {
    // Marca como pronto
    isAudioReady = true;

    // Atualiza progresso para 100%
    document.getElementById('progressText').textContent = '✅ Concluído!';
    document.getElementById('progressPercent').textContent = '100%';
    document.getElementById('progressFill').style.width = '100%';

    // Mostra a área de download
    document.getElementById('downloadArea').classList.remove('hidden');

    // Habilita o botão de download
    document.getElementById('downloadBtn').disabled = false;

    // Configura o player de áudio SOMENTE agora
    const audioPlayer = document.getElementById('audioPlayer');
    audioPlayer.src = `/api/download/${currentJobId}`;
    audioPlayer.load();
}

async function downloadAudio() {
    // Verificação tripla antes de permitir download
    if (!currentJobId) {
        alert('Nenhum áudio para baixar.');
        return;
    }

    if (!isAudioReady) {
        alert('O áudio ainda está sendo processado. Aguarde a conclusão.');
        return;
    }

    // Última verificação: consulta a API para confirmar
    try {
        const response = await fetch(`/api/status/${currentJobId}`);
        const status = await response.json();

        if (status.status !== 'completed') {
            alert('O áudio ainda está sendo processado. Aguarde a conclusão.');
            return;
        }

        // Tudo OK, faz o download
        window.location.href = `/api/download/${currentJobId}`;

    } catch (error) {
        console.error('Erro ao verificar status:', error);
        alert('Erro ao verificar status do áudio.');
    }
}

function startOver() {
    // Limpa estado
    blocks = [];
    currentJobId = null;
    isAudioReady = false;
    if (pollInterval) clearInterval(pollInterval);

    // Reset da área de processamento
    resetProcessingArea();

    // Reset UI
    document.getElementById('inputText').value = '';
    document.getElementById('charCount').textContent = '0';
    document.getElementById('step2').classList.add('hidden');
    document.getElementById('step3').classList.add('hidden');
    document.getElementById('blocksContainer').innerHTML = '';

    // Scroll to top
    window.scrollTo({ top: 0, behavior: 'smooth' });
}

