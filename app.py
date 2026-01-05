import os
import tempfile
import traceback

from flask import Flask, jsonify, send_file, request, render_template
from dotenv import load_dotenv

# -------------------------
# 初期化
# -------------------------
app = Flask(__name__)
load_dotenv()

OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY") or os.environ.get("API_KEY")

# OpenAI クライアント
client = None
client_error = None
try:
    from openai import OpenAI
    client = OpenAI(api_key=OPENAI_API_KEY)
except Exception as e:
    client = None
    client_error = str(e)

# -------------------------
# 画面ルート
# -------------------------
@app.get("/")
def index():
    return render_template("index.html")

@app.get("/select")
def select():
    return render_template("select.html")

@app.get("/story")
def story():
    theme = request.args.get("theme", "red")
    return render_template("story.html", theme=theme)

# ★★★ ここが重要：おしまい画面 ★★★
@app.get("/story_end")
def story_end():
    theme = request.args.get("theme", "red")
    return render_template("story_end.html", theme=theme)

# -------------------------
# ヘルスチェック
# -------------------------
@app.get("/health")
def health():
    return jsonify({
        "ok": True,
        "has_key": bool(OPENAI_API_KEY),
        "client_ready": client is not None,
        "client_error": client_error
    })

# -------------------------
# 音声生成（TTS）
# -------------------------
def generate_mp3(text: str, voice: str = "nova") -> str:
    if client is None:
        raise RuntimeError(f"OpenAI client が初期化されていません: {client_error}")

    with tempfile.NamedTemporaryFile(delete=False, suffix=".mp3") as f:
        mp3_path = f.name

    speech = client.audio.speech.create(
        model="gpt-4o-mini-tts",
        voice=voice,
        input=text
    )
    speech.stream_to_file(mp3_path)
    return mp3_path

@app.post("/tts")
def tts():
    try:
        body = request.get_json(silent=True) or {}
        text = (body.get("text") or "").strip()

        if not text:
            return jsonify({"ok": False, "error": "text が空です"}), 400

        mp3_path = generate_mp3(text=text, voice="nova")
        return send_file(mp3_path, mimetype="audio/mpeg", as_attachment=False)

    except Exception as e:
        traceback.print_exc()
        return jsonify({"ok": False, "error": str(e)}), 500

# -------------------------
# 表紙画像生成
# -------------------------
@app.post("/api/generate_cover")
def generate_cover():
    try:
        body = request.get_json(silent=True) or {}
        theme = body.get("theme", "red")

        out_dir = os.path.join(app.root_path, "static", "img")
        os.makedirs(out_dir, exist_ok=True)
        out_path = os.path.join(out_dir, f"{theme}_cover.png")

        if client is None:
            return jsonify({
                "ok": False,
                "error": "OpenAI設定がありません"
            }), 500

        prompt = f"""
        子ども向け絵本の表紙イラスト。
        やさしい水彩、パステル調。
        テーマ：{theme}
        文字なし。怖さなし。
        """

        img = client.images.generate(
            model="gpt-image-1",
            prompt=prompt,
            size="1024x1024"
        )

        image_bytes = img.data[0].b64_json
        import base64
        with open(out_path, "wb") as f:
            f.write(base64.b64decode(image_bytes))

        return jsonify({"ok": True, "path": f"/static/img/{theme}_cover.png"})

    except Exception as e:
        traceback.print_exc()
        return jsonify({"ok": False, "error": str(e)}), 500

# -------------------------
# 起動
# -------------------------
if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=True)
