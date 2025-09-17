

```markdown
# YouTube Video Transcriber

A web application that converts YouTube videos to text with real-time progress tracking. This project solves the problem of long waiting times during transcription by providing detailed progress updates and efficient chunked processing.

## Features

- **Real-time Progress Tracking**: Detailed status updates at each step of transcription
- **Time Estimates**: Calculates and displays estimated remaining time
- **Chunked Processing**: Splits audio into segments for smoother progress updates
- **Multi-format Downloads**: 
  - Text transcription (TXT)
  - Audio (MP3)
  - Video (MP4)
- **Language Detection**: Automatically detects the video language
- **Responsive Design**: Works on desktop and mobile devices



## Installation

### Prerequisites

- Python 3.8+
- FFmpeg (included in the project)
- Internet connection for downloading models and videos

### Setup

1. Clone the repository:
```bash
git clone https://github.com/your-username/youtube-transcriber.git
cd youtube-transcriber
```

2. Create and activate a virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Run the application:
```bash
python app.py
```

5. Open your browser and navigate to `http://127.0.0.1:5000`

## Usage

1. Enter a YouTube video URL in the input field
2. Click "Transcribe" to start the process
3. Monitor the progress bar and status updates
4. Once complete, view the transcription and download files as needed

## Technology Stack

- **Frontend**: HTML5, CSS3, JavaScript
- **Backend**: Flask (Python)
- **Speech Recognition**: Whisper (OpenAI)
- **Video Download**: yt-dlp
- **Audio Processing**: FFmpeg
- **Threading**: Background task processing

## Project Structure

```
youtube-transcriber/
├── app.py                 # Main Flask application
├── requirements.txt       # Python dependencies
├── templates/
│   └── index.html         # Main UI template
├── downloads/             # Storage for downloaded files
├── ffmpeg.exe             # FFmpeg binary
└── README.md              # This file
```

## API Endpoints

- `GET /` - Main interface
- `POST /transcribe` - Start transcription task
- `GET /status/<task_id>` - Check task status
- `GET /download/<video_id>/<format>` - Download files (txt, mp3, mp4)

## How It Works

1. **Video Download**: Uses yt-dlp to download audio and video
2. **Audio Conversion**: Converts audio to WAV format using FFmpeg
3. **Chunked Processing**: Splits audio into 30-second segments
4. **Transcription**: Processes each segment with Whisper
5. **Progress Tracking**: Updates status after each segment
6. **Result Compilation**: Combines segments and saves results
7. **Cleanup**: Removes temporary files

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

1. Fork the project
2. Create your feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Acknowledgments

- [OpenAI Whisper](https://github.com/openai/whisper) for speech recognition
- [yt-dlp](https://github.com/yt-dlp/yt-dlp) for video downloading
- [Flask](https://flask.palletsprojects.com/) for the web framework

## Future Enhancements

- Support for additional video platforms (Vimeo, Dailymotion)
- Transcription in multiple languages simultaneously
- Speaker diarization (identifying different speakers)
- Cloud storage integration (Google Drive, Dropbox)
- Mobile application

## Support

If you encounter any issues or have questions, please open an issue on GitHub.

---

**Note**: This application is for educational and personal use only. Please respect YouTube's terms of service and copyright laws when using this tool.
```
