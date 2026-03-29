from fastapi import FastAPI
from pydantic import BaseModel
from typing import Optional
import yt_dlp
import tempfile
import os
import re
from pathlib import Path

app = FastAPI(title="YouTube Transcript API")


class TranscriptRequest(BaseModel):
    videoId: str
    preferredLanguage: str = "ko"


class TranscriptResponse(BaseModel):
    success: bool
    transcriptText: str = ""
    language: Optional[str] = None
    source: Optional[str] = None
    error: Optional[str] = None


def clean_vtt_text(vtt_path: str) -> str:
    with open(vtt_path, "r", encoding="utf-8") as f:
        text = f.read()

    # WEBVTT 헤더 제거
    text = text.replace("WEBVTT", "")

    # 타임코드 제거
    text = re.sub(r"\d{2}:\d{2}:\d{2}\.\d{3}\s-->\s\d{2}:\d{2}:\d{2}\.\d{3}.*", "", text)
    text = re.sub(r"\d{2}:\d{2}\.\d{3}\s-->\s\d{2}:\d{2}\.\d{3}.*", "", text)

    # VTT 스타일/메타 제거
    text = re.sub(r"<[^>]+>", "", text)
    text = re.sub(r"NOTE.*", "", text)

    lines = []
    seen = set()

    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue
        # 숫자 인덱스 제거
        if line.isdigit():
            continue
        # 중복 연속 문장 줄이기
        if line not in seen:
            lines.append(line)
            seen.add(line)

    return "\n".join(lines).strip()


def find_subtitle_file(temp_dir: str) -> Optional[str]:
    exts = [".vtt", ".srt", ".srv3", ".ttml"]
    for file in Path(temp_dir).rglob("*"):
        if file.suffix.lower() in exts:
            return str(file)
    return None


@app.post("/transcript", response_model=TranscriptResponse)
def get_transcript(req: TranscriptRequest):
    video_url = f"https://www.youtube.com/watch?v={req.videoId}"

    with tempfile.TemporaryDirectory() as temp_dir:
        outtmpl = os.path.join(temp_dir, "%(id)s.%(ext)s")

        ydl_opts = {
            "skip_download": True,
            "writesubtitles": True,
            "writeautomaticsub": True,
            "subtitleslangs": [req.preferredLanguage, "ko", "en"],
            "subtitlesformat": "vtt/best",
            "outtmpl": outtmpl,
            "quiet": True,
            "no_warnings": True,
        }

        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(video_url, download=True)

            subtitle_file = find_subtitle_file(temp_dir)
            if not subtitle_file:
                return TranscriptResponse(
                    success=False,
                    error="No subtitle file found"
                )

            transcript_text = clean_vtt_text(subtitle_file)
            if not transcript_text:
                return TranscriptResponse(
                    success=False,
                    error="Subtitle file exists but transcript text is empty"
                )

            language = req.preferredLanguage
            source = "subtitle_or_auto"

            return TranscriptResponse(
                success=True,
                transcriptText=transcript_text,
                language=language,
                source=source
            )

        except Exception as e:
            return TranscriptResponse(
                success=False,
                error=str(e)
            )


@app.get("/health")
def health():
    return {"ok": True}