const API_BASE = 'http://localhost:5000/api';

let allFiles = [];
let filteredFiles = [];
let currentTypeFilter = 'all';
let currentSourceFilter = 'all';

// DOM Elements
const refreshFilesBtn = document.getElementById('refreshFiles');
const filesList = document.getElementById('filesList');
const filterTypeButtons = document.querySelectorAll('#filterType .chip');
const filterSourceSelect = document.getElementById('filterSource');
const totalFilesSpan = document.getElementById('totalFiles');
const filteredFilesSpan = document.getElementById('filteredFiles');

// Event Listeners
refreshFilesBtn.addEventListener('click', loadFiles);

filterTypeButtons.forEach(btn => {
    btn.addEventListener('click', () => {
        filterTypeButtons.forEach(b => b.classList.remove('active'));
        btn.classList.add('active');
        currentTypeFilter = btn.dataset.type;
        applyFilters();
    });
});

filterSourceSelect.addEventListener('change', () => {
    currentSourceFilter = filterSourceSelect.value;
    applyFilters();
});

// Initialize
loadFiles();
loadSources();

// Functions
async function loadFiles() {
    try {
        const response = await fetch(`${API_BASE}/files`);
        const data = await response.json();

        if (data.success) {
            allFiles = [];

            // Flatten files with metadata
            Object.keys(data.files).forEach(type => {
                data.files[type].forEach(file => {
                    allFiles.push({
                        ...file,
                        format: type
                    });
                });
            });

            totalFilesSpan.textContent = allFiles.length;
            applyFilters();
        } else {
            showToast(`Error loading files: ${data.error}`, 'error');
        }
    } catch (error) {
        showToast(`Failed to load files: ${error.message}`, 'error');
    }
}

async function loadSources() {
    try {
        const response = await fetch(`${API_BASE}/images`);
        const data = await response.json();

        if (data.success) {
            filterSourceSelect.innerHTML = '<option value="all">All Sources</option>';

            data.images.forEach(image => {
                const option = document.createElement('option');
                option.value = image.name;
                option.textContent = image.name;
                filterSourceSelect.appendChild(option);
            });
        }
    } catch (error) {
        console.error('Failed to load sources:', error);
    }
}

function applyFilters() {
    filteredFiles = allFiles.filter(file => {
        const typeMatch = currentTypeFilter === 'all' || file.format === currentTypeFilter;
        const sourceMatch = currentSourceFilter === 'all' || file.source === currentSourceFilter;
        return typeMatch && sourceMatch;
    });

    filteredFilesSpan.textContent = filteredFiles.length;
    displayFiles(filteredFiles);
}

function displayFiles(files) {
    if (files.length === 0) {
        filesList.innerHTML = '<p class="empty-msg">No files match the current filters.</p>';
        return;
    }

    filesList.innerHTML = '';

    files.forEach(file => {
        const fileCard = document.createElement('div');
        fileCard.className = 'file-card';

        // Create thumbnail
        const isImage = ['jpeg', 'jpg', 'png', 'gif'].includes(file.format.toLowerCase());
        const thumbnailHTML = isImage
            ? `<div class="file-thumbnail">
                   <img src="${API_BASE}/download/${file.path}" alt="${file.name}" loading="lazy">
               </div>`
            : `<div class="file-thumbnail">
                   <div class="file-thumbnail-placeholder">${getFileIcon(file.format)}</div>
               </div>`;

        fileCard.innerHTML = `
            ${thumbnailHTML}
            <div class="file-name">${file.name}</div>
            <div class="file-meta">${file.format.toUpperCase()} • ${file.size_human}</div>
        `;

        fileCard.addEventListener('click', () => downloadFile(file.path));

        filesList.appendChild(fileCard);
    });
}

function getFileIcon(type) {
    const icons = {
        'jpeg': '🖼',
        'jpg': '🖼',
        'png': '🖼',
        'gif': '🎞',
        'pdf': '📄',
        'doc': '📝',
        'docx': '📝',
        'office_new': '📝',
        'xlsx': '📊',
        'pptx': '📊',
        'txt': '📃',
        'zip': '🗜',
        'mp4': '🎬'
    };
    return icons[type.toLowerCase()] || '📄';
}

function downloadFile(filepath) {
    window.open(`${API_BASE}/download/${filepath}`, '_blank');
}

function showToast(message, type = 'info') {
    const toast = document.getElementById('toast');
    toast.textContent = message;
    toast.className = `toast ${type} show`;

    setTimeout(() => {
        toast.classList.remove('show');
    }, 3000);
}
