from fastapi import FastAPI
from pydantic import BaseModel
from youtube_transcript_api import YouTubeTranscriptApi

app = FastAPI()
ytt_api = YouTubeTranscriptApi()


class TranscriptRequest(BaseModel):
    videoId: str
    preferredLanguage: str = "ko"


@app.get("/health")
def health():
    return {"ok": True}


@app.post("/transcript")
def get_transcript(req: TranscriptRequest):
    try:
        video_id = req.videoId.strip()

        if not video_id:
            return {
                "success": False,
                "transcriptText": "",
                "language": "",
                "source": "youtube-transcript-api",
                "error": "videoId is required"
            }

        fetched = ytt_api.fetch(
            video_id,
            languages=[req.preferredLanguage, "ko", "en"]
        )

        transcript_text = " ".join(
            snippet.text.strip()
            for snippet in fetched
            if getattr(snippet, "text", "").strip()
        )

        return {
            "success": True,
            "transcriptText": transcript_text,
            "language": getattr(fetched, "language_code", req.preferredLanguage),
            "source": "youtube-transcript-api",
            "error": None
        }

    except Exception as e:
        return {
            "success": False,
            "transcriptText": "",
            "language": "",
            "source": "youtube-transcript-api",
            "error": str(e)
        }
