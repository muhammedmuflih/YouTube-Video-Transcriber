from celery import Celery
import whisper
from pytube import YouTube
import os
import re
from urllib.parse import parse_qs, urlparse

# Configure Celery
celery = Celery('tasks', broker='C:\Users\ADMIN\Documents\youtube\Redis-x64-3.0.504.msi', backend='rpc://')

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
    
    parsed_url = urlparse(url)
    query_params = parse_qs(parsed_url.query)
    if 'v' in query_params:
        return query_params['v'][0]
    
    return None

@celery.task(bind=True)
def transcribe_video(self, url):
    try:
        # Extract video ID and validate
        video_id = extract_video_id(url)
        if not video_id:
            return {"success": False, "error": "Invalid YouTube URL format"}
        
        # Update task status
        self.update_state(
            state='PROGRESS',
            meta={'current': 1, 'total': 10, 'status': 'Extracting video info...'}
        )
        
        # Construct a clean URL
        clean_url = f"https://www.youtube.com/watch?v={video_id}"
        
        # Create YouTube object
        yt = YouTube(clean_url)
        
        # Update task status
        self.update_state(
            state='PROGRESS',
            meta={'current': 2, 'total': 10, 'status': 'Finding audio stream...'}
        )
        
        # Get audio stream
        audio_streams = yt.streams.filter(only_audio=True).order_by('abr').desc()
        
        if not audio_streams:
            return {"success": False, "error": "No audio streams available for this video"}
        
        audio_stream = audio_streams.first()
        
        # Update task status
        self.update_state(
            state='PROGRESS',
            meta={'current': 3, 'total': 10, 'status': 'Downloading audio...'}
        )
        
        # Download the audio
        audio_file = audio_stream.download(output_path="downloads", filename_prefix=f"{video_id}_")
        
        # Update task status
        self.update_state(
            state='PROGRESS',
            meta={'current': 4, 'total': 10, 'status': 'Loading speech recognition model...'}
        )
        
        # Load Whisper model
        model = whisper.load_model("base")
        
        # Update task status
        self.update_state(
            state='PROGRESS',
            meta={'current': 5, 'total': 10, 'status': 'Transcribing audio...'}
        )
        
        # Transcribe with language detection
        result = model.transcribe(
            audio_file,
            fp16=False,
            language=None,
            task="transcribe",
            verbose=False
        )
        
        transcription = result["text"]
        detected_language = result.get("language", "unknown")
        
        # Update task status
        self.update_state(
            state='PROGRESS',
            meta={'current': 8, 'total': 10, 'status': 'Saving transcription...'}
        )
        
        # Save transcription
        txt_filename = f"downloads/{video_id}.txt"
        with open(txt_filename, "w", encoding="utf-8") as f:
            f.write(f"Title: {yt.title}\n")
            f.write(f"URL: {clean_url}\n")
            f.write(f"Language: {detected_language}\n\n")
            f.write(transcription)
        
        # Update task status
        self.update_state(
            state='PROGRESS',
            meta={'current': 9, 'total': 10, 'status': 'Cleaning up...'}
        )
        
        # Clean up audio file to save space
        try:
            os.remove(audio_file)
        except:
            pass
        
        # Return the result
        return {
            "success": True,
            "transcription": transcription,
            "title": yt.title,
            "video_id": video_id,
            "language": detected_language,
            "txt_file": txt_filename
        }
        
    except Exception as e:
        return {"success": False, "error": str(e)}