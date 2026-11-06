import asyncio
import json
import logging

logger = logging.getLogger(__name__)

async def get_media_info(file_path: str) -> dict:
    """Use ffprobe to extract detailed media metadata."""
    cmd = [
        "ffprobe",
        "-v", "quiet",
        "-print_format", "json",
        "-show_format",
        "-show_streams",
        file_path
    ]
    
    try:
        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        stdout, stderr = await process.communicate()
        
        if process.returncode != 0:
            logger.error(f"ffprobe failed: {stderr.decode()}")
            return {}
            
        data = json.loads(stdout.decode())
        
        format_info = data.get("format", {})
        streams = data.get("streams", [])
        
        video_stream = next((s for s in streams if s["codec_type"] == "video"), {})
        audio_streams = [s for s in streams if s["codec_type"] == "audio"]
        
        metadata = {
            "resolution": f"{video_stream.get('width', '0')}x{video_stream.get('height', '0')}",
            "video_codec": video_stream.get("codec_name", "unknown"),
            "video_bitrate": int(video_stream.get("bit_rate", 0)) or int(format_info.get("bit_rate", 0)),
            "fps": eval(video_stream.get("r_frame_rate", "0/1")),
            "audio_codecs": [s.get("codec_name", "unknown") for s in audio_streams],
            "audio_languages": [s.get("tags", {}).get("language", "und") for s in audio_streams],
            "container": format_info.get("format_name", "unknown"),
            "size": int(format_info.get("size", 0)),
            "duration": float(format_info.get("duration", 0))
        }
        
        return metadata
    except Exception as e:
        logger.error(f"Error running ffprobe: {e}")
        return {}
