// HER REAL VOICE manifest — normalized line → mp3 file in mobile-voice/.
// Rendered once via /v2/tts (OpenAI, her laptop voice identity). Empty entries
// fall through to session-TTS → speechSynthesis → chime+caption, so the page
// works even before rendering.
window.NOVA_VOICE_MANIFEST = {};
