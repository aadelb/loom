import importlib
import sys
from pathlib import Path

sys.path.insert(0, str(Path('src').resolve()))

optional_modules = [
    "loom.tools.llm",
    "loom.tools.enrich",
    "loom.tools.experts",
    "loom.tools.creative",
    "loom.providers.youtube_transcripts",
    "loom.tools.vastai",
    "loom.tools.billing",
    "loom.tools.email_report",
    "loom.tools.joplin",
    "loom.tools.tor",
    "loom.tools.transcribe",
    "loom.tools.document",
    "loom.tools.metrics",
    "loom.tools.slack",
    "loom.tools.gcp",
    "loom.tools.vercel",
    "loom.tools.cipher_mirror",
    "loom.tools.forum_cortex",
    "loom.tools.onion_spectra",
    "loom.tools.ghost_weave",
    "loom.tools.dead_drop_scanner",
    "loom.tools.persona_profile",
    "loom.tools.radicalization_detect",
    "loom.tools.sentiment_deep",
    "loom.tools.network_persona",
    "loom.tools.text_analyze",
    "loom.tools.screenshot",
    "loom.tools.geoip_local",
    "loom.tools.image_intel",
    "loom.tools.ip_intel",
    "loom.tools.cve_lookup",
    "loom.tools.urlhaus_lookup"
]

print("--- 6. Silent import failures in server.py ---")
for mod in optional_modules:
    try:
        importlib.import_module(mod)
    except ImportError as e:
        print(f"Silent import failure: {mod} (Reason: {e})")
    except Exception as e:
        print(f"Silent failure (Other error): {mod} (Reason: {e})")
