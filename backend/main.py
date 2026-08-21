"""FastAPI app — see CLAUDE.md Section 7. Routes dispatch by trigger type
straight to the matching agent function; no supervisor/intent-classifier
layer, per the deliberate rule-based routing decision."""

import logging

from fastapi import Depends, FastAPI, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from agents.article_insight import get_article_insight
from agents.ask_ai import ask_ai
from agents.insight import get_insight
from agents.recommendation import get_recommendations
from agents.signal_ingestion import log_signal
from agents.simplify import simplify_content
from agents.summarize import summarize_content
from agents.takeaways import get_takeaways
from agents.translate import translate_content
from agents.video_transcript_summary import get_video_summary
from db import get_db

logger = logging.getLogger(__name__)

app = FastAPI(title="Beyond Portal Agent POC")


class SignalRequest(BaseModel):
    user_id: str
    content_id: str
    signal_type: str
    depth_pct: float | None = None


class SummarizeRequest(BaseModel):
    content_id: str


class SimplifyRequest(BaseModel):
    content_id: str


class TranslateRequest(BaseModel):
    content_id: str
    target_language: str


class AskAIRequest(BaseModel):
    user_id: str
    question: str


class VideoSummaryRequest(BaseModel):
    content_id: str | None = None
    video_url: str | None = None


class ArticleInsightRequest(BaseModel):
    content_id: str


class TakeawaysRequest(BaseModel):
    content_id: str


def _handle(fn, *args, **kwargs):
    """Every route's external-call/bad-input failures land here so nothing
    leaks a raw traceback or DB error to the client (Section 5/11.1). The
    HTTP response stays generic, but the real exception is always logged
    server-side (logger.exception includes the full traceback) so it's
    still debuggable from the console."""
    try:
        return fn(*args, **kwargs)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except RuntimeError as exc:
        logger.exception("Handled RuntimeError in %s", fn.__name__)
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    except Exception as exc:
        logger.exception("Unexpected error in %s", fn.__name__)
        raise HTTPException(status_code=500, detail="An unexpected error occurred") from exc


@app.post("/signals")
def create_signal(body: SignalRequest, db: Session = Depends(get_db)):
    return _handle(log_signal, db, body.user_id, body.content_id, body.signal_type, body.depth_pct)


@app.get("/recommendations/{user_id}")
def recommendations(user_id: str, db: Session = Depends(get_db)):
    return _handle(get_recommendations, db, user_id)


@app.post("/summarize")
def summarize(body: SummarizeRequest, db: Session = Depends(get_db)):
    return _handle(summarize_content, db, body.content_id)


@app.post("/simplify")
def simplify(body: SimplifyRequest, db: Session = Depends(get_db)):
    return _handle(simplify_content, db, body.content_id)


@app.post("/translate")
def translate(body: TranslateRequest, db: Session = Depends(get_db)):
    return _handle(translate_content, db, body.content_id, body.target_language)


@app.get("/insights/{user_id}")
def insights(user_id: str, db: Session = Depends(get_db)):
    return _handle(get_insight, db, user_id)


@app.post("/ask-ai")
def ask_ai_route(body: AskAIRequest, db: Session = Depends(get_db)):
    return _handle(ask_ai, db, body.user_id, body.question)


@app.post("/video-summary")
def video_summary(body: VideoSummaryRequest, db: Session = Depends(get_db)):
    return _handle(get_video_summary, db, body.content_id, body.video_url)


@app.post("/article-insight")
def article_insight(body: ArticleInsightRequest, db: Session = Depends(get_db)):
    return _handle(get_article_insight, db, body.content_id)


@app.post("/takeaways")
def takeaways(body: TakeawaysRequest, db: Session = Depends(get_db)):
    return _handle(get_takeaways, db, body.content_id)
