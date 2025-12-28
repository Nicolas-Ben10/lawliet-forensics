import os
import sys
import json
import threading
from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
from pathlib import Path
from werkzeug.utils import secure_filename
from rich.console import Console
from rich.panel import Panel
from rich.live import Live
from rich.table import Table
from rich.progress import Progress

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'core'))
from lawliet import carve

app = Flask(__name__, static_folder='.')
CORS(app)

console = Console()

PROJECT_ROOT = Path(__file__).parent.parent
STORAGE_DIR = PROJECT_ROOT / 'storage'
RECOVERED_DIR = PROJECT_ROOT / 'recovered'
WEB_DIR = Path(__file__).parent

STORAGE_DIR.mkdir(exist_ok=True)
RECOVERED_DIR.mkdir(exist_ok=True)

app.config['MAX_CONTENT_LENGTH'] = 50 * 1024 * 1024 * 1024  
ALLOWED_EXTENSIONS = {'raw', 'img', 'dd', 'bin'}

operations = {
    'file_recovery': {'status': 'idle', 'progress': 0, 'message': ''},
    'file_upload': {'status': 'idle', 'progress': 0, 'message': '', 'filename': ''}
}

ASCII_ART = """
 [bold red]██╗      █████╗ ██╗    ██╗██╗     ██╗███████╗████████╗[/bold red]
 [bold white]██║     ██╔══██╗██║    ██║██║     ██║██╔════╝╚══██╔══╝[/bold white]
 [bold red]██║     ███████║██║ █╗ ██║██║     ██║█████╗     ██║   [/bold red]
 [bold white]██║     ██╔══██║██║███╗██║██║     ██║██╔══╝     ██║   [/bold white]
 [bold red]███████╗██║  ██║╚███╔███╔╝███████╗██║███████╗   ██║   [/bold red]
 [bold white]╚══════╝╚═╝  ╚═╝ ╚══╝╚══╝ ╚══════╝╚═╝╚══════╝   ╚═╝   [/bold white]
           [italic cyan]Digital Forensics File Carver[/italic cyan]
           [italic blue]By Nicolas Pauferro[/italic blue]
           [italic purple]Supported files: jpg, png, pdf, gif, zip, mp4 and pptx[/italic purple]
           [italic white]txt, mp3, rar and docx cooming soon...[/italic white]

"""

def print_welcome():
    console.print(Panel(ASCII_ART, subtitle="Version - 1.0 - Web Interface", border_style="blue"))


def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route('/')
def index():
    return send_file(WEB_DIR / 'index.html')

@app.route('/style.css')
def serve_css():
    return send_file(WEB_DIR / 'style.css', mimetype='text/css')

@app.route('/script.js')
def serve_js():
    return send_file(WEB_DIR / 'script.js', mimetype='application/javascript')

@app.route('/files.js')
def serve_files_js():
    return send_file(WEB_DIR / 'files.js', mimetype='application/javascript')

@app.route('/files.html')
def serve_files_html():
    return send_file(WEB_DIR / 'files.html')

@app.route('/logo.jpg')
def serve_logo():
    return send_file(WEB_DIR / 'logo.jpg')

@app.route('/api/upload-image', methods=['POST'])
def upload_image():
    if 'file' not in request.files:
        return jsonify({'success': False, 'error': 'No file provided'}), 400
    
    file = request.files['file']
    
    if file.filename == '':
        return jsonify({'success': False, 'error': 'No file selected'}), 400
    
    if not allowed_file(file.filename):
        return jsonify({'success': False, 'error': f'Invalid file type. Allowed: {", ".join(ALLOWED_EXTENSIONS)}'}), 400
    
    filename = secure_filename(file.filename)
    filepath = STORAGE_DIR / filename
    
    if filepath.exists():
        return jsonify({'success': False, 'error': f'File {filename} already exists'}), 409
    
    try:
        operations['file_upload']['status'] = 'uploading'
        operations['file_upload']['progress'] = 0
        operations['file_upload']['message'] = f'Uploading {filename}...'
        operations['file_upload']['filename'] = filename
        
        file.save(str(filepath))
        
        operations['file_upload']['status'] = 'completed'
        operations['file_upload']['progress'] = 100
        operations['file_upload']['message'] = f'Upload completed: {filename}'
        
        return jsonify({
            'success': True, 
            'message': 'File uploaded successfully',
            'filename': filename,
            'size': filepath.stat().st_size
        })
    
    except Exception as e:
        operations['file_upload']['status'] = 'error'
        operations['file_upload']['message'] = str(e)
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/recover', methods=['POST'])
def recover_files():
    data = request.json
    image_path = data.get('image_path')
    device_path = data.get('device_path')
    buffer_size_mb = data.get('buffer_size', 8)
    
    # Must provide either image_path or device_path
    if not image_path and not device_path:
        return jsonify({'success': False, 'error': 'Either image_path or device_path is required'}), 400
    
    # Use device_path if provided, otherwise use image_path
    source_path = device_path if device_path else image_path
    
    try:
        buffer_size_mb = int(buffer_size_mb)
        if buffer_size_mb < 1 or buffer_size_mb > 1024:
            return jsonify({'success': False, 'error': 'Buffer size must be between 1 and 1024 MB'}), 400
    except (ValueError, TypeError):
        return jsonify({'success': False, 'error': 'Invalid buffer size'}), 400
    
    buffer_size_bytes = buffer_size_mb * 1024 * 1024
    
    # Handle device paths (like /dev/sdb)
    if device_path:
        source_path = Path(device_path)
        
        # Validate device path
        if not str(source_path).startswith('/dev/'):
            return jsonify({'success': False, 'error': 'Device path must start with /dev/'}), 400
        
        # Check if device exists
        if not source_path.exists():
            return jsonify({'success': False, 'error': f'Device not found: {source_path}'}), 404
        
        # Safety check: prevent using system drives
        dangerous_devices = ['/dev/sda', '/dev/nvme0n1', '/dev/vda']
        if str(source_path) in dangerous_devices:
            return jsonify({'success': False, 'error': f'Cannot use system drive: {source_path}. This is a safety measure.'}), 403
    
    # Handle image file paths
    else:
        if not os.path.isabs(image_path):
            source_path = STORAGE_DIR / image_path
        else:
            source_path = Path(image_path)
        
        if not source_path.exists():
            return jsonify({'success': False, 'error': f'Image file not found: {source_path}'}), 404
    
    if operations['file_recovery']['status'] == 'running':
        return jsonify({'success': False, 'error': 'File recovery already in progress'}), 409
    
    def run_recovery():
        operations['file_recovery']['status'] = 'running'
        operations['file_recovery']['progress'] = 0
        operations['file_recovery']['message'] = f'Starting file recovery with {buffer_size_mb}MB buffer...'
        
        try:
            carve(str(source_path), str(RECOVERED_DIR), buffer_size_bytes)
            
            operations['file_recovery']['status'] = 'completed'
            operations['file_recovery']['progress'] = 100
            operations['file_recovery']['message'] = 'File recovery completed successfully'
        
        except Exception as e:
            operations['file_recovery']['status'] = 'error'
            operations['file_recovery']['message'] = str(e)
    
    thread = threading.Thread(target=run_recovery)
    thread.daemon = True
    thread.start()
    
    return jsonify({'success': True, 'message': 'File recovery started'})

@app.route('/api/progress/<operation>', methods=['GET'])
def get_progress(operation):
    if operation not in operations:
        return jsonify({'success': False, 'error': 'Invalid operation'}), 400
    
    return jsonify({'success': True, 'operation': operations[operation]})

@app.route('/api/devices', methods=['GET'])
def list_devices():
    try:
        import subprocess
        import json as json_lib
        
        # Use lsblk to list block devices
        result = subprocess.run(
            ['lsblk', '-J', '-o', 'NAME,SIZE,TYPE,MOUNTPOINT,MODEL'],
            capture_output=True,
            text=True
        )
        
        if result.returncode != 0:
            return jsonify({'success': False, 'error': 'Failed to list devices'}), 500
        
        lsblk_data = json_lib.loads(result.stdout)
        devices = []
        
        for device in lsblk_data.get('blockdevices', []):
            # Only include disk and partition types, exclude loop devices
            if device.get('type') in ['disk', 'part']:
                devices.append({
                    'name': device.get('name'),
                    'path': f"/dev/{device.get('name')}",
                    'size': device.get('size'),
                    'type': device.get('type'),
                    'mountpoint': device.get('mountpoint'),
                    'model': device.get('model', 'Unknown')
                })
        
        return jsonify({'success': True, 'devices': devices})
    
    except FileNotFoundError:
        return jsonify({'success': False, 'error': 'lsblk command not found'}), 500
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/images', methods=['GET'])
def list_images():
    try:
        images = []
        for file in STORAGE_DIR.glob('*'):
            if file.is_file() and file.suffix.lower() in ['.raw', '.img', '.dd', '.bin']:
                stat = file.stat()
                images.append({
                    'name': file.name,
                    'path': str(file),
                    'size': stat.st_size,
                    'size_human': format_bytes(stat.st_size),
                    'modified': stat.st_mtime
                })
        
        return jsonify({'success': True, 'images': images})
    
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/files', methods=['GET'])
def list_recovered_files():
    try:
        files_by_type = {}
        
        for subdir in RECOVERED_DIR.iterdir():
            if subdir.is_dir():
                file_type = subdir.name
                files_by_type[file_type] = []
                
                for file in subdir.glob('*'):
                    if file.is_file():
                        stat = file.stat()
                        files_by_type[file_type].append({
                            'name': file.name,
                            'path': str(file.relative_to(RECOVERED_DIR)),
                            'size': stat.st_size,
                            'size_human': format_bytes(stat.st_size),
                            'type': file_type
                        })
        
        return jsonify({'success': True, 'files': files_by_type})
    
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/download/<path:filepath>', methods=['GET'])
def download_file(filepath):
    try:
        file_path = RECOVERED_DIR / filepath
        
        if not file_path.exists() or not file_path.is_file():
            return jsonify({'success': False, 'error': 'File not found'}), 404
        
        if not str(file_path.resolve()).startswith(str(RECOVERED_DIR.resolve())):
            return jsonify({'success': False, 'error': 'Invalid file path'}), 403
        
        return send_file(file_path, as_attachment=True)
    
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/delete-image/<filename>', methods=['DELETE'])
def delete_image(filename):
    try:
        filename = secure_filename(filename)
        filepath = STORAGE_DIR / filename
        
        if not filepath.exists():
            return jsonify({'success': False, 'error': 'File not found'}), 404
        
        if not str(filepath.resolve()).startswith(str(STORAGE_DIR.resolve())):
            return jsonify({'success': False, 'error': 'Invalid file path'}), 403
        
        filepath.unlink()
        return jsonify({'success': True, 'message': f'Deleted {filename}'})
    
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

def format_bytes(bytes_size):
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if bytes_size < 1024.0:
            return f"{bytes_size:.2f} {unit}"
        bytes_size /= 1024.0
    return f"{bytes_size:.2f} PB"

if __name__ == '__main__':
    print_welcome()
    console.print(f"Storage directory: {STORAGE_DIR}")
    console.print(f"Recovered files directory: {RECOVERED_DIR}")
    console.print(f"Max upload size: {app.config['MAX_CONTENT_LENGTH'] / (1024**3):.0f} GB")
    console.print("\nStarting server on http://localhost:5000")
    console.print("=" * 60)
    console.print("=" * 60)
    
    
    app.run(host='0.0.0.0', port=5000, debug=True, use_reloader=False)
