from flask import Flask, request, jsonify, send_file
import subprocess
import os
import tempfile
import uuid
import requests
from urllib.parse import urlparse

app = Flask(__name__)

@app.route('/health', methods=['GET'])
def health_check():
    return jsonify({'status': 'healthy', 'message': 'Loom downloader API is running'})

@app.route('/download-loom', methods=['POST'])
def download_loom():
    try:
        data = request.get_json()
        loom_url = data.get('url')
        
        if not loom_url:
            return jsonify({'error': 'No URL provided', 'usage': 'POST {"url": "https://www.loom.com/share/VIDEO_ID"}'}), 400
        
        # Validate URL
        if 'loom.com' not in loom_url:
            return jsonify({'error': 'Invalid Loom URL'}), 400
        
        # Create unique filename
        file_id = str(uuid.uuid4())
        temp_dir = tempfile.gettempdir()
        output_path = os.path.join(temp_dir, f"loom_{file_id}.mp4")
        
        # Download using the loom-dl script
        result = subprocess.run([
            'python', 'loomdl.py', loom_url, '-o', output_path
        ], capture_output=True, text=True, timeout=300)
        
        if result.returncode == 0 and os.path.exists(output_path):
            # Get file size for response
            file_size = os.path.getsize(output_path)
            
            return jsonify({
                'success': True, 
                'message': 'Video downloaded successfully',
                'download_url': f'/get-video/{file_id}',
                'file_id': file_id,
                'file_size_mb': round(file_size / (1024 * 1024), 2)
            })
        else:
            error_msg = result.stderr or result.stdout or 'Download failed'
            return jsonify({
                'success': False, 
                'error': f'Download failed: {error_msg}'
            }), 500
            
    except subprocess.TimeoutExpired:
        return jsonify({'success': False, 'error': 'Download timeout (300s limit)'}), 500
    except Exception as e:
        return jsonify({'success': False, 'error': f'Server error: {str(e)}'}), 500

@app.route('/get-video/<file_id>')
def get_video(file_id):
    try:
        temp_dir = tempfile.gettempdir()
        file_path = os.path.join(temp_dir, f"loom_{file_id}.mp4")
        
        if os.path.exists(file_path):
            return send_file(
                file_path, 
                as_attachment=True, 
                download_name=f"loom_video_{file_id}.mp4",
                mimetype='video/mp4'
            )
        else:
            return jsonify({'error': 'File not found or expired'}), 404
    except Exception as e:
        return jsonify({'error': f'Error serving file: {str(e)}'}), 500

@app.route('/cleanup/<file_id>', methods=['DELETE'])
def cleanup_file(file_id):
    try:
        temp_dir = tempfile.gettempdir()
        file_path = os.path.join(temp_dir, f"loom_{file_id}.mp4")
        
        if os.path.exists(file_path):
            os.remove(file_path)
            return jsonify({'success': True, 'message': 'File cleaned up'})
        else:
            return jsonify({'success': True, 'message': 'File already cleaned up'})
    except Exception as e:
        return jsonify({'error': f'Cleanup error: {str(e)}'}), 500

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
