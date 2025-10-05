import os
from flask import Flask, request, jsonify
from flask_cors import CORS
import os
os.environ["TF_CPP_MIN_LOG_LEVEL"] = "3"  # Suppress TensorFlow logs
os.environ["TF_ENABLE_ONEDNN_OPTS"] = "0"  # Reduce memory footprint
from deepface import DeepFace
from huggingface_hub import InferenceClient
from io import BytesIO
import base64
from PIL import Image
import cv2
from dotenv import load_dotenv
load_dotenv()

app = Flask(__name__)
# ✅ Allow requests only from your frontend
CORS(app, resources={r"/*": {"origins": [
    os.getenv("LOCAL_FRONTEND_URL"),     # for CRA
    os.getenv("PRODUCTION_FRONTEND_URL")  # production domain (optional)
]}})


# ✅ HuggingFace Inference Client
client = InferenceClient(
    provider="fal-ai",
    api_key=os.getenv("HF_TOKEN")  # may expire
)

# Emotion → Prompt mapping for AI image
PROMPT_MAP = {
    "happy": "A close-up portrait of a smiling person, natural lighting, ultra realistic",
    "sad": "A portrait of a person with teary eyes looking down, cinematic lighting, realistic",
    "angry": "A portrait of a person with an angry expression, furrowed brows, dramatic lighting, ultra realistic",
    "surprise": "A portrait of a person with wide open eyes and mouth in shock, expressive, photorealistic",
    "fear": "A portrait of a scared person looking anxious, tense face, dim lighting, ultra realistic",
    "neutral": "A portrait of a calm person with a neutral expression, natural light, photorealistic",
    "disgust": "A portrait of a person showing disgust, wrinkled nose and mouth, realistic photography"
}

# Fallback image URLs
URL_IMAGE_MAP = {
    "happy": "https://images.unsplash.com/photo-1542596594-649edbc13630?w=700&auto=format&fit=crop&q=60",
    "sad": "https://images.unsplash.com/photo-1495558685573-aba7573d9c01?w=700&auto=format&fit=crop&q=60",
    "angry": "https://images.unsplash.com/photo-1620110488106-dad904f50930?w=700&auto=format&fit=crop&q=60",
    "surprise": "https://images.unsplash.com/photo-1758523672207-bc370d350fd9?w=700&auto=format&fit=crop&q=60",
    "fear": "https://images.unsplash.com/photo-1604697964284-ffb6d6aa8d62?w=700&auto=format&fit=crop&q=60",
    "neutral": "https://images.unsplash.com/photo-1604955620083-115f4ffe676c?w=700&auto=format&fit=crop&q=60",
    "disgust": "https://media.istockphoto.com/id/924923754/photo/young-man-with-disgusted-expression-repulsing-something-isolated-on-the-pastel.webp"
}

@app.route("/detect_emotion", methods=["POST"])
def detect_emotion():
    try:
        # Save uploaded image
        file = request.files["image"]
        img_path = "temp.jpg"
        file.save(img_path)

        # Read image with OpenCV
        img = cv2.imread(img_path)
        rgb_img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)

        # Detect emotion, age, gender using DeepFace
        analysis = DeepFace.analyze(
            img_path=img_path,
            actions=['emotion', 'age', 'gender'],
            enforce_detection=False
        )

        result = analysis[0]
        dominant_emotion = result['dominant_emotion']
        age = result['age']
        gender = result['gender']
        face_region = result.get('region', None)

        # Draw bounding box with gender & age
        if face_region:
            x, y, w, h = face_region['x'], face_region['y'], face_region['w'], face_region['h']
            cv2.rectangle(rgb_img, (x, y), (x+w, y+h), (0, 255, 0), 2)
            cv2.putText(rgb_img, f"{gender}, {age}", (x, y-10),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 0), 2)

        # Convert annotated image to base64
        pil_img = Image.fromarray(rgb_img)
        buffered_box = BytesIO()
        pil_img.save(buffered_box, format="PNG")
        boxed_image = f"data:image/png;base64,{base64.b64encode(buffered_box.getvalue()).decode('utf-8')}"

        # Generate AI image
        prompt = PROMPT_MAP.get(dominant_emotion, "A peaceful landscape, realistic")
        try:
            ai_image = client.text_to_image(prompt, model="tencent/HunyuanImage-3.0")
            buffered_ai = BytesIO()
            ai_image.save(buffered_ai, format="PNG")
            final_image = f"data:image/png;base64,{base64.b64encode(buffered_ai.getvalue()).decode('utf-8')}"
        except Exception as api_err:
            print("⚠️ HuggingFace API failed, using fallback URL:", api_err)
            final_image = URL_IMAGE_MAP.get(dominant_emotion, URL_IMAGE_MAP["neutral"])

        return jsonify({
            "emotion": dominant_emotion,
            "age": age,
            "gender": gender,
            "prompt": prompt,
            "boxed_image": boxed_image,  # Original image with bounding box
            "ai_image": final_image       # AI-generated image or fallback
        })

    except Exception as e:
        return jsonify({"error": str(e)}), 500


if __name__ == "__main__":
    print("🚀 Flask server running on http://127.0.0.1:5000")
    app.run(host="0.0.0.0", port=5000, debug=True)
