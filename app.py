import os
import tempfile
import traceback
import base64

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

# ★ おしまい画面
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
# 表紙画像生成（重要）
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
            return jsonify({"ok": False, "error": "OpenAI設定がありません"}), 500

        # ★ テーマ別プロンプト（裸の動物防止）
        theme_map = {
            "red": (
                "『あかずきん』風の絵本表紙。"
                "森の小道、赤いずきんの雰囲気。"
                "子ども向け、やさしい表情。"
            ),
            "pigs": (
                "『3びきのこぶた』の絵本表紙。"
                "子ぶた3びきは【服を着た擬人化キャラクター】。"
                "帽子・ベスト・エプロンなどを身につけている。"
                "わらの家・木の家・れんがの家が背景に見える。"
                "【リアルな豚・裸・肌の質感は禁止】。"
            ),
            "bremen": (
                "『ブレーメンのおんがくたい』の絵本表紙。"
                "ろば・いぬ・ねこ・にわとりが仲よく行進。"
                "楽器は小さくかわいく、夜でも安心感のある雰囲気。"
            ),
            "peach": (
                "『ももたろう』風の絵本表紙。"
                "大きな桃、旅の道具、明るく元気な雰囲気。"
                "戦い・武器・こわさは描かない。"
            ),
            "red_oni": (
                "『ないたあかおに』風の絵本表紙。"
                "やさしい赤おに、友情のあたたかい雰囲気。"
            ),
        }

        theme_desc = theme_map.get(
            theme,
            f"子ども向け絵本の表紙。テーマは『{theme}』。"
        )

        safety_rules = (
            "文字は入れない。"
            "怖さ・暴力・流血表現は禁止。"
            "人物や動物は丸くかわいいデフォルメ。"
            "リアルな動物の質感・裸・肌の描写は禁止。"
            "背景はシンプルで見やすく。"
        )

        prompt = f"""
        子ども向け絵本の表紙イラスト。
        スタイル：やさしい水彩、パステル調、丸みのあるデザイン。
        内容：{theme_desc}
        ルール：{safety_rules}
        """

        img = client.images.generate(
            model="gpt-image-1",
            prompt=prompt,
            size="1024x1024"
        )

        image_bytes = base64.b64decode(img.data[0].b64_json)
        with open(out_path, "wb") as f:
            f.write(image_bytes)

        return jsonify({"ok": True, "path": f"/static/img/{theme}_cover.png"})

    except Exception as e:
        traceback.print_exc()
        return jsonify({"ok": False, "error": str(e)}), 500

# -------------------------
# 起動
# -------------------------
if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=True)
