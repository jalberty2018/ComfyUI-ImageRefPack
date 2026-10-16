from pathlib import Path

SOURCE = (Path(__file__).parents[1] / "web" / "image_refpack.js").read_text(encoding="utf-8")

def test_frontend_uses_fixed_image_canvas_and_two_slots():
    assert 'const KINDS = ["image"]' in SOURCE
    assert "const CAPS = { image: 2 }" in SOURCE
    assert "const GRID_COLUMNS = tenImages ? 5 : 2" in SOURCE
    assert "const GRID_ROWS = tenImages ? 2 : 1" in SOURCE
    assert "width: 420" in SOURCE
    assert "bottomPad: 14" in SOURCE
    assert 'document.createElement("canvas")' in SOURCE
    assert "drawAddSquare" in SOURCE
    assert "openEditModal" in SOURCE

def test_frontend_does_not_expose_prompt_video_or_audio_controls():
    custom_block = SOURCE.split("function buildCustomBlock(node)", 1)[1].split("// Config (reference pack)", 1)[0]
    registration = SOURCE.split("app.registerExtension({", 1)[1]
    assert '"video", "Video"' not in custom_block
    assert '"audio", "Audio"' not in custom_block
    assert "mmrp-uploads" not in custom_block
    assert "Save config" not in custom_block
    assert "Load config" not in custom_block
    assert "Local LLM" not in custom_block
    assert "Director" not in custom_block
    assert "directionInput" not in custom_block
    assert 'widgetByName(node, "prompt_provider")' not in registration
    assert "installDirectorRunHook" not in registration


def test_current_frontend_registration():
    assert 'tenImages ? "LSImageReferenceManagerUpload" : "LSImageUploadFirstLastReferencePack"' in SOURCE
    assert 'tenImages ? "LSImageReferenceManager" : "LSImageLocalInputFirstLastReferencePack"' in SOURCE
    assert 'while (this.outputs?.length > names.length)' in SOURCE
