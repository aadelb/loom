"""Google Cloud Vision and Text-to-Speech integration.

Tools:
- research_image_analyze: Analyze images using Google Cloud Vision API
- research_text_to_speech: Convert text to speech using Google Cloud TTS
"""

from __future__ import annotations

import base64
import logging
import os
from pathlib import Path
from typing import Any

import httpx

from loom.validators import PathSafetyError, validate_local_file_path
from loom.error_responses import handle_tool_errors

logger = logging.getLogger("loom.tools.gcp")

# Google Cloud API endpoints
_GCP_VISION_API = "https://vision.googleapis.com/v1/images:annotate"
_GCP_TTS_API = "https://texttospeech.googleapis.com/v1/text:synthesize"
_GCP_VOICES_API = "https://texttospeech.googleapis.com/v1/voices"

# Constraints
MAX_IMAGE_SIZE_BYTES = 20 * 1024 * 1024  # 20 MB
MAX_TEXT_CHARS = 5000

# Supported TTS voices (extended list for all language codes)
_TTS_VOICE_SAMPLES = {
    "en-US-Neural2-A": "Female US English",
    "en-US-Neural2-C": "Male US English",
    "en-GB-Neural2-A": "Female UK English",
    "en-GB-Neural2-B": "Male UK English",
    "es-ES-Neural2-A": "Female Spanish",
    "fr-FR-Neural2-A": "Female French",
    "de-DE-Neural2-A": "Female German",
    "it-IT-Neural2-A": "Female Italian",
    "ja-JP-Neural2-A": "Female Japanese",
    "zh-CN-Standard-A": "Female Mandarin Chinese",
}


def _validate_gcp_key(key: str) -> bool:
    """Validate GCP API key format.

    Args:
        key: API key string

    Returns:
        True if appears valid, False otherwise
    """
    return len(key) > 20 and key.startswith("AIza")


def _load_gcp_credentials() -> str | None:
    """Load GCP API key from environment.

    Checks:
    1. GOOGLE_AI_KEY (API key)
    2. GOOGLE_CLOUD_API_KEY (fallback)
    3. GOOGLE_API_KEY (fallback)

    Returns:
        API key string or None if not found
    """
    api_key = (
        os.environ.get("GOOGLE_AI_KEY")
        or os.environ.get("GOOGLE_CLOUD_API_KEY")
        or os.environ.get("GOOGLE_API_KEY")
    )
    return api_key


@handle_tool_errors("research_image_analyze")
async def research_image_analyze(
    image_url: str,
    features: list[str] | None = None,
    max_results: int = 10,
) -> dict[str, Any]:
    """Analyze images using Google Cloud Vision API.

    Detects labels, text, faces, landmarks, logos, and other features
    in images provided via URL or base64 encoding.

    Requires GOOGLE_AI_KEY (or GOOGLE_CLOUD_API_KEY) environment variable
    with Vision API enabled.

    Args:
        image_url: public image URL (https://) or local file path under ~/.loom/.
            Local files are base64 encoded before sending.
        features: list of detection features. Defaults to ["LABEL_DETECTION",
            "TEXT_DETECTION"]. Options: LABEL_DETECTION, TEXT_DETECTION,
            FACE_DETECTION, LANDMARK_DETECTION, LOGO_DETECTION, SAFE_SEARCH_DETECTION,
            IMAGE_PROPERTIES, OBJECT_LOCALIZATION, WEB_DETECTION
        max_results: max results per feature type (1-100, default 10)

    Returns:
        Dict with keys:
        - status: "success" or "failed"
        - features: detected features with confidence scores
        - text: OCR text if TEXT_DETECTION enabled
        - labels: detected labels if LABEL_DETECTION enabled
        - safe_search: safety attributes (adult, spoof, medical, violence, racy)
        - error: error message on failure
    """
    # Validate inputs
    if not image_url:
        return {
            "status": "failed",
            "error": "image_url is required",
        }

    if max_results < 1 or max_results > 100:
        return {
            "status": "failed",
            "error": "max_results must be 1-100",
        }

    # Validate and set default features
    valid_features = {
        "LABEL_DETECTION",
        "TEXT_DETECTION",
        "FACE_DETECTION",
        "LANDMARK_DETECTION",
        "LOGO_DETECTION",
        "SAFE_SEARCH_DETECTION",
        "IMAGE_PROPERTIES",
        "OBJECT_LOCALIZATION",
        "WEB_DETECTION",
    }

    if features is None:
        features = ["LABEL_DETECTION", "TEXT_DETECTION"]
    elif not features:
        return {
            "status": "failed",
            "error": "features list cannot be empty",
        }
    else:
        invalid = [f for f in features if f not in valid_features]
        if invalid:
            return {
                "status": "failed",
                "error": f"invalid features: {', '.join(invalid)}",
                "valid_features": sorted(valid_features),
            }
        features = list(dict.fromkeys(features))  # Remove duplicates while preserving order

    # Get API key
    api_key = _load_gcp_credentials()
    if not api_key:
        logger.error("gcp_vision_missing_credentials")
        return {
            "status": "failed",
            "error": "missing GCP credentials",
            "details": "set GOOGLE_AI_KEY (or GOOGLE_CLOUD_API_KEY) environment variable",
        }

    # Prepare image source
    image_source: dict[str, Any] = {}

    if image_url.startswith("http://") or image_url.startswith("https://"):
        # URL reference
        image_source["imageUrl"] = {"url": image_url}
    else:
        # Validate local file path before attempting to read
        try:
            validated_path = validate_local_file_path(image_url)
        except PathSafetyError as e:
            logger.warning("gcp_vision_path_validation_failed: %s", e)
            return {
                "status": "failed",
                "error": str(e),
            }

        # Check if file exists
        if not os.path.isfile(validated_path):
            return {
                "status": "failed",
                "error": "image file not found",
            }

        # Local file — read and encode as base64
        try:
            with open(validated_path, "rb") as f:
                image_bytes = f.read(MAX_IMAGE_SIZE_BYTES + 1)
                if len(image_bytes) > MAX_IMAGE_SIZE_BYTES:
                    return {
                        "status": "failed",
                        "error": f"image exceeds {MAX_IMAGE_SIZE_BYTES / 1024 / 1024:.0f} MB",
                    }
                image_base64 = base64.b64encode(image_bytes).decode("utf-8")
                image_source["content"] = image_base64
        except FileNotFoundError:
            return {
                "status": "failed",
                "error": "image file not found",
            }
        except Exception as e:
            logger.error("gcp_vision_file_read_error: %s", e)
            return {
                "status": "failed",
                "error": "failed to read image file",
                "details": str(e)[:200],
            }

    # Build Vision API request
    request_body = {
        "requests": [
            {
                "image": image_source,
                "features": [
                    {"type": feature_type, "maxResults": max_results}
                    for feature_type in features
                ],
            }
        ]
    }

    # Call Vision API
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            logger.info("gcp_vision_analyze url_type=%s features=%s", "url" if image_url.startswith("http") else "local_file", features)

            response = await client.post(
                _GCP_VISION_API,
                json=request_body,
                headers={"X-Goog-Api-Key": api_key},
            )

            if response.status_code != 200:
                logger.error("gcp_vision_http_error status=%d", response.status_code)
                return {
                    "status": "failed",
                    "error": f"HTTP {response.status_code}",
                    "details": response.text[:500],
                }

            result = response.json()

            # Check for API errors
            if "error" in result:
                error_detail = result["error"]
                logger.error("gcp_vision_api_error: %s", error_detail)
                return {
                    "status": "failed",
                    "error": error_detail.get("message", "unknown error"),
                    "code": error_detail.get("code"),
                }

            # Extract responses
            if not result.get("responses"):
                return {
                    "status": "failed",
                    "error": "no responses from Vision API",
                }

            response_data = result["responses"][0]

            # Build result
            analysis: dict[str, Any] = {
                "status": "success",
                "features": {},
            }

            # Labels
            if "labelAnnotations" in response_data:
                analysis["labels"] = [
                    {
                        "description": item["description"],
                        "score": round(item["score"], 3),
                    }
                    for item in response_data["labelAnnotations"]
                ]

            # Text (OCR)
            if "textAnnotations" in response_data:
                annotations = response_data["textAnnotations"]
                if annotations:
                    analysis["text"] = annotations[0].get("description", "")
                    analysis["text_blocks"] = [
                        {
                            "text": item["description"],
                            "confidence": round(item.get("confidence", 0), 3),
                        }
                        for item in annotations[1:10]  # Skip full text, take first 10 blocks
                    ]

            # Faces
            if "faceAnnotations" in response_data:
                analysis["faces"] = [
                    {
                        "confidence": round(item["detectionConfidence"], 3),
                        "joy": item.get("joyLikelihood", "UNKNOWN"),
                        "anger": item.get("angerLikelihood", "UNKNOWN"),
                    }
                    for item in response_data["faceAnnotations"]
                ]

            # Safe Search
            if "safeSearchAnnotation" in response_data:
                safe = response_data["safeSearchAnnotation"]
                analysis["safe_search"] = {
                    "adult": safe.get("adult", "UNKNOWN"),
                    "spoof": safe.get("spoof", "UNKNOWN"),
                    "medical": safe.get("medical", "UNKNOWN"),
                    "violence": safe.get("violence", "UNKNOWN"),
                    "racy": safe.get("racy", "UNKNOWN"),
                }

            # Image properties
            if "imagePropertiesAnnotation" in response_data:
                props = response_data["imagePropertiesAnnotation"]
                if "dominantColors" in props:
                    analysis["dominant_colors"] = [
                        {
                            "color_hex": color["color"].get("name", "unknown"),
                            "score": round(color.get("score", 0), 3),
                            "pixel_fraction": round(color.get("pixelFraction", 0), 3),
                        }
                        for color in props["dominantColors"][:5]
                    ]

            logger.info("gcp_vision_success features=%d", len(analysis.get("features", {})))
            return analysis

    except httpx.TimeoutException:
        logger.error("gcp_vision_timeout")
        return {
            "status": "failed",
            "error": "Google Cloud Vision API timeout",
        }
    except Exception as e:
        logger.error("gcp_vision_error: %s", e)
        return {
            "status": "failed",
            "error": "unexpected error",
            "details": str(e)[:200],
        }


@handle_tool_errors("research_text_to_speech")
async def research_text_to_speech(
    text: str,
    language: str = "en",
    voice: str = "en-US-Neural2-A",
    speaking_rate: float = 1.0,
) -> dict[str, Any]:
    """Convert text to speech using Google Cloud Text-to-Speech.

    Synthesizes natural-sounding speech from text. Returns base64-encoded
    audio data (MP3 format).

    Requires GOOGLE_AI_KEY (or GOOGLE_CLOUD_API_KEY) environment variable
    with Text-to-Speech API enabled.

    Args:
        text: text to synthesize (max 5000 chars)
        language: language code (e.g., "en", "es", "fr"). Defaults to "en".
        voice: voice ID in format LANGUAGE-REGION-NEURAL2-VARIANT.
            Examples: en-US-Neural2-A, en-GB-Neural2-B, es-ES-Neural2-A.
            See research_tts_voices() for full list.
        speaking_rate: speech rate (0.25-4.0, default 1.0). <1 = slower, >1 = faster.

    Returns:
        Dict with keys:
        - status: "success" or "failed"
        - audio_base64: base64-encoded MP3 audio
        - audio_content: raw base64 (for convenience)
        - config: voice config used
        - error: error message on failure
    """
    # Validate text
    if not text:
        return {
            "status": "failed",
            "error": "text is required",
        }

    if len(text) > MAX_TEXT_CHARS:
        return {
            "status": "failed",
            "error": f"text exceeds {MAX_TEXT_CHARS} chars",
        }

    # Validate voice
    if voice not in _TTS_VOICE_SAMPLES:
        return {
            "status": "failed",
            "error": f"unsupported voice: {voice}",
            "details": f"supported: {', '.join(_TTS_VOICE_SAMPLES.keys())}",
        }

    # Validate language code (basic pattern: two-letter codes like "en", "es", "fr")
    if not isinstance(language, str) or len(language) < 2 or not language.replace("-", "").isalnum():
        return {
            "status": "failed",
            "error": "invalid language code format",
            "example": "en, es, fr, ja, zh",
        }

    # Validate speaking rate
    if speaking_rate < 0.25 or speaking_rate > 4.0:
        return {
            "status": "failed",
            "error": "speaking_rate must be 0.25-4.0",
        }

    # Get API key
    api_key = _load_gcp_credentials()
    if not api_key:
        logger.error("gcp_tts_missing_credentials")
        return {
            "status": "failed",
            "error": "missing GCP credentials",
            "details": "set GOOGLE_AI_KEY (or GOOGLE_CLOUD_API_KEY) environment variable",
        }

    # Build TTS request
    request_body = {
        "input": {"text": text},
        "voice": {
            "languageCode": language,
            "name": voice,
        },
        "audioConfig": {
            "audioEncoding": "MP3",
            "speakingRate": speaking_rate,
        },
    }

    # Call TTS API
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            logger.info("gcp_tts_synthesize voice=%s rate=%.2f chars=%d", voice, speaking_rate, len(text))

            response = await client.post(
                _GCP_TTS_API,
                json=request_body,
                headers={"X-Goog-Api-Key": api_key},
            )

            if response.status_code != 200:
                logger.error("gcp_tts_http_error status=%d", response.status_code)
                return {
                    "status": "failed",
                    "error": f"HTTP {response.status_code}",
                    "details": response.text[:500],
                }

            result = response.json()

            # Check for API errors
            if "error" in result:
                error_detail = result["error"]
                logger.error("gcp_tts_api_error: %s", error_detail)
                return {
                    "status": "failed",
                    "error": error_detail.get("message", "unknown error"),
                    "code": error_detail.get("code"),
                }

            # Extract audio content
            audio_base64 = result.get("audioContent", "")
            if not audio_base64:
                return {
                    "status": "failed",
                    "error": "no audio content in response",
                }

            logger.info("gcp_tts_success audio_size_b64=%d", len(audio_base64))

            return {
                "status": "success",
                "audio_base64": audio_base64,
                "config": {
                    "voice": voice,
                    "language": language,
                    "speaking_rate": speaking_rate,
                },
                "note": "audio_base64 is base64-encoded MP3. Decode and save as .mp3 file.",
            }

    except httpx.TimeoutException:
        logger.error("gcp_tts_timeout")
        return {
            "status": "failed",
            "error": "Google Cloud TTS API timeout",
        }
    except Exception as e:
        logger.error("gcp_tts_error: %s", e)
        return {
            "status": "failed",
            "error": "unexpected error",
            "details": str(e)[:200],
        }


@handle_tool_errors("research_tts_voices")
async def research_tts_voices() -> dict[str, Any]:
    """List supported Text-to-Speech voices.

    Fetches from Google Cloud TTS API if API key available, otherwise
    returns cached list of common voices.

    Returns:
        Dict with supported voices and descriptions
    """
    api_key = _load_gcp_credentials()

    # If API key available, try to fetch live list from Google Cloud
    if api_key:
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(
                    _GCP_VOICES_API,
                    headers={"X-Goog-Api-Key": api_key},
                )
                if response.status_code == 200:
                    result = response.json()
                    voices = {}
                    for voice in result.get("voices", []):
                        voice_name = voice.get("name", "")
                        lang_code = voice.get("languageCodes", ["unknown"])[0]
                        voices[voice_name] = f"{lang_code} - {voice.get('ssmlGender', 'unknown')}"
                    if voices:
                        logger.info("gcp_tts_voices_fetched count=%d", len(voices))
                        return {
                            "status": "success",
                            "voices": voices,
                            "source": "google_cloud_api",
                            "note": "Use voice IDs in research_text_to_speech(voice=...) parameter",
                        }
        except Exception as e:
            logger.debug("gcp_voices_fetch_failed: %s", e)

    # Fall back to cached list
    return {
        "status": "success",
        "voices": _TTS_VOICE_SAMPLES,
        "source": "cached",
        "note": "Use voice IDs in research_text_to_speech(voice=...) parameter. For full list, set GOOGLE_AI_KEY.",
    }
