import logging
import json
from typing import List, Union

from fastapi import FastAPI, HTTPException
from fastapi.responses import PlainTextResponse
from pydantic import BaseModel, Field
import requests

from app.config import settings

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("translation_service")

app = FastAPI(title=settings.app_name, version="1.0.0")

LANGUAGE_MAP = {
    "zh": "Chinese",
    "en": "English",
    "fr": "French",
    "pt": "Portuguese",
    "es": "Spanish",
    "ja": "Japanese",
    "tr": "Turkish",
    "ru": "Russian",
    "ar": "Arabic",
    "ko": "Korean",
    "th": "Thai",
    "it": "Italian",
    "de": "German",
    "vi": "Vietnamese",
    "ms": "Malay",
    "id": "Indonesian",
    "tl": "Filipino",
    "hi": "Hindi",
    "zh-hant": "Traditional Chinese",
    "pl": "Polish",
    "cs": "Czech",
    "nl": "Dutch",
    "km": "Khmer",
    "my": "Burmese",
    "fa": "Persian",
    "gu": "Gujarati",
    "ur": "Urdu",
    "te": "Telugu",
    "mr": "Marathi",
    "he": "Hebrew",
    "bn": "Bengali",
    "ta": "Tamil",
    "uk": "Ukrainian",
    "bo": "Tibetan",
    "kk": "Kazakh",
    "mn": "Mongolian",
    "ug": "Uyghur",
    "yue": "Cantonese"
}

def get_full_language_name(lang: str) -> str:
    lang_lower = lang.strip().lower()
    if lang_lower in LANGUAGE_MAP:
        return LANGUAGE_MAP[lang_lower]
    for code, name in LANGUAGE_MAP.items():
        if name.lower() == lang_lower:
            return name
    return lang.strip().capitalize()

class TranslationRequest(BaseModel):
    text: str = Field(..., description="The text to translate.")
    target_lang: str = Field(..., description="The target language code or full name (e.g. 'en', 'vi', 'zh', 'Japanese').")
    source_lang: str = Field(None, description="Optional source language code or name.")
    temperature: float = Field(None, description="Sampling temperature.")
    top_p: float = Field(None, description="Top-p sampling probability.")
    top_k: int = Field(None, description="Top-k filtering threshold.")
    repetition_penalty: float = Field(None, description="Repetition penalty.")
    max_tokens: int = Field(None, description="Maximum tokens to generate.")

def query_vllm_translation(
    source_text: str,
    tgt_lang_name: str,
    temperature: float,
    top_p: float,
    top_k: int,
    repetition_penalty: float,
    max_tokens: int
) -> str:
    prompt = f"Translate the following text into {tgt_lang_name}. Note that you should only output the translated result without any additional explanation:\n\n{source_text}"
    
    payload = {
        "model": settings.model_name,
        "messages": [
            {"role": "user", "content": prompt}
        ],
        "temperature": temperature,
        "top_p": top_p,
        "max_tokens": max_tokens,
        "repetition_penalty": repetition_penalty,
        "extra_body": {
            "top_k": top_k
        },
        "stream": False
    }
    
    headers = {"Content-Type": "application/json"}
    url = f"{settings.vllm_api_url.rstrip('/')}/chat/completions"
    
    try:
        response = requests.post(url, json=payload, headers=headers, timeout=60)
        response.raise_for_status()
        res_data = response.json()
        translated_text = res_data["choices"][0]["message"]["content"]
        return translated_text.strip()
    except Exception as e:
        logger.error(f"Error querying vLLM server: {e}")
        raise HTTPException(status_code=500, detail=f"vLLM server error: {e}")

@app.get("/health")
async def health():
    vllm_healthy = False
    try:
        url = f"{settings.vllm_api_url.rstrip('/')}/models"
        res = requests.get(url, timeout=5)
        if res.status_code == 200:
            vllm_healthy = True
    except Exception:
        pass

    return {
        "status": "healthy" if vllm_healthy else "vllm_unreachable",
        "vllm_api_url": settings.vllm_api_url,
        "model": settings.model_name
    }

@app.post("/translate", response_class=PlainTextResponse)
async def translate(request: TranslationRequest):
    tgt_lang_name = get_full_language_name(request.target_lang)
    
    temp = request.temperature if request.temperature is not None else settings.default_temperature
    tp = request.top_p if request.top_p is not None else settings.default_top_p
    tk = request.top_k if request.top_k is not None else settings.default_top_k
    rep_pen = request.repetition_penalty if request.repetition_penalty is not None else settings.default_repetition_penalty
    max_tok = request.max_tokens if request.max_tokens is not None else settings.default_max_tokens
    
    if not request.text.strip():
        return ""
        
    translated_text = query_vllm_translation(
        source_text=request.text,
        tgt_lang_name=tgt_lang_name,
        temperature=temp,
        top_p=tp,
        top_k=tk,
        repetition_penalty=rep_pen,
        max_tokens=max_tok
    )
    return translated_text
