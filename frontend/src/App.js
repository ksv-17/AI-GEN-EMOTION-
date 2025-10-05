import React, { useRef, useState, useEffect } from "react";

const EmotionToImage = () => {
  const videoRef = useRef(null);
  const [emotion, setEmotion] = useState("");
  const [age, setAge] = useState("");
  const [gender, setGender] = useState("");
  const [boxedImage, setBoxedImage] = useState("");
  const [aiImage, setAiImage] = useState("");
  const [loading, setLoading] = useState(false);

  // Start webcam
  useEffect(() => {
    navigator.mediaDevices.getUserMedia({ video: true })
      .then(stream => {
        if (videoRef.current) videoRef.current.srcObject = stream;
      })
      .catch(err => console.error("⚠️ Camera error:", err));
  }, []);

  // Function to speak text
  const speak = (text) => {
    if ('speechSynthesis' in window) {
      const utterance = new SpeechSynthesisUtterance(text);
      window.speechSynthesis.speak(utterance);
    }
  };

  const handleCapture = async () => {
    if (!videoRef.current) return;
    const video = videoRef.current;

    if (!video.videoWidth || !video.videoHeight) {
      alert("⚠️ Camera not ready yet!");
      return;
    }

    setLoading(true);
    setEmotion("");
    setAge("");
    setGender("");
    setBoxedImage("");
    setAiImage("");

    speak("Detecting emotion, age, gender and generating image");

    const canvas = document.createElement("canvas");
    canvas.width = video.videoWidth;
    canvas.height = video.videoHeight;
    const ctx = canvas.getContext("2d");
    ctx.drawImage(video, 0, 0);

    canvas.toBlob(async (blob) => {
      const formData = new FormData();
      formData.append("image", blob, "frame.jpg");

      try {
        const res = await fetch(`${import.meta.env.VITE_API_URL}/detect_emotion`, {
          method: "POST",
          body: formData,
        });

        const data = await res.json();
        console.log("✅ Response data:", data);

        if (data.error) {
          setEmotion("⚠️ " + data.error);
          speak("Failed to detect emotion or generate image");
        } else {
          setEmotion(data.emotion);
          setAge(data.age);
          if (data.gender) {
            const genderKey = Object.keys(data.gender).reduce((a, b) =>
              data.gender[a] > data.gender[b] ? a : b
            );
            setGender(genderKey);
          }
          setBoxedImage(data.boxed_image);
          setAiImage(data.ai_image);
          speak(`Detected emotion is ${data.emotion}, age ${data.age}, gender ${data.gender}`);
        }
      } catch (err) {
        console.error("⚠️ Fetch error:", err);
        setEmotion("❌ Failed to connect to server!");
        speak("Failed to connect to server");
      } finally {
        setLoading(false);
      }
    }, "image/jpeg");
  };

  return (
    <div style={{ textAlign: "center", marginTop: "30px", fontFamily: "Arial, sans-serif" }}>
      <h2>🎭 Real-Time Emotion, Age & Gender Detection + AI Image Generator</h2>
      <video
        ref={videoRef}
        autoPlay
        playsInline
        width="320"
        height="240"
        style={{ border: "2px solid #444", borderRadius: "8px", background: "#000" }}
      />
      <br />
      <button
        onClick={handleCapture}
        style={{
          padding: "10px 20px",
          fontSize: "16px",
          marginTop: "20px",
          cursor: "pointer",
          border: "none",
          borderRadius: "5px",
          background: "#007bff",
          color: "white",
        }}
      >
        📸 Capture & Generate Image
      </button>

      <h3 style={{ marginTop: "20px", color: "#222" }}>
        {loading ? "⏳ Detecting and generating..." : `Emotion: ${emotion} | Age: ${age} | Gender: ${gender}`}
      </h3>

      <div style={{ display: "flex", justifyContent: "center", gap: "20px", marginTop: "20px" }}>
        {boxedImage && (
          <div>
            <h4>Original Image with Face Box</h4>
            <img src={boxedImage} alt="Boxed" width="320" height="240" style={{ borderRadius: "8px", border: "2px solid #444" }} />
          </div>
        )}
        {aiImage && (
          <div>
            <h4>AI Generated / Fallback Image</h4>
            <img src={aiImage} alt="AI" width="320" height="240" style={{ borderRadius: "8px", border: "2px solid #444" }} />
          </div>
        )}
      </div>
    </div>
  );
};

export default EmotionToImage;
