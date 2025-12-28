const API_BASE = 'http://localhost:5000/api';

let progressIntervals = {};
let currentSelectedImage = null;
let currentMode = 'image'; // 'image' or 'device'

// DOM Elements
const uploadArea = document.getElementById('uploadArea');
const imageFileInput = document.getElementById('imageFile');
const uploadProgress = document.getElementById('uploadProgress');
const uploadProgressBar = document.getElementById('uploadProgressBar');
const uploadProgressText = document.getElementById('uploadProgressText');
const uploadProgressMessage = document.getElementById('uploadProgressMessage');

const refreshImagesBtn = document.getElementById('refreshImages');
const imagesList = document.getElementById('imagesList');
const imageSelect = document.getElementById('imageSelect');
const recoverFilesBtn = document.getElementById('recoverFiles');
const recoveryProgress = document.getElementById('recoveryProgress');
const recoveryProgressBar = document.getElementById('recoveryProgressBar');
const recoveryProgressText = document.getElementById('recoveryProgressText');
const recoveryProgressMessage = document.getElementById('recoveryProgressMessage');

// Mode switching elements
const modeImageBtn = document.getElementById('modeImage');
const modeDeviceBtn = document.getElementById('modeDevice');
const imageModeDiv = document.getElementById('imageMode');
const deviceModeDiv = document.getElementById('deviceMode');
const deviceSelect = document.getElementById('deviceSelect');
const deviceManual = document.getElementById('deviceManual');

// Event Listeners
uploadArea.addEventListener('click', () => imageFileInput.click());
imageFileInput.addEventListener('change', handleFileSelect);

// Drag and drop
uploadArea.addEventListener('dragover', (e) => {
    e.preventDefault();
    uploadArea.classList.add('drag-over');
});

uploadArea.addEventListener('dragleave', () => {
    uploadArea.classList.remove('drag-over');
});

uploadArea.addEventListener('drop', (e) => {
    e.preventDefault();
    uploadArea.classList.remove('drag-over');

    const files = e.dataTransfer.files;
    if (files.length > 0) {
        imageFileInput.files = files;
        handleFileSelect();
    }
});

refreshImagesBtn.addEventListener('click', loadImages);
recoverFilesBtn.addEventListener('click', recoverFiles);
imageSelect.addEventListener('change', () => {
    if (currentMode === 'image') {
        recoverFilesBtn.disabled = !imageSelect.value;
    }
});

// Mode switching
modeImageBtn.addEventListener('click', () => switchMode('image'));
modeDeviceBtn.addEventListener('click', () => switchMode('device'));

// Device selection
deviceSelect.addEventListener('change', () => {
    if (currentMode === 'device') {
        recoverFilesBtn.disabled = !deviceSelect.value && !deviceManual.value;
    }
});

deviceManual.addEventListener('input', () => {
    if (currentMode === 'device') {
        recoverFilesBtn.disabled = !deviceSelect.value && !deviceManual.value;
    }
});

// Initialize
loadImages();
loadDevices();

// Functions
function handleFileSelect() {
    const file = imageFileInput.files[0];
    if (file) {
        uploadImage(file);
    }
}

async function uploadImage(file) {
    const formData = new FormData();
    formData.append('file', file);

    try {
        uploadProgress.style.display = 'block';
        uploadProgressText.textContent = '0%';
        uploadProgressMessage.textContent = 'Uploading...';

        const xhr = new XMLHttpRequest();

        xhr.upload.addEventListener('progress', (e) => {
            if (e.lengthComputable) {
                const percentComplete = Math.round((e.loaded / e.total) * 100);
                uploadProgressBar.style.width = `${percentComplete}%`;
                uploadProgressText.textContent = `${percentComplete}%`;
                uploadProgressMessage.textContent = `${formatBytes(e.loaded)} / ${formatBytes(e.total)}`;
            }
        });

        xhr.addEventListener('load', () => {
            if (xhr.status === 200) {
                const data = JSON.parse(xhr.responseText);
                if (data.success) {
                    showToast('Upload completed', 'success');
                    uploadProgressBar.style.width = '100%';
                    uploadProgressText.textContent = '100%';
                    uploadProgressMessage.textContent = 'Complete';
                    imageFileInput.value = '';
                    loadImages();

                    setTimeout(() => {
                        uploadProgress.style.display = 'none';
                    }, 2000);
                } else {
                    showToast(`Error: ${data.error}`, 'error');
                }
            } else {
                const data = JSON.parse(xhr.responseText);
                showToast(`Error: ${data.error || 'Upload failed'}`, 'error');
            }
        });

        xhr.addEventListener('error', () => {
            showToast('Upload failed: Network error', 'error');
        });

        xhr.open('POST', `${API_BASE}/upload-image`);
        xhr.send(formData);

    } catch (error) {
        showToast(`Failed to upload: ${error.message}`, 'error');
    }
}

async function loadImages() {
    try {
        const response = await fetch(`${API_BASE}/images`);
        const data = await response.json();

        if (data.success) {
            displayImages(data.images);
            populateImageSelect(data.images);
        } else {
            showToast(`Error loading images: ${data.error}`, 'error');
        }
    } catch (error) {
        showToast(`Failed to load images: ${error.message}`, 'error');
    }
}

function displayImages(images) {
    if (images.length === 0) {
        imagesList.innerHTML = '<p class="empty-msg">No sources found.</p>';
        return;
    }

    imagesList.innerHTML = '';
    images.forEach(image => {
        const imageItem = document.createElement('div');
        imageItem.className = 'image-item';
        if (currentSelectedImage === image.name) {
            imageItem.classList.add('selected');
        }

        imageItem.innerHTML = `
            <div class="image-name">${image.name}</div>
            <div class="image-info">Size: ${image.size_human}</div>
            <div class="image-actions">
                <button class="btn-sm" onclick="deleteImage('${image.name}')">Delete</button>
            </div>
        `;

        imageItem.addEventListener('click', (e) => {
            if (!e.target.classList.contains('btn-sm')) {
                selectImage(image.name, e.currentTarget);
            }
        });

        imagesList.appendChild(imageItem);
    });
}

function selectImage(imageName, element) {
    currentSelectedImage = imageName;
    imageSelect.value = imageName;
    recoverFilesBtn.disabled = false;

    // Update UI
    document.querySelectorAll('.image-item').forEach(item => {
        item.classList.remove('selected');
    });
    element.classList.add('selected');
}

function populateImageSelect(images) {
    imageSelect.innerHTML = '<option value="">Select an image to carve...</option>';

    images.forEach(image => {
        const option = document.createElement('option');
        option.value = image.name;
        option.textContent = `${image.name} (${image.size_human})`;
        imageSelect.appendChild(option);
    });
}

async function deleteImage(filename) {
    if (!confirm(`Delete ${filename}?`)) {
        return;
    }

    try {
        const response = await fetch(`${API_BASE}/delete-image/${filename}`, {
            method: 'DELETE'
        });

        const data = await response.json();

        if (data.success) {
            showToast('Image deleted', 'success');
            loadImages();
        } else {
            showToast(`Error: ${data.error}`, 'error');
        }
    } catch (error) {
        showToast(`Failed to delete: ${error.message}`, 'error');
    }
}

function switchMode(mode) {
    currentMode = mode;

    // Update button states
    if (mode === 'image') {
        modeImageBtn.classList.add('active');
        modeDeviceBtn.classList.remove('active');
        imageModeDiv.style.display = 'flex';
        deviceModeDiv.style.display = 'none';
        recoverFilesBtn.disabled = !imageSelect.value;
    } else {
        modeImageBtn.classList.remove('active');
        modeDeviceBtn.classList.add('active');
        imageModeDiv.style.display = 'none';
        deviceModeDiv.style.display = 'flex';
        recoverFilesBtn.disabled = !deviceSelect.value && !deviceManual.value;
    }
}

async function loadDevices() {
    try {
        const response = await fetch(`${API_BASE}/devices`);
        const data = await response.json();

        if (data.success) {
            populateDeviceSelect(data.devices);
        } else {
            console.error('Error loading devices:', data.error);
        }
    } catch (error) {
        console.error('Failed to load devices:', error.message);
    }
}

function populateDeviceSelect(devices) {
    deviceSelect.innerHTML = '<option value="">Select a device...</option>';

    devices.forEach(device => {
        const option = document.createElement('option');
        option.value = device.path;
        const mountInfo = device.mountpoint ? ` [MOUNTED: ${device.mountpoint}]` : '';
        option.textContent = `${device.path} (${device.size}) - ${device.model}${mountInfo}`;

        // Disable mounted devices for safety
        if (device.mountpoint) {
            option.disabled = true;
        }

        deviceSelect.appendChild(option);
    });
}

async function recoverFiles() {
    const bufferSize = parseInt(document.getElementById('bufferSize').value) || 8;
    let requestBody = { buffer_size: bufferSize };

    // Validate based on current mode
    if (currentMode === 'image') {
        const imagePath = imageSelect.value;
        if (!imagePath) {
            showToast('Select an image first', 'warning');
            return;
        }
        requestBody.image_path = imagePath;
    } else {
        // Device mode
        const devicePath = deviceManual.value || deviceSelect.value;
        if (!devicePath) {
            showToast('Select or enter a device path', 'warning');
            return;
        }
        requestBody.device_path = devicePath;
    }

    if (bufferSize < 1 || bufferSize > 1024) {
        showToast('Buffer size must be 1-1024 MB', 'warning');
        return;
    }

    try {
        recoverFilesBtn.disabled = true;
        const response = await fetch(`${API_BASE}/recover`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(requestBody)
        });

        const data = await response.json();

        if (data.success) {
            showToast('Recovery started', 'success');
            recoveryProgress.style.display = 'block';
            startProgressTracking('file_recovery', updateRecoveryProgress);
        } else {
            showToast(`Error: ${data.error}`, 'error');
            recoverFilesBtn.disabled = false;
        }
    } catch (error) {
        showToast(`Failed to start recovery: ${error.message}`, 'error');
        recoverFilesBtn.disabled = false;
    }
}

function updateRecoveryProgress(operation) {
    recoveryProgressBar.style.width = `${operation.progress}%`;
    recoveryProgressText.textContent = `${operation.progress}%`;
    recoveryProgressMessage.textContent = operation.message;

    if (operation.status === 'completed') {
        showToast('Recovery completed!', 'success');
        recoverFilesBtn.disabled = false;
        stopProgressTracking('file_recovery');
    } else if (operation.status === 'error') {
        showToast(`Error: ${operation.message}`, 'error');
        recoverFilesBtn.disabled = false;
        stopProgressTracking('file_recovery');
    }
}

function startProgressTracking(operation, callback) {
    if (progressIntervals[operation]) {
        clearInterval(progressIntervals[operation]);
    }

    progressIntervals[operation] = setInterval(async () => {
        try {
            const response = await fetch(`${API_BASE}/progress/${operation}`);
            const data = await response.json();

            if (data.success) {
                callback(data.operation);
            }
        } catch (error) {
            console.error('Progress tracking error:', error);
        }
    }, 1000);
}

function stopProgressTracking(operation) {
    if (progressIntervals[operation]) {
        clearInterval(progressIntervals[operation]);
        delete progressIntervals[operation];
    }
}

function formatBytes(bytes) {
    if (bytes === 0) return '0 B';
    const k = 1024;
    const sizes = ['B', 'KB', 'MB', 'GB', 'TB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
}

function showToast(message, type = 'info') {
    const toast = document.getElementById('toast');
    toast.textContent = message;
    toast.className = `toast ${type} show`;

    setTimeout(() => {
        toast.classList.remove('show');
    }, 3000);
}
