from flask import Flask, request, render_template, send_file, jsonify
import whisper
import os
import re
import threading
import yt_dlp
import uuid
import subprocess
import numpy as np
from whisper.audio import SAMPLE_RATE

app = Flask(__name__)

# Set the path to FFmpeg before loading the model
os.environ["PATH"] = os.getcwd() + os.pathsep + os.environ.get("PATH", "")
model = whisper.load_model("base")  # "tiny", "base", "small", "medium", "large"

# Dictionary to store task status and video info
tasks = {}
video_info = {}

def extract_video_id(url):
    """Extract video ID from various YouTube URL formats"""
    patterns = [
        r'(?:v=|\/)([0-9A-Za-z_-]{11}).*',
        r'youtu\.be\/([0-9A-Za-z_-]{11})',
        r'youtube\.com\/embed\/([0-9A-Za-z_-]{11})'
    ]
    
    for pattern in patterns:
        match = re.search(pattern, url)
        if match:
            return match.group(1)
    
    return None

def convert_to_wav(input_file, output_file):
    """Convert audio file to WAV format using FFmpeg"""
    try:
        # Check if input file exists
        if not os.path.exists(input_file):
            print(f"Input file does not exist: {input_file}")
            return False
            
        # Use the local ffmpeg.exe
        cmd = [
            '.\\ffmpeg.exe',
            '-i', input_file,
            '-ar', '16000',
            '-ac', '1',
            '-c:a', 'pcm_s16le',
            output_file
        ]
        
        print(f"Running command: {' '.join(cmd)}")
        
        # Run the command and capture output
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        if result.returncode != 0:
            print(f"FFmpeg error: {result.stderr}")
            return False
            
        # Check if output file was created
        if not os.path.exists(output_file):
            print(f"Output file was not created: {output_file}")
            return False
            
        print(f"Successfully converted {input_file} to {output_file}")
        return True
    except Exception as e:
        print(f"Error converting to WAV: {str(e)}")
        return False

def download_media(url, video_id):
    """Download both audio and video using yt-dlp"""
    try:
        # Get the current working directory
        current_dir = os.getcwd()
        
        # Ensure downloads directory exists
        downloads_dir = os.path.join(current_dir, "downloads")
        os.makedirs(downloads_dir, exist_ok=True)
        
        # File paths
        original_audio = os.path.join(downloads_dir, f'{video_id}_audio')
        original_video = os.path.join(downloads_dir, f'{video_id}_video')
        wav_audio = os.path.join(downloads_dir, f'{video_id}_audio.wav')
        mp3_audio = os.path.join(downloads_dir, f'{video_id}_audio.mp3')
        mp4_video = os.path.join(downloads_dir, f'{video_id}_video.mp4')
        
        # Clean up any existing files
        for ext in ['mp3', 'webm', 'm4a', 'opus', 'wav', 'mp4']:
            for base_name in [original_audio, original_video]:
                test_file = f"{base_name}.{ext}"
                if os.path.exists(test_file):
                    try:
                        os.remove(test_file)
                        print(f"Removed existing file: {test_file}")
                    except:
                        pass
        
        # Download audio
        audio_opts = {
            'format': 'bestaudio/best',
            'outtmpl': f'{original_audio}.%(ext)s',
            'quiet': False,
            'no_warnings': False,
            'ffmpeg_location': '.',
        }
        
        # Download video
        video_opts = {
            'format': 'best[height<=720]/best',  # Download best quality up to 720p
            'outtmpl': f'{original_video}.%(ext)s',
            'quiet': False,
            'no_warnings': False,
            'ffmpeg_location': '.',
        }
        
        with yt_dlp.YoutubeDL(audio_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            print(f"Downloading audio: {info['title']}")
            ydl.download([url])
        
        with yt_dlp.YoutubeDL(video_opts) as ydl:
            print(f"Downloading video: {info['title']}")
            ydl.download([url])
            
        # Find the downloaded audio file
        audio_file = None
        for ext in ['mp3', 'webm', 'm4a', 'opus']:
            test_file = f"{original_audio}.{ext}"
            if os.path.exists(test_file):
                audio_file = test_file
                print(f"Found downloaded audio file: {audio_file}")
                break
        
        if not audio_file:
            raise Exception("Could not find downloaded audio file")
        
        # Find the downloaded video file
        video_file = None
        for ext in ['mp4', 'webm', 'mkv']:
            test_file = f"{original_video}.{ext}"
            if os.path.exists(test_file):
                video_file = test_file
                print(f"Found downloaded video file: {video_file}")
                break
        
        if not video_file:
            print("Warning: Could not find downloaded video file")
            video_file = None
        
        # Store video info for later use
        video_info[video_id] = {
            'title': info.get('title', 'Unknown Title'),
            'url': url,
            'original_audio_file': audio_file,
            'original_video_file': video_file
        }
        
        # Convert to WAV format for Whisper
        print(f"Converting {audio_file} to WAV format...")
        if not convert_to_wav(audio_file, wav_audio):
            raise Exception("Failed to convert audio to WAV format")
        
        # Convert to MP3 for download (if not already MP3)
        if not audio_file.endswith('.mp3'):
            print(f"Converting {audio_file} to MP3 for download...")
            cmd = [
                '.\\ffmpeg.exe',
                '-i', audio_file,
                '-acodec', 'mp3',
                '-ab', '192k',
                mp3_audio
            ]
            result = subprocess.run(cmd, capture_output=True, text=True)
            
            if result.returncode != 0:
                print(f"FFmpeg error: {result.stderr}")
                mp3_audio = audio_file
        else:
            mp3_audio = audio_file
        
        # Convert video to MP4 for download (if not already MP4)
        if video_file and not video_file.endswith('.mp4'):
            print(f"Converting {video_file} to MP4 for download...")
            cmd = [
                '.\\ffmpeg.exe',
                '-i', video_file,
                '-c:v', 'libx264',
                '-c:a', 'aac',
                '-preset', 'fast',
                mp4_video
            ]
            result = subprocess.run(cmd, capture_output=True, text=True)
            
            if result.returncode != 0:
                print(f"FFmpeg error: {result.stderr}")
                mp4_video = video_file
        else:
            mp4_video = video_file if video_file else None
        
        # Remove original files if they're different from the final files
        if audio_file != mp3_audio and os.path.exists(audio_file):
            try:
                os.remove(audio_file)
                print(f"Removed original audio file: {audio_file}")
            except Exception as e:
                print(f"Error removing original audio file: {str(e)}")
        
        if video_file and video_file != mp4_video and os.path.exists(video_file):
            try:
                os.remove(video_file)
                print(f"Removed original video file: {video_file}")
            except Exception as e:
                print(f"Error removing original video file: {str(e)}")
        
        return wav_audio, mp3_audio, mp4_video, info.get('title', 'Unknown Title')
    except Exception as e:
        print(f"Error in download_media: {str(e)}")
        raise Exception(f"Error downloading media: {str(e)}")

def transcribe_video(task_id, url):
    """Function to transcribe video in background thread"""
    try:
        # Update task status
        tasks[task_id] = {
            'state': 'PROGRESS',
            'status': {'current': 1, 'total': 10, 'status': 'Extracting video info...'}
        }
        
        # Extract video ID and validate
        video_id = extract_video_id(url)
        if not video_id:
            tasks[task_id] = {
                'state': 'FAILURE',
                'status': 'Invalid YouTube URL format'
            }
            return
        
        # Update task status
        tasks[task_id] = {
            'state': 'PROGRESS',
            'status': {'current': 2, 'total': 10, 'status': 'Downloading media...'}
        }
        
        # Download media using yt-dlp
        try:
            wav_audio, mp3_audio, mp4_video, video_title = download_media(url, video_id)
            
            # Verify the audio file exists and is accessible
            if not os.path.exists(wav_audio):
                tasks[task_id] = {
                    'state': 'FAILURE',
                    'status': f'Audio file not found: {wav_audio}'
                }
                return
                
            # Get file size to verify it's not empty
            file_size = os.path.getsize(wav_audio)
            if file_size == 0:
                tasks[task_id] = {
                    'state': 'FAILURE',
                    'status': 'Downloaded audio file is empty'
                }
                return
                
            print(f"Audio file: {wav_audio}, Size: {file_size} bytes")
        except Exception as e:
            tasks[task_id] = {
                'state': 'FAILURE',
                'status': str(e)
            }
            return
        
        # Update task status
        tasks[task_id] = {
            'state': 'PROGRESS',
            'status': {'current': 3, 'total': 10, 'status': 'Preparing audio for transcription...'}
        }
        
        # Load audio and prepare for chunked transcription
        try:
            audio = whisper.load_audio(wav_audio)
            audio_duration = len(audio) / SAMPLE_RATE
            print(f"Audio duration: {audio_duration:.2f} seconds")
        except Exception as e:
            tasks[task_id] = {
                'state': 'FAILURE',
                'status': f'Error loading audio: {str(e)}'
            }
            return
        
        # Update task status
        tasks[task_id] = {
            'state': 'PROGRESS',
            'status': {'current': 4, 'total': 10, 'status': 'Starting transcription...'}
        }
        
        # Transcribe with language detection using chunked approach
        try:
            # Split audio into chunks of 30 seconds each
            chunk_duration = 30  # seconds
            chunk_length = chunk_duration * SAMPLE_RATE
            chunks = [audio[i:i+chunk_length] for i in range(0, len(audio), chunk_length)]
            total_chunks = len(chunks)
            
            transcription_parts = []
            detected_language = None
            
            # Start transcription phase (steps 4 to 8)
            for i, chunk in enumerate(chunks):
                # Calculate progress within the transcription phase (4 to 8)
                progress_in_transcription = (i / total_chunks) * 4  # 4 is the range from 4 to 8
                current_progress = 4 + progress_in_transcription
                
                # Update task status for each chunk
                tasks[task_id] = {
                    'state': 'PROGRESS',
                    'status': {
                        'current': current_progress, 
                        'total': 10, 
                        'status': f'Transcribing chunk {i+1}/{total_chunks} ({(i+1)*chunk_duration}/{int(audio_duration)}s)...'
                    }
                }
                
                # Transcribe the chunk
                result = model.transcribe(
                    chunk,
                    fp16=False,
                    language=None,
                    task="transcribe",
                    verbose=False
                )
                
                # Set language from first chunk
                if i == 0:
                    detected_language = result.get("language", "unknown")
                
                transcription_parts.append(result["text"])
            
            # Combine all transcriptions
            transcription = " ".join(transcription_parts)
            print(f"Transcription completed. Language: {detected_language}")
            
        except Exception as e:
            tasks[task_id] = {
                'state': 'FAILURE',
                'status': f'Error transcribing audio: {str(e)}'
            }
            return
        
        # Update task status
        tasks[task_id] = {
            'state': 'PROGRESS',
            'status': {'current': 9, 'total': 10, 'status': 'Saving transcription...'}
        }
        
        # Save transcription
        try:
            txt_filename = f"downloads/{video_id}.txt"
            with open(txt_filename, "w", encoding="utf-8") as f:
                f.write(f"Title: {video_title}\n")
                f.write(f"URL: {url}\n")
                f.write(f"Language: {detected_language}\n\n")
                f.write(transcription)
        except Exception as e:
            tasks[task_id] = {
                'state': 'FAILURE',
                'status': f'Error saving transcription: {str(e)}'
            }
            return
        
        # Update task status
        tasks[task_id] = {
            'state': 'PROGRESS',
            'status': {'current': 10, 'total': 10, 'status': 'Cleaning up...'}
        }
        
        # Clean up WAV file (but keep MP3 and MP4 for download)
        try:
            os.remove(wav_audio)
            print(f"Removed WAV file: {wav_audio}")
        except Exception as e:
            print(f"Error removing WAV file: {str(e)}")
        
        # Return the result
        tasks[task_id] = {
            'state': 'SUCCESS',
            'result': {
                "success": True,
                "transcription": transcription,
                "title": video_title,
                "video_id": video_id,
                "language": detected_language,
                "txt_file": txt_filename,
                "mp3_file": mp3_audio,
                "mp4_file": mp4_video
            }
        }
        
    except Exception as e:
        tasks[task_id] = {
            'state': 'FAILURE',
            'status': f'Unexpected error: {str(e)}'
        }

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/transcribe', methods=['POST'])
def transcribe():
    url = request.form['url']
    try:
        # Validate URL format
        video_id = extract_video_id(url)
        if not video_id:
            return jsonify({"success": False, "error": "Invalid YouTube URL format"})
        
        # Generate a unique task ID
        task_id = str(uuid.uuid4())
        
        # Initialize task status
        tasks[task_id] = {
            'state': 'PENDING',
            'status': 'Pending...'
        }
        
        # Start the background thread
        thread = threading.Thread(target=transcribe_video, args=(task_id, url))
        thread.start()
        
        # Return the task ID so the client can check status
        return jsonify({
            "success": True,
            "task_id": task_id,
            "video_id": video_id,
            "message": "Transcription started. Please wait..."
        })
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})

@app.route('/status/<task_id>')
def task_status(task_id):
    if task_id in tasks:
        return jsonify(tasks[task_id])
    else:
        return jsonify({
            'state': 'FAILURE',
            'status': 'Task not found'
        })

@app.route('/download/<video_id>/<format>')
def download_file(video_id, format):
    if format == 'txt':
        file_path = f"downloads/{video_id}.txt"
        if os.path.exists(file_path):
            return send_file(file_path, as_attachment=True)
    
    elif format == 'mp3':
        # Check if the MP3 file exists
        file_path = f"downloads/{video_id}_audio.mp3"
        if os.path.exists(file_path):
            return send_file(file_path, as_attachment=True)
        
        # If MP3 doesn't exist, check if we have the original audio file
        if video_id in video_info and 'original_audio_file' in video_info[video_id]:
            original_file = video_info[video_id]['original_audio_file']
            if os.path.exists(original_file):
                return send_file(original_file, as_attachment=True, download_name=f"{video_id}_audio.mp3")
    
    elif format == 'mp4':
        # Check if the MP4 file exists
        file_path = f"downloads/{video_id}_video.mp4"
        if os.path.exists(file_path):
            return send_file(file_path, as_attachment=True)
        
        # If MP4 doesn't exist, check if we have the original video file
        if video_id in video_info and 'original_video_file' in video_info[video_id]:
            original_file = video_info[video_id]['original_video_file']
            if os.path.exists(original_file):
                return send_file(original_file, as_attachment=True, download_name=f"{video_id}_video.mp4")
    
    return "File not found", 404

if __name__ == '__main__':
    # Ensure downloads directory exists
    os.makedirs("downloads", exist_ok=True)
    print("Starting YouTube Transcriber...")
    print("Open your browser and go to http://127.0.0.1:5000")
    app.run(debug=True)