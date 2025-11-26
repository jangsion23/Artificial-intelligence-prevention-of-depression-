// =======================
// 공통: 화면 전환 로직
// =======================
const menuCards = document.querySelectorAll(".menu-card");
const mainMenu = document.getElementById("mainMenu");
const sections = document.querySelectorAll(".page-section");

menuCards.forEach((card) => {
  card.addEventListener("click", () => {
    const targetId = card.dataset.target;
    mainMenu.style.display = "none";
    sections.forEach((sec) => sec.classList.add("hidden"));
    document.getElementById(targetId).classList.remove("hidden");
  });
});

const backButtons = document.querySelectorAll("[data-back]");
backButtons.forEach((btn) => {
  btn.addEventListener("click", () => {
    sections.forEach((sec) => sec.classList.add("hidden"));
    mainMenu.style.display = "block";
  });
});

// =======================
// 1. 영상 녹화하기
// =======================
let recordStream = null;
let mediaRecorder = null;
let recordedChunks = [];

const recordVideoEl = document.getElementById("recordVideo");
const startRecordBtn = document.getElementById("startRecordBtn");
const stopRecordBtn = document.getElementById("stopRecordBtn");

// 녹화 시작
startRecordBtn.addEventListener("click", async () => {
  try {
    recordStream = await navigator.mediaDevices.getUserMedia({
      video: true,
      audio: true,
    });
    recordVideoEl.srcObject = recordStream;

    recordedChunks = [];
    mediaRecorder = new MediaRecorder(recordStream);

    mediaRecorder.ondataavailable = (e) => {
      if (e.data.size > 0) recordedChunks.push(e.data);
    };

    // 녹화 종료 시 자동 업로드
    mediaRecorder.onstop = async () => {
      try {
        if (recordedChunks.length === 0) {
          alert("녹화된 데이터가 없습니다.");
          return;
        }

        const blob = new Blob(recordedChunks, { type: "video/webm" });
        const formData = new FormData();
        formData.append("video", blob, "mymemory-record.webm");

        const res = await fetch("/api/videos", {
          method: "POST",
          body: formData,
        });

        if (!res.ok) throw new Error("업로드 실패");
        const data = await res.json();
        console.log("업로드 및 분석 결과:", data);
        alert("✅ 영상이 저장되고 감정 분석이 완료되었습니다!");
      } catch (err) {
        console.error(err);
        alert("영상 업로드 중 오류가 발생했습니다.");
      } finally {
        recordedChunks = [];
      }
    };

    mediaRecorder.start();
    alert("🎥 녹화를 시작했습니다. 다 찍으면 '녹화 종료'를 눌러주세요.");
  } catch (err) {
    console.error(err);
    alert("카메라/마이크 권한을 허용해주세요.");
  }
});

// 녹화 종료
stopRecordBtn.addEventListener("click", () => {
  if (!mediaRecorder || mediaRecorder.state !== "recording") {
    alert("먼저 녹화를 시작해주세요.");
    return;
  }

  mediaRecorder.stop(); // onstop에서 업로드
  if (recordStream) {
    recordStream.getTracks().forEach((t) => t.stop());
  }
  alert("⏹ 녹화를 종료했습니다. 영상을 저장하고 분석 중입니다.");
});

// =======================
// 2. 기록된 영상 보기 + 삭제 기능
// =======================
const refreshListBtn = document.getElementById("refreshListBtn");
const videoListEl = document.getElementById("videoList");

refreshListBtn.addEventListener("click", loadVideoList);

async function loadVideoList() {
  videoListEl.innerHTML = "불러오는 중...";

  try {
    const res = await fetch("/api/videos");
    if (!res.ok) throw new Error("목록 조회 실패");
    const videos = await res.json();

    if (!Array.isArray(videos) || videos.length === 0) {
      videoListEl.innerHTML = "<p>아직 저장된 영상이 없습니다.</p>";
      return;
    }

    videoListEl.innerHTML = "";

    videos.forEach((v, idx) => {
      const card = document.createElement("div");
      card.className = "video-card";

      // ===== 왼쪽: 편지 썸네일 + 숨겨진 video =====
      const leftBox = document.createElement("div");

      const thumb = document.createElement("div");
      thumb.className = "video-thumb";

      const thumbIcon = document.createElement("div");
      thumbIcon.className = "video-thumb-icon";
      thumbIcon.textContent = "💌";

      const thumbText = document.createElement("div");
      thumbText.className = "video-thumb-text";
      thumbText.textContent = `기록 영상 ${idx + 1}`;

      const thumbSub = document.createElement("div");
      thumbSub.className = "video-thumb-subtext";
      const date = new Date(v.created_at);
      thumbSub.textContent = date.toLocaleString("ko-KR");

      thumb.appendChild(thumbIcon);
      thumb.appendChild(thumbText);
      thumb.appendChild(thumbSub);

      const videoEl = document.createElement("video");
      videoEl.src = v.video_url;
      videoEl.controls = true;
      videoEl.className = "video-player hidden"; // 처음엔 숨김

      // 썸네일 클릭 시 영상 열고/닫기 토글
      thumb.addEventListener("click", () => {
        videoEl.classList.toggle("hidden");
      });

      leftBox.appendChild(thumb);
      leftBox.appendChild(videoEl);

      // ===== 오른쪽: 메타 정보 =====
      const metaDiv = document.createElement("div");
      metaDiv.className = "video-meta";

      const dateSpan = document.createElement("span");
      dateSpan.textContent = date.toLocaleString("ko-KR");

      const emotionBadge = document.createElement("span");
      emotionBadge.className = "main-emotion-badge";

      const counts = v.emotion_counts || {};
      let mainEmotion = "-";
      let maxCount = 0;
      Object.entries(counts).forEach(([emo, cnt]) => {
        if (cnt > maxCount) {
          maxCount = cnt;
          mainEmotion = emo;
        }
      });
      emotionBadge.textContent =
        mainEmotion !== "-" ? `주요 감정: ${mainEmotion}` : "주요 감정: -";

      const deleteBtn = document.createElement("button");
      deleteBtn.textContent = "삭제";
      deleteBtn.className = "delete-btn";
      deleteBtn.addEventListener("click", async () => {
        if (!confirm("정말 이 영상을 삭제할까요?")) return;

        try {
          const res = await fetch("/api/delete_video", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ filename: v.video_filename }),
          });

          const data = await res.json();
          if (!res.ok) {
            alert(
              "삭제 중 오류가 발생했습니다: " + (data.error || "알 수 없는 오류")
            );
            return;
          }

          alert("영상이 삭제되었습니다.");
          loadVideoList(); // 목록 새로고침
        } catch (err) {
          console.error(err);
          alert("삭제 요청 중 오류가 발생했습니다.");
        }
      });

      metaDiv.appendChild(dateSpan);
      metaDiv.appendChild(emotionBadge);
      metaDiv.appendChild(deleteBtn);

      card.appendChild(leftBox);
      card.appendChild(metaDiv);

      videoListEl.appendChild(card);
    });
  } catch (err) {
    console.error(err);
    videoListEl.innerHTML =
      "<p>목록을 불러오는 중 오류가 발생했습니다.</p>";
  }
}

// =======================
// 3. 종합 감정 요약
// =======================
const getSummaryBtn = document.getElementById("getSummaryBtn");
const summaryMessage = document.getElementById("summaryMessage");

getSummaryBtn.addEventListener("click", async () => {
  summaryMessage.textContent = "분석 중입니다...";

  try {
    const res = await fetch("/api/emotion-summary");
    if (!res.ok) throw new Error("요약 조회 실패");

    const data = await res.json();
    // emotions는 백엔드에서만 사용 (프론트에서는 표시 안 함)
    // const emotions = data.emotions || {};
    // console.log("emotions:", emotions);

    summaryMessage.textContent =
      data.message || "요약 멘트가 아직 없습니다.";
  } catch (err) {
    console.error(err);
    summaryMessage.textContent =
      "요약을 불러오는 중 오류가 발생했습니다. 나중에 다시 시도해 주세요.";
  }
});
