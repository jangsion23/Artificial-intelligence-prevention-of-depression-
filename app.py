import os
import json
import datetime

from flask import Flask, request, jsonify, render_template, send_from_directory
import cv2
from PIL import Image
import torch
from transformers import pipeline

# ===============================
# 기본 설정
# ===============================
BASE_DIR = os.path.dirname(os.path.realpath(__file__))
VIDEOS_DIR = os.path.join(BASE_DIR, "videos")
os.makedirs(VIDEOS_DIR, exist_ok=True)

app = Flask(__name__, template_folder="templates")  # static은 기본 'static' 사용


# ===============================
# 얼굴 감정 인식 모델 (HF: dima806/facial_emotions_image_detection)
# ===============================
print("Hugging Face 얼굴 감정 분석 모델을 로드합니다...")
device = 0 if torch.cuda.is_available() else -1

classifier = pipeline(
    task="image-classification",
    model="dima806/facial_emotions_image_detection",
    device=device
)
print("✅ 얼굴 감정 모델 로딩 완료! (device:", "cuda" if device == 0 else "cpu", ")")

# OpenCV 얼굴 검출기 (Haar Cascade)
face_cascade = cv2.CascadeClassifier(
    cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
)

# ===============================
# 감정 라벨 매핑 (7개 감정)
# ===============================
EMOTION_LABEL_MAP = {
    "angry": "분노",
    "disgust": "혐오",
    "fear": "공포",
    "happy": "행복",
    "sad": "슬픔",
    "surprise": "놀람",
    "neutral": "중립",
}

ALL_EMOTIONS_KO = list(EMOTION_LABEL_MAP.values())


def normalize_emotion_label(raw_label: str) -> str:
    """영어 감정 → 한국어 감정 라벨 변환"""
    raw_label = str(raw_label).strip()
    if raw_label in ALL_EMOTIONS_KO:
        return raw_label

    key = raw_label.lower()
    return EMOTION_LABEL_MAP.get(key, raw_label)


# ===============================
# 유틸: 영상 하나 감정 분석 (프레임 단위)
# ===============================
def analyze_video_emotions(video_path: str, frame_step: int = 5):
    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        print(f"[WARN] 비디오를 열 수 없습니다: {video_path}")
        return {
            "frames_analyzed": 0,
            "faces_analyzed": 0,
            "emotion_counts": {},
            "emotion_ratios": {},
            "timeline": []
        }

    # ✅ 여기 버그 수정: cap을 덮어쓰지 말고 fps만 가져오기
    fps = cap.get(cv2.CAP_PROP_FPS)
    if fps <= 0:
        fps = 30.0

    frame_idx = 0
    total_faces = 0
    emotion_counts = {}
    timeline = []

    while True:
        ret, frame = cap.read()
        if not ret:
            break

        # frame_step 간격으로만 분석
        if frame_idx % frame_step != 0:
            frame_idx += 1
            continue

        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        faces = face_cascade.detectMultiScale(
            gray,
            scaleFactor=1.1,
            minNeighbors=5,
            minSize=(50, 50)
        )

        frame_emotion_counts = {}

        for (x, y, w, h) in faces:
            face_roi_color = frame[y:y + h, x:x + w]

            try:
                pil_image = Image.fromarray(
                    cv2.cvtColor(face_roi_color, cv2.COLOR_BGR2RGB)
                )
                results = classifier(pil_image)
                top_result = results[0]

                raw_label = top_result["label"]
                label_ko = normalize_emotion_label(raw_label)

                # 전체 카운트
                emotion_counts[label_ko] = emotion_counts.get(label_ko, 0) + 1
                total_faces += 1

                # 프레임 내 카운트
                frame_emotion_counts[label_ko] = frame_emotion_counts.get(label_ko, 0) + 1

            except Exception as e:
                print("[WARN] 얼굴 감정 분석 중 오류:", e)
                continue

        # 이 프레임에서 대표 감정 하나 기록
        if frame_emotion_counts:
            main_emo = max(frame_emotion_counts.items(), key=lambda x: x[1])[0]
            time_sec = frame_idx / fps
            timeline.append({
                "time": round(float(time_sec), 3),
                "emotion": main_emo
            })

        frame_idx += 1

    cap.release()

    # 감정 비율 계산
    emotion_ratios = {}
    if total_faces > 0:
        for k, v in emotion_counts.items():
            emotion_ratios[k] = v / total_faces

    # 7개 감정 모두 key 포함
    for emo in ALL_EMOTIONS_KO:
        emotion_ratios.setdefault(emo, 0.0)

    return {
        "frames_analyzed": frame_idx,
        "faces_analyzed": total_faces,
        "emotion_counts": emotion_counts,
        "emotion_ratios": emotion_ratios,
        "timeline": timeline
    }


# ===============================
# index.html
# ===============================
@app.route("/", methods=["GET"])
def index():
    current_year = datetime.datetime.utcnow().year
    return render_template("index.html", year=current_year)


# ===============================
# 영상 파일 서빙
# ===============================
@app.route("/videos/<path:filename>")
def serve_video(filename):
    return send_from_directory(VIDEOS_DIR, filename)


# ===============================
# 영상 업로드 + 분석
# ===============================
@app.route("/api/videos", methods=["GET", "POST"])
def api_videos():
    if request.method == "POST":
        if "video" not in request.files:
            return jsonify({"error": "No file part 'video' in the request"}), 400

        file = request.files["video"]
        if file.filename == "":
            return jsonify({"error": "No selected file"}), 400

        ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        video_filename = f"video_{ts}.webm"
        video_path = os.path.join(VIDEOS_DIR, video_filename)

        # 저장
        file.save(video_path)
        print(f"[INFO] 영상 저장 완료: {video_path}")

        # 감정 분석
        try:
            analysis = analyze_video_emotions(video_path, frame_step=5)
        except Exception as e:
            print("[ERROR] 분석 중 예외 발생:", e)
            # 분석 실패해도 업로드는 성공처리하고, 분석 결과는 비워서 돌려줄 수도 있음
            analysis = {
                "frames_analyzed": 0,
                "faces_analyzed": 0,
                "emotion_counts": {},
                "emotion_ratios": {},
                "timeline": []
            }

        emotion_counts = analysis["emotion_counts"]
        dominant_emotion = None
        if emotion_counts:
            dominant_emotion = max(emotion_counts.items(), key=lambda x: x[1])[0]

        meta = {
            "video_filename": video_filename,
            "video_path": os.path.relpath(video_path, BASE_DIR),
            "created_at": datetime.datetime.now().isoformat(),
            "frames_analyzed": analysis["frames_analyzed"],
            "faces_analyzed": analysis["faces_analyzed"],
            "emotion_counts": emotion_counts,
            "emotion_ratios": analysis["emotion_ratios"],
            "timeline": analysis["timeline"],
            "dominant_emotion": dominant_emotion
        }

        meta_filename = os.path.splitext(video_filename)[0] + ".json"
        meta_path = os.path.join(VIDEOS_DIR, meta_filename)
        with open(meta_path, "w", encoding="utf-8") as f:
            json.dump(meta, f, ensure_ascii=False, indent=2)

        print(f"[INFO] 메타데이터 저장 완료: {meta_path}")

        return jsonify({
            "status": "ok",
            "video_filename": video_filename,
            "video_url": f"/videos/{video_filename}",
            "analysis": analysis
        })

    else:
        # GET: 목록 조회
        metas = []
        for fname in os.listdir(VIDEOS_DIR):
            if not fname.endswith(".json"):
                continue
            meta_path = os.path.join(VIDEOS_DIR, fname)
            try:
                with open(meta_path, "r", encoding="utf-8") as f:
                    meta = json.load(f)
            except:
                continue

            video_filename = meta.get("video_filename")
            meta["video_url"] = f"/videos/{video_filename}"

            # emotion_counts 라벨 정리
            fixed_counts = {}
            for emo, cnt in (meta.get("emotion_counts") or {}).items():
                ko = normalize_emotion_label(emo)
                fixed_counts[ko] = fixed_counts.get(ko, 0) + cnt
            meta["emotion_counts"] = fixed_counts

            # 대표 감정 누락 시 재계산
            if "dominant_emotion" not in meta or not meta["dominant_emotion"]:
                counts = meta.get("emotion_counts", {})
                if counts:
                    meta["dominant_emotion"] = max(counts.items(), key=lambda x: x[1])[0]
                else:
                    meta["dominant_emotion"] = None

            meta.setdefault("timeline", [])
            metas.append(meta)

        metas.sort(key=lambda m: m.get("created_at", ""), reverse=True)
        return jsonify(metas)


# ===============================
# 영상 삭제
# ===============================
@app.route("/api/delete_video", methods=["POST"])
def delete_video():
    data = request.get_json(silent=True) or {}
    filename = data.get("filename")

    if not filename:
        return jsonify({"error": "filename is required"}), 400

    video_path = os.path.join(VIDEOS_DIR, filename)
    meta_filename = os.path.splitext(filename)[0] + ".json"
    meta_path = os.path.join(VIDEOS_DIR, meta_filename)

    deleted_video = False
    deleted_meta = False

    if os.path.exists(video_path):
        try:
            os.remove(video_path)
            deleted_video = True
            print("[INFO] 영상 파일 삭제:", video_path)
        except Exception as e:
            print("[WARN] 영상 파일 삭제 실패:", e)

    if os.path.exists(meta_path):
        try:
            os.remove(meta_path)
            deleted_meta = True
            print("[INFO] 메타 파일 삭제:", meta_path)
        except Exception as e:
            print("[WARN] 메타 파일 삭제 실패:", e)

    if not deleted_video and not deleted_meta:
        return jsonify({"error": "file not found"}), 404

    return jsonify({
        "status": "ok",
        "deleted_video": deleted_video,
        "deleted_meta": deleted_meta
    })


# ===============================
# 전체 영상 기반 종합 감정 요약
# ===============================
@app.route("/api/emotion-summary", methods=["GET"])
def emotion_summary():
    import random

    total_counts = {}
    total_faces = 0

    for fname in os.listdir(VIDEOS_DIR):
        if not fname.endswith(".json"):
            continue
        meta_path = os.path.join(VIDEOS_DIR, fname)
        try:
            with open(meta_path, "r", encoding="utf-8") as f:
                meta = json.load(f)
        except:
            continue

        counts = meta.get("emotion_counts", {})
        for emo, cnt in counts.items():
            ko = normalize_emotion_label(emo)
            total_counts[ko] = total_counts.get(ko, 0) + cnt
            total_faces += cnt

    if total_faces == 0:
        empty_ratios = {emo: 0.0 for emo in ALL_EMOTIONS_KO}
        return jsonify({
            "emotions": empty_ratios,
            "message": "아직 분석된 얼굴 데이터가 충분하지 않아요. 먼저 몇 개의 영상을 기록해 주세요."
        })

    emotion_ratios = {emo: cnt / total_faces for emo, cnt in total_counts.items()}
    for emo in ALL_EMOTIONS_KO:
        emotion_ratios.setdefault(emo, 0.0)

    main_emotion = max(total_counts.items(), key=lambda x: x[1])[0]

    # 감정별 랜덤 멘트
    emotion_messages = {
        "행복": [
            "최근 영상들에서는 행복한 표정이 많이 보였어요. 요즘 좋은 일이 많은가 봐요 🙂",
            "밝게 웃는 모습이 자주 포착됐어요. 당신의 에너지가 화면 밖까지 전해져요.",
            "행복한 감정이 많이 느껴졌어요. 이 기분이 오래오래 이어지면 좋겠어요."
        ],
        "슬픔": [
            "슬픔이 자주 감지되고 있어요. 혼자 버티지 말고, 잠깐 쉬어가도 괜찮아요.",
            "조금 지친 표정들이 보였어요. 오늘 하루, 나를 위해 아주 작은 휴식을 선물해 보는 건 어때요?",
            "마음이 무거웠던 순간들이 있었던 것 같아요. 그런 날에도 여기까지 온 자신을 칭찬해 주세요."
        ],
        "분노": [
            "요즘 많이 예민하고 화나는 일이 있었던 것 같아요. 나를 힘들게 했던 상황들을 잘 정리해 보는 건 어떨까요?",
            "분노의 흔적이 조금 보였어요. 때로는 화나는 감정을 솔직하게 인정하는 것도 괜찮아요.",
            "답답하고 억울한 마음이 있었던 것 같아요. 너무 오래 혼자 끌어안고 있지는 않았으면 해요."
        ],
        "놀람": [
            "놀라는 표정이 자주 포착됐어요. 변화가 많은 시기일 수도 있겠네요.",
            "예상치 못한 순간들이 많았던 것 같아요. 그래도 여기까지 잘 따라와 준 나 자신이 대단해요.",
            "조금 당황스러운 상황들이 있었던 것 같아요. 하지만 그 순간에도 잘 버티고 넘어온 모습이 보여요."
        ],
        "공포": [
            "불안하거나 두려운 감정이 감지되고 있어요. 편하게 털어놓을 수 있는 사람과 이야기를 나눠보는 건 어때요?",
            "걱정과 긴장이 느껴지는 표정이 보였어요. 너무 완벽하려 하지 않아도 괜찮아요.",
            "불안한 마음이 이어졌던 것 같아요. 오늘은 나를 조금 더 따뜻하게 대해주면 좋겠어요."
        ],
        "혐오": [
            "싫다고 느껴지는 것들이 많았던 것 같아요. 나에게 맞지 않는 것들로부터 거리를 두는 것도 중요해요.",
            "마음에 들지 않는 상황이 자주 있었던 것 같아요. 그 속에서도 나를 지키려 한 당신이 고마워요.",
            "꺼려지는 감정이 조금 보였어요. 나에게 독이 되는 것들에서 한 걸음 멀어져도 괜찮아요."
        ],
        "중립": [
            "표정이 전반적으로 차분하고 안정적으로 나타나고 있어요. 잔잔한 하루들이 이어지고 있는지도 모르겠네요.",
            "큰 기복 없이 담담한 표정이 많이 보였어요. 조용히 흐르는 일상 속에서도 나만의 속도를 지키고 있어요.",
            "감정의 파도가 크지 않았던 것 같아요. 천천히, 나답게 걸어가는 시간이 되고 있는 듯해요."
        ]
    }

    candidates = emotion_messages.get(main_emotion, [
        "오늘도 여기까지 잘 오셨어요. 어떤 감정이든, 있는 그대로의 나를 인정해 주세요."
    ])
    message = random.choice(candidates)

    return jsonify({
        "emotions": emotion_ratios,  # 프론트에서는 안 쓰지만 백엔드용으로 유지
        "message": message
    })


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=8080, debug=True)
