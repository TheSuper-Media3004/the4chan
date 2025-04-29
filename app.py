import os
from flask import Flask, request, jsonify, send_from_directory, session, render_template
from flask_cors import CORS
from models import db, Post
from dotenv import load_dotenv
from transformers import pipeline
from PIL import Image
import torch
import open_clip
load_dotenv()

app = Flask(__name__)
CORS(app, supports_credentials=True)

app.secret_key = os.getenv('SECRET_KEY', '5c8d9e6b3f7a4d1e2c9b0f8a7d6e5c4f')
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL', 'mysql+pymysql://root:Razor%402005@localhost:3306/mysql')
app.config['UPLOAD_FOLDER'] = os.getenv('UPLOAD_FOLDER', 'uploads')

db.init_app(app)
with app.app_context():
    db.create_all()

moderator = pipeline("text-classification", model="unitary/toxic-bert", top_k=None)

device = "cuda" if torch.cuda.is_available() else "cpu"
print(f"Device set to use {device}")

clip_model, _, preprocess = open_clip.create_model_and_transforms('ViT-H-14', pretrained='laion2b_s32b_b79k')
clip_model.to(device).eval()

def detect_nsfw_image(image_path):
    try:
        img = Image.open(image_path).convert("RGB")
        image_input = preprocess(img).unsqueeze(0).to(device)

        with torch.no_grad():
            image_features = clip_model.encode_image(image_input)

        print(f"Extracted image features shape: {image_features.shape}")
        return False  # TODO: Implement NSFW classification here

    except Exception as e:
        print("Error in NSFW detection:", e)
        return False

@app.route("/")
def index():
    return render_template('index.html')

@app.route("/adminpanel")
def admin_panel():
    return render_template('admin.html')

@app.route("/post", methods=["POST"])
def create_post():
    user_id = request.form.get("user_id")
    board = request.form.get("board")
    content = request.form.get("content")
    image = None
    is_nsfw = False

    # Text moderation
    print("Received content:", content)
    result = moderator(content)[0]
    print("Moderation result:", result)
    
    for r in result:
        print(f"Label: {r['label']}, Score: {r['score']}")
    toxic_score = next((r['score'] for r in result if r['label'] == 'toxic'), 0)
    severe_toxic_score = next((r['score'] for r in result if r['label'] == 'severe_toxic'), 0)
    insult_score = next((r['score'] for r in result if r['label'] == 'insult'), 0)
    identity_hate_score = next((r['score'] for r in result if r['label'] == 'identity_hate'), 0)
    board_normalized = board.strip().lower().strip('/') if board else ""


    if board_normalized == "b":
        # Very lenient: only block if extremely toxic
        if toxic_score > 0.98 or severe_toxic_score > 0.98 or insult_score > 0.98 or identity_hate_score > 0.98:
            return jsonify({"success": False, "message": "Post flagged as extremely toxic or offensive (even /b/ has limits)"}), 400
    else:

        if toxic_score > 0.7 or severe_toxic_score > 0.5 or insult_score > 0.5 or identity_hate_score > 0.5:
            return jsonify({"success": False, "message": "Post flagged as toxic or offensive"}), 400

    if 'image' in request.files:
        img = request.files['image']
        if img and img.filename:
            os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
            image_path = os.path.join(app.config['UPLOAD_FOLDER'], img.filename)
            img.save(image_path)

            nsfw_detected = detect_nsfw_image(image_path)

            board_normalized = board.strip().lower().strip('/')
            if board_normalized == "pol" and nsfw_detected:
                os.remove(image_path)
                return jsonify({"success": False, "message": "NSFW images are not allowed on /pol/"}), 400
            # Allow NSFW images only on /b/, block on other boards except /b/
            if nsfw_detected and board_normalized != "b":
                os.remove(image_path)
                return jsonify({"success": False, "message": "NSFW images are only allowed on /b/"}), 400
            if nsfw_detected:
                is_nsfw = True
            image = img.filename

    post = Post(user_id=user_id, board=board, content=content, image=image, is_approved=True, is_nsfw=is_nsfw)
    db.session.add(post)
    db.session.commit()

    return jsonify({"success": True})

@app.route("/posts/<board>", methods=["GET"])
def get_posts(board):
    posts = Post.query.filter_by(board=board, is_approved=True).all()
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
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

@app.route("/admin/login", methods=["POST"])
def admin_login():
    password = request.form.get("password")
    if password == os.getenv("ADMIN_PASSWORD", "Razor@2005"):
        session['admin_logged_in'] = True
        return jsonify({"success": True})
    return jsonify({"success": False}), 401

@app.route("/admin/logout", methods=["POST"])
def admin_logout():
    session.pop('admin_logged_in', None)
    return jsonify({"success": True})

@app.route("/admin/check", methods=["GET"])
def admin_check():
    return jsonify({"logged_in": session.get('admin_logged_in', False)})

@app.route("/admin/posts", methods=["GET"])
def admin_get_posts():
    if not session.get('admin_logged_in'):
        return jsonify({"error": "Unauthorized"}), 401

    posts = Post.query.all()
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
    if not session.get('admin_logged_in'):
        return jsonify({"error": "Unauthorized"}), 401

    post = Post.query.get(post_id)
    if post:
        post.is_approved = True
        db.session.commit()
        return jsonify({"success": True})
    return jsonify({"error": "Post not found"}), 404

@app.route("/admin/delete/<int:post_id>", methods=["DELETE"])
def delete_post(post_id):
    if not session.get('admin_logged_in'):
        return jsonify({"error": "Unauthorized"}), 401

    post = Post.query.get(post_id)
    if post:
        db.session.delete(post)
        db.session.commit()
        return jsonify({"success": True})
    return jsonify({"error": "Post not found"}), 404

@app.route("/clear_history", methods=["POST"])
def clear_history():
    try:
        Post.query.delete()
        db.session.commit()
        return jsonify({"success": True})
    except Exception as e:
        db.session.rollback()
        return jsonify({"success": False, "error": str(e)}), 500

@app.route("/create_board", methods=["POST"])
def create_board():
    board_name = request.json.get("board")
    nsfw_setting = request.json.get("nsfw")

    new_board = Board(name=board_name, nsfw=nsfw_setting)
    db.session.add(new_board)
    db.session.commit()

    return jsonify({"success": True, "message": "Board created successfully."})

import requests

@app.route("/gemini_chat", methods=["POST"])
def gemini_chat():
    try:
        data = request.get_json()
        user_msg = data.get("message", "")
        if not user_msg:
            return jsonify({"error": "No message provided."}), 400
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            return jsonify({"error": "Gemini API key not set on server."}), 500
        api_url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-pro:generateContent?key={api_key}"
        payload = {"contents": [{"parts": [{"text": user_msg}]}]}
        headers = {"Content-Type": "application/json"}
        resp = requests.post(api_url, json=payload, headers=headers, timeout=15)
        if resp.status_code != 200:
            return jsonify({"error": "Gemini API error."}), 502
        data = resp.json()
        bot_msg = "No response."
        try:
            bot_msg = data["candidates"][0]["content"]["parts"][0]["text"]
        except Exception:
            pass
        return jsonify({"message": bot_msg})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    app.run(debug=True)
