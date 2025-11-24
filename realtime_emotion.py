import cv2
from transformers import pipeline
from PIL import Image
import torch

# 1. 모델 로드 (GPU가 있으면 사용)
print("Hugging Face 감정 분석 모델을 로드합니다...")
device = 0 if torch.cuda.is_available() else -1
classifier = pipeline(
    task="image-classification",
    model="dima806/facial_emotions_image_detection",
    device=device
)
print("✅ 모델 로딩 완료!")

# 2. OpenCV 얼굴 탐지기 로드 (Haar Cascade)
# OpenCV 라이브러리 내부에 포함된 기본 정면 얼굴 탐지 XML 파일 사용
face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')

# 3. 웹캠 켜기 (0번 카메라)
cap = cv2.VideoCapture(0)

if not cap.isOpened():
    print("오류: 웹캠을 열 수 없습니다.")
    exit()

print("웹캠이 켜졌습니다. 'q' 키를 누르면 종료됩니다.")

while True:
    # 4. 웹캠에서 프레임(이미지) 읽기
    ret, frame = cap.read()
    if not ret:
        print("오류: 프레임을 읽을 수 없습니다.")
        break

    # 5. 얼굴 탐지를 위해 흑백 이미지로 변환
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    
    # 6. 흑백 이미지에서 얼굴 탐지
    faces = face_cascade.detectMultiScale(
        gray, 
        scaleFactor=1.1,  # 이미지 축소 비율
        minNeighbors=5,   # 얼굴로 간주하기 위한 최소 인접 사각형 수
        minSize=(50, 50)  # 최소 얼굴 크기
    )

    # 7. 탐지된 얼굴마다 감정 분석 실행
    for (x, y, w, h) in faces:
        # 원본 컬러 프레임에서 얼굴 영역(ROI: Region of Interest) 자르기
        face_roi_color = frame[y:y+h, x:x+w]

        try:
            # OpenCV 이미(BGR) -> PIL 이미지(RGB) 변환
            pil_image = Image.fromarray(cv2.cvtColor(face_roi_color, cv2.COLOR_BGR2RGB))
            
            # 8. Hugging Face 모델로 감정 분석
            results = classifier(pil_image)
            
            # 9. 가장 확률 높은 감정 가져오기
            top_result = results[0]
            emotion = top_result['label'].capitalize()
            score = top_result['score']
            
            # 10. 화면에 표시할 텍스트 준비
            text = f"{emotion} ({score*100:.1f}%)"
            
            # 11. 얼굴 주변에 사각형 그리기 (파란색)
            cv2.rectangle(frame, (x, y), (x+w, y+h), (255, 0, 0), 2)
            
            # 12. 얼굴 위에 감정 텍스트 쓰기
            cv2.putText(frame, text, (x, y - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 0, 0), 2)

        except Exception as e:
            # 얼굴이 너무 작거나 프레임 밖으로 나갈 때 오류 방지
            print(f"분석 오류: {e}")
            pass

    # 13. 결과 프레임을 "Real-time Emotion Recognition" 창에 표시
    cv2.imshow('Real-time Emotion Recognition (Press ''q'' to quit)', frame)

    # 14. 'q' 키를 누르면 루프 종료
    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

# 15. 종료 시 자원 해제
print("프로그램을 종료합니다.")
cap.release()
cv2.destroyAllWindows()