import os
import uuid
from pathlib import Path

import requests
import torch
import open_clip
from dotenv import load_dotenv
from flask import Flask, request, jsonify, send_from_directory, session, render_template
from flask_cors import CORS
from PIL import Image
from transformers import pipeline
from werkzeug.utils import secure_filename

from models import db, Post, Board

load_dotenv()

app = Flask(__name__)
CORS(app, supports_credentials=True)

app.secret_key = os.getenv("SECRET_KEY")
app.config["SQLALCHEMY_DATABASE_URI"] = os.getenv("DATABASE_URL")
app.config["UPLOAD_FOLDER"] = os.getenv("UPLOAD_FOLDER", "uploads")
app.config["MAX_CONTENT_LENGTH"] = 10 * 1024 * 1024

if not app.secret_key:
    raise RuntimeError("SECRET_KEY is missing in .env")

if not app.config["SQLALCHEMY_DATABASE_URI"]:
    raise RuntimeError("DATABASE_URL is missing in .env")

Path(app.config["UPLOAD_FOLDER"]).mkdir(exist_ok=True)

with app.app_context():
    db.init_app(app)
    db.create_all()


moderator = pipeline(
    "text-classification",
    model="unitary/toxic-bert",
    top_k=None
)

device = "cuda" if torch.cuda.is_available() else "cpu"
print(f"Device: {device}")

clip_model, _, preprocess = open_clip.create_model_and_transforms(
    "ViT-H-14",
    pretrained="laion2b_s32b_b79k"
)
clip_model.to(device).eval()


def normalize_board(board):
    return board.strip().lower().strip("/") if board else ""


def is_text_toxic(content, board):
    result = moderator(content or "")[0]

    scores = {item["label"]: item["score"] for item in result}

    toxic = scores.get("toxic", 0)
    severe = scores.get("severe_toxic", 0)
    insult = scores.get("insult", 0)
    hate = scores.get("identity_hate", 0)

    if board == "b":
        return toxic > 0.98 or severe > 0.98 or insult > 0.98 or hate > 0.98

    return toxic > 0.7 or severe > 0.5 or insult > 0.5 or hate > 0.5


def detect_nsfw_image(image_path):
    try:
        img = Image.open(image_path).convert("RGB")
        image_input = preprocess(img).unsqueeze(0).to(device)

        with torch.no_grad():
            clip_model.encode_image(image_input)

        return False

    except Exception as e:
        print("NSFW detection error:", e)
        return False


def save_uploaded_image(file):
    original_name = secure_filename(file.filename)
    ext = Path(original_name).suffix.lower()

    if ext not in [".jpg", ".jpeg", ".png", ".webp", ".gif"]:
        raise ValueError("Invalid image type")

    filename = f"{uuid.uuid4().hex}{ext}"
    path = Path(app.config["UPLOAD_FOLDER"]) / filename
    file.save(path)

    return filename, path


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/adminpanel")
def admin_panel():
    return render_template("admin.html")


@app.route("/post", methods=["POST"])
def create_post():
    user_id = request.form.get("user_id")
    board = request.form.get("board")
    content = request.form.get("content")

    if not board or not content:
        return jsonify({"success": False, "message": "Board and content are required"}), 400

    board_normalized = normalize_board(board)

    if is_text_toxic(content, board_normalized):
        return jsonify({
            "success": False,
            "message": "Post flagged as toxic or offensive"
        }), 400

    image = None
    is_nsfw = False

    if "image" in request.files:
        img = request.files["image"]

        if img and img.filename:
            try:
                image, image_path = save_uploaded_image(img)
            except ValueError as e:
                return jsonify({"success": False, "message": str(e)}), 400

            nsfw_detected = detect_nsfw_image(image_path)

            if nsfw_detected and board_normalized != "b":
                image_path.unlink(missing_ok=True)
                return jsonify({
                    "success": False,
                    "message": "NSFW images are only allowed on /b/"
                }), 400

            is_nsfw = nsfw_detected

    post = Post(
        user_id=user_id,
        board=board_normalized,
        content=content,
        image=image,
        is_approved=True,
        is_nsfw=is_nsfw
    )

    db.session.add(post)
    db.session.commit()

    return jsonify({"success": True})


@app.route("/posts/<board>", methods=["GET"])
def get_posts(board):
    board = normalize_board(board)

    posts = Post.query.filter_by(
        board=board,
        is_approved=True
    ).order_by(Post.id.desc()).all()

    return jsonify([
        {
            "id": post.id,
            "content": post.content,
            "image": post.image,
            "user_id": post.user_id,
            "is_nsfw": post.is_nsfw
        }
        for post in posts
    ])


@app.route("/uploads/<path:filename>")
def uploaded_file(filename):
    return send_from_directory(app.config["UPLOAD_FOLDER"], filename)


@app.route("/admin/login", methods=["POST"])
def admin_login():
    password = request.form.get("password")
    admin_password = os.getenv("ADMIN_PASSWORD")

    if not admin_password:
        return jsonify({"success": False, "message": "Admin password not configured"}), 500

    if password == admin_password:
        session["admin_logged_in"] = True
        return jsonify({"success": True})

    return jsonify({"success": False}), 401


@app.route("/admin/logout", methods=["POST"])
def admin_logout():
    session.pop("admin_logged_in", None)
    return jsonify({"success": True})


@app.route("/admin/check", methods=["GET"])
def admin_check():
    return jsonify({"logged_in": session.get("admin_logged_in", False)})


def admin_required():
    return session.get("admin_logged_in", False)


@app.route("/admin/posts", methods=["GET"])
def admin_get_posts():
    if not admin_required():
        return jsonify({"error": "Unauthorized"}), 401

    posts = Post.query.order_by(Post.id.desc()).all()

    return jsonify([
        {
            "id": post.id,
            "content": post.content,
            "image": post.image,
            "user_id": post.user_id,
            "board": post.board,
            "is_approved": post.is_approved,
            "is_nsfw": post.is_nsfw
        }
        for post in posts
    ])


@app.route("/admin/approve/<int:post_id>", methods=["POST"])
def approve_post(post_id):
    if not admin_required():
        return jsonify({"error": "Unauthorized"}), 401

    post = Post.query.get_or_404(post_id)
    post.is_approved = True
    db.session.commit()

    return jsonify({"success": True})


@app.route("/admin/delete/<int:post_id>", methods=["DELETE"])
def delete_post(post_id):
    if not admin_required():
        return jsonify({"error": "Unauthorized"}), 401

    post = Post.query.get_or_404(post_id)

    if post.image:
        image_path = Path(app.config["UPLOAD_FOLDER"]) / post.image
        image_path.unlink(missing_ok=True)

    db.session.delete(post)
    db.session.commit()

    return jsonify({"success": True})


@app.route("/clear_history", methods=["POST"])
def clear_history():
    if not admin_required():
        return jsonify({"error": "Unauthorized"}), 401

    try:
        Post.query.delete()
        db.session.commit()
        return jsonify({"success": True})

    except Exception as e:
        db.session.rollback()
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/create_board", methods=["POST"])
def create_board():
    if not admin_required():
        return jsonify({"error": "Unauthorized"}), 401

    data = request.get_json() or {}

    board_name = normalize_board(data.get("board"))
    nsfw_setting = bool(data.get("nsfw"))

    if not board_name:
        return jsonify({"success": False, "message": "Board name required"}), 400

    new_board = Board(name=board_name, nsfw=nsfw_setting)

    db.session.add(new_board)
    db.session.commit()

    return jsonify({"success": True, "message": "Board created successfully"})


@app.route("/gemini_chat", methods=["POST"])
def gemini_chat():
    try:
        data = request.get_json() or {}
        user_msg = data.get("message", "").strip()

        if not user_msg:
            return jsonify({"error": "No message provided"}), 400

        api_key = os.getenv("GEMINI_API_KEY")

        if not api_key:
            return jsonify({"error": "Gemini API key not set"}), 500

        api_url = (
            "https://generativelanguage.googleapis.com/v1beta/"
            f"models/gemini-pro:generateContent?key={api_key}"
        )

        payload = {
            "contents": [
                {
                    "parts": [
                        {"text": user_msg}
                    ]
                }
            ]
        }

        response = requests.post(api_url, json=payload, timeout=15)

        if response.status_code != 200:
            return jsonify({"error": "Gemini API error"}), 502

        result = response.json()

        bot_msg = (
            result.get("candidates", [{}])[0]
            .get("content", {})
            .get("parts", [{}])[0]
            .get("text", "No response")
        )

        return jsonify({"message": bot_msg})

    except Exception as e:
        return jsonify({"error": str(e)}), 500


if __name__ == "__main__":
    app.run(debug=True)
