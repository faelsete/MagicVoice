/**
 * MagicVoice - Text to Speech Application
 * Clean, minimal, automated flow
 */

// Constants
const MAX_CHARS_CONVERSION = 8000;  // ~9 min audio
const MAX_CHARS_AUDIOBOOK = Infinity;  // Sem limite - divide em blocos automaticamente
const BLOCK_SIZE = 2500;

// Voices data
const VOICES = {
    'pt-BR': [
        { id: 'pt-BR-AntonioNeural', name: 'Antônio' },
        { id: 'pt-BR-FranciscaNeural', name: 'Francisca' },
        { id: 'pt-BR-ThalitaNeural', name: 'Thalita' }
    ],
    'en-US': [
        { id: 'en-US-GuyNeural', name: 'Guy' },
        { id: 'en-US-JennyNeural', name: 'Jenny' },
        { id: 'en-US-AriaNeural', name: 'Aria' }
    ],
    'es-MX': [
        { id: 'es-MX-JorgeNeural', name: 'Jorge' },
        { id: 'es-MX-DaliaNeural', name: 'Dalia' }
    ],
    'multilingual': [
        { id: 'en-US-AvaMultilingualNeural', name: 'Ava' },
        { id: 'en-US-AndrewMultilingualNeural', name: 'Andrew' },
        { id: 'en-US-EmmaMultilingualNeural', name: 'Emma' },
        { id: 'en-US-BrianMultilingualNeural', name: 'Brian' }
    ]
};

// State
let currentMode = 'conversion';
let currentJobId = null;
let statusInterval = null;

// DOM Elements
const textInput = document.getElementById('textInput');
const charCount = document.getElementById('charCount');
const charLimit = document.getElementById('charLimit');
const charCounter = document.getElementById('charCounter');
const languageSelect = document.getElementById('languageSelect');
const voiceSelect = document.getElementById('voiceSelect');
const generateBtn = document.getElementById('generateBtn');
const progressContainer = document.getElementById('progressContainer');
const progressFill = document.getElementById('progressFill');
const progressText = document.getElementById('progressText');
const resultContainer = document.getElementById('resultContainer');
const blocksCard = document.getElementById('blocksCard');
const blocksPreview = document.getElementById('blocksPreview');
const blockCount = document.getElementById('blockCount');
const modeDescription = document.getElementById('modeDescription');
const audioPlayer = document.getElementById('audioPlayer');
const downloadBtn = document.getElementById('downloadBtn');
const resultInfo = document.getElementById('resultInfo');

// Initialize
document.addEventListener('DOMContentLoaded', () => {
    updateVoices();
    updateCharLimit();

    textInput.addEventListener('input', () => {
        updateCharCount();
        if (currentMode === 'audiobook') {
            updateBlocksPreview();
        }
    });
});

// Mode switching
function setMode(mode) {
    currentMode = mode;

    // Update buttons
    document.querySelectorAll('.mode-btn').forEach(btn => {
        btn.classList.toggle('active', btn.dataset.mode === mode);
    });

    // Update UI
    updateCharLimit();

    if (mode === 'conversion') {
        modeDescription.textContent = 'Cole seu texto (máx. 9 minutos de áudio)';
        blocksCard.classList.add('hidden');
    } else {
        modeDescription.textContent = 'Cole seu texto para criar um audiolivro';
        blocksCard.classList.remove('hidden');
        updateBlocksPreview();
    }
}

// Update character limit based on mode
function updateCharLimit() {
    const limit = currentMode === 'conversion' ? MAX_CHARS_CONVERSION : MAX_CHARS_AUDIOBOOK;
    charLimit.textContent = limit === Infinity ? 'ilimitado' : limit.toLocaleString();
    updateCharCount();
}

// Update character counter
function updateCharCount() {
    const count = textInput.value.length;
    const limit = currentMode === 'conversion' ? MAX_CHARS_CONVERSION : MAX_CHARS_AUDIOBOOK;

    charCount.textContent = count.toLocaleString();
    charCounter.classList.toggle('warning', count > limit);
}

// Update voices dropdown
function updateVoices() {
    const lang = languageSelect.value;
    const voices = VOICES[lang] || [];

    voiceSelect.innerHTML = '';
    voices.forEach(v => {
        const option = document.createElement('option');
        option.value = v.id;
        option.textContent = v.name;
        voiceSelect.appendChild(option);
    });
}

// Update blocks preview (Audiobook mode)
function updateBlocksPreview() {
    const text = textInput.value.trim();
    if (!text) {
        blocksPreview.innerHTML = '<div class="block-item"><span class="block-text" style="color: #999;">Digite algum texto para ver os blocos...</span></div>';
        blockCount.textContent = '0';
        return;
    }

    // Simple block splitting
    const blocks = splitTextIntoBlocks(text);
    blockCount.textContent = blocks.length;

    blocksPreview.innerHTML = blocks.map((block, i) => `
        <div class="block-item">
            <span class="block-number">${i + 1}</span>
            <span class="block-text">${escapeHtml(block.substring(0, 80))}${block.length > 80 ? '...' : ''}</span>
        </div>
    `).join('');
}

// Split text into blocks
function splitTextIntoBlocks(text) {
    const blocks = [];
    let remaining = text;

    while (remaining.length > 0) {
        if (remaining.length <= BLOCK_SIZE) {
            blocks.push(remaining);
            break;
        }

        // Find best split point (sentence end)
        let splitPoint = BLOCK_SIZE;
        const searchStart = Math.max(0, BLOCK_SIZE - 200);

        for (let i = BLOCK_SIZE; i >= searchStart; i--) {
            if ('.!?'.includes(remaining[i])) {
                splitPoint = i + 1;
                break;
            }
        }

        blocks.push(remaining.substring(0, splitPoint).trim());
        remaining = remaining.substring(splitPoint).trim();
    }

    return blocks;
}

// Generate audio
async function generateAudio() {
    const text = textInput.value.trim();

    if (!text) {
        alert('Digite ou cole algum texto.');
        return;
    }

    const limit = currentMode === 'conversion' ? MAX_CHARS_CONVERSION : MAX_CHARS_AUDIOBOOK;
    if (text.length > limit) {
        alert(`Texto muito longo. Máximo: ${limit.toLocaleString()} caracteres.`);
        return;
    }

    // Prepare blocks
    const blocks = currentMode === 'conversion'
        ? [{ content: text }]
        : splitTextIntoBlocks(text).map(b => ({ content: b }));

    // Show progress
    showProgress();

    try {
        // Check if Azure is configured
        const azureConfigured = isAzureConfigured();
        const settings = JSON.parse(localStorage.getItem('magicvoice_settings') || '{}');

        // Build request body
        const requestBody = {
            blocks: blocks,
            engine: azureConfigured ? 'azure' : 'edge',
            voice_id: voiceSelect.value,
            force_language: null
        };

        // Add Azure credentials if configured
        if (azureConfigured && settings.azure) {
            requestBody.azure_config = {
                apiKey: settings.azure.apiKey,
                region: settings.azure.region
            };
        }

        // Start processing
        const response = await fetch('/api/process', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(requestBody)
        });

        const data = await response.json();

        if (data.job_id) {
            currentJobId = data.job_id;
            pollStatus();
        } else {
            showError('Erro ao iniciar processamento');
        }

    } catch (error) {
        showError('Erro de conexão: ' + error.message);
    }
}

// Poll status
function pollStatus() {
    if (statusInterval) clearInterval(statusInterval);

    statusInterval = setInterval(async () => {
        try {
            const response = await fetch(`/api/status/${currentJobId}`);
            const data = await response.json();

            updateProgress(data.progress, data.status);

            if (data.status === 'completed') {
                clearInterval(statusInterval);
                showResult();
            } else if (data.status === 'error') {
                clearInterval(statusInterval);
                showError(data.error || 'Erro no processamento');
            }

        } catch (error) {
            clearInterval(statusInterval);
            showError('Erro ao verificar status');
        }
    }, 1000);
}

// Show progress
function showProgress() {
    generateBtn.disabled = true;
    generateBtn.innerHTML = '<div class="spinner"></div> Gerando...';
    progressContainer.classList.add('active');
    resultContainer.classList.remove('active');
    progressFill.style.width = '0%';
    progressText.textContent = 'Iniciando...';
}

// Update progress
function updateProgress(percent, status) {
    progressFill.style.width = percent + '%';

    if (status === 'processing') {
        progressText.textContent = `Processando... ${percent}%`;
    } else if (status === 'completed') {
        progressText.textContent = 'Concluído!';
    }
}

// Show result
async function showResult() {
    progressContainer.classList.remove('active');
    resultContainer.classList.add('active');

    generateBtn.disabled = false;
    generateBtn.innerHTML = `
        <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <polygon points="5 3 19 12 5 21 5 3"/>
        </svg>
        Gerar Áudio
    `;

    // Set audio source and download link
    const audioUrl = `/api/download/${currentJobId}`;
    audioPlayer.src = audioUrl;

    // Fetch audio as blob for reliable download
    try {
        const response = await fetch(audioUrl);
        const blob = await response.blob();
        const blobUrl = URL.createObjectURL(blob);

        downloadBtn.href = blobUrl;
        downloadBtn.download = `magicvoice_${Date.now()}.mp3`;

        // Get duration
        audioPlayer.onloadedmetadata = () => {
            const duration = Math.round(audioPlayer.duration);
            const mins = Math.floor(duration / 60);
            const secs = duration % 60;
            resultInfo.textContent = `Duração: ${mins}:${secs.toString().padStart(2, '0')}`;
        };

    } catch (error) {
        console.error('Error fetching audio:', error);
        // Fallback to direct URL
        downloadBtn.href = audioUrl;
    }
}

// Show error
function showError(message) {
    progressContainer.classList.remove('active');

    generateBtn.disabled = false;
    generateBtn.innerHTML = `
        <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <polygon points="5 3 19 12 5 21 5 3"/>
        </svg>
        Gerar Áudio
    `;

    alert('Erro: ' + message);
}

// Reset app
function resetApp() {
    textInput.value = '';
    resultContainer.classList.remove('active');
    progressContainer.classList.remove('active');
    audioPlayer.src = '';
    updateCharCount();

    if (currentMode === 'audiobook') {
        updateBlocksPreview();
    }

    // Revoke blob URL to free memory
    if (downloadBtn.href.startsWith('blob:')) {
        URL.revokeObjectURL(downloadBtn.href);
    }
}

// Utility: escape HTML
function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

// ==========================================
// SETTINGS
// ==========================================

const settingsModal = document.getElementById('settingsModal');
const azureEnabled = document.getElementById('azureEnabled');
const azureFields = document.getElementById('azureFields');
const azureApiKey = document.getElementById('azureApiKey');
const azureRegion = document.getElementById('azureRegion');

// Premium voices (only shown when Azure is enabled)
const AZURE_PREMIUM_VOICES = {
    'pt-BR': [
        { id: 'pt-BR-AntonioNeural', name: 'Antônio', premium: false },
        { id: 'pt-BR-FranciscaNeural', name: 'Francisca', premium: false },
        { id: 'pt-BR-ThalitaNeural', name: 'Thalita', premium: false },
        { id: 'pt-BR-LeticiaNeural', name: 'Letícia ⭐', premium: true },
        { id: 'pt-BR-ManuelaNeural', name: 'Manuela ⭐', premium: true },
        { id: 'pt-BR-NicolauNeural', name: 'Nicolau ⭐', premium: true },
        { id: 'pt-BR-ValerioNeural', name: 'Valério ⭐', premium: true },
        { id: 'pt-BR-YaraNeural', name: 'Yara ⭐', premium: true }
    ],
    'en-US': [
        { id: 'en-US-GuyNeural', name: 'Guy', premium: false },
        { id: 'en-US-JennyNeural', name: 'Jenny', premium: false },
        { id: 'en-US-AriaNeural', name: 'Aria', premium: false },
        { id: 'en-US-DavisNeural', name: 'Davis ⭐', premium: true },
        { id: 'en-US-JasonNeural', name: 'Jason ⭐', premium: true },
        { id: 'en-US-NancyNeural', name: 'Nancy ⭐', premium: true },
        { id: 'en-US-SaraNeural', name: 'Sara ⭐', premium: true },
        { id: 'en-US-TonyNeural', name: 'Tony ⭐', premium: true }
    ],
    'es-MX': [
        { id: 'es-MX-JorgeNeural', name: 'Jorge', premium: false },
        { id: 'es-MX-DaliaNeural', name: 'Dalia', premium: false },
        { id: 'es-MX-BeatrizNeural', name: 'Beatriz ⭐', premium: true },
        { id: 'es-MX-CandelaNeural', name: 'Candela ⭐', premium: true }
    ],
    'multilingual': [
        { id: 'en-US-AvaMultilingualNeural', name: 'Ava', premium: false },
        { id: 'en-US-AndrewMultilingualNeural', name: 'Andrew', premium: false },
        { id: 'en-US-EmmaMultilingualNeural', name: 'Emma', premium: false },
        { id: 'en-US-BrianMultilingualNeural', name: 'Brian', premium: false }
    ]
};

// Load settings from localStorage
function loadSettings() {
    const settings = JSON.parse(localStorage.getItem('magicvoice_settings') || '{}');

    if (settings.azure) {
        azureEnabled.checked = settings.azure.enabled || false;
        azureApiKey.value = settings.azure.apiKey || '';
        azureRegion.value = settings.azure.region || 'eastus';

        if (settings.azure.enabled) {
            azureFields.classList.add('active');
        }
    }

    // Update voices based on settings
    updateVoices();
}

// Save settings to localStorage
function saveSettings() {
    const settings = {
        azure: {
            enabled: azureEnabled.checked,
            apiKey: azureApiKey.value,
            region: azureRegion.value
        }
    };

    localStorage.setItem('magicvoice_settings', JSON.stringify(settings));

    // Update voices with new settings
    updateVoices();

    closeSettings();
}

// Open settings modal
function openSettings() {
    loadSettings();
    settingsModal.classList.add('active');
}

// Close settings modal
function closeSettings() {
    settingsModal.classList.remove('active');
}

// Close on overlay click
function closeSettingsOnOverlay(event) {
    if (event.target === settingsModal) {
        closeSettings();
    }
}

// Toggle Azure fields visibility
function toggleAzure() {
    if (azureEnabled.checked) {
        azureFields.classList.add('active');
    } else {
        azureFields.classList.remove('active');
    }
}

// Check if Azure is configured
function isAzureConfigured() {
    const settings = JSON.parse(localStorage.getItem('magicvoice_settings') || '{}');
    return settings.azure && settings.azure.enabled && settings.azure.apiKey;
}

// Override updateVoices to include premium voices
const originalUpdateVoices = updateVoices;
updateVoices = function () {
    const lang = languageSelect.value;
    const azureConfigured = isAzureConfigured();

    // Get voices based on Azure status
    let voices;
    if (azureConfigured) {
        voices = AZURE_PREMIUM_VOICES[lang] || [];
    } else {
        voices = VOICES[lang] || [];
    }

    voiceSelect.innerHTML = '';
    voices.forEach(v => {
        // Skip premium voices if Azure is not configured
        if (v.premium && !azureConfigured) return;

        const option = document.createElement('option');
        option.value = v.id;
        option.textContent = v.name;
        voiceSelect.appendChild(option);
    });
};

// Initialize settings on page load
document.addEventListener('DOMContentLoaded', () => {
    loadSettings();
});
