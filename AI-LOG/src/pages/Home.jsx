import React, { useState, useRef, useEffect } from 'react';

// (임시) 데이터에 '요약본', '결과', '대응법' 항목을 추가합니다.
const DUMMY_VIDEO_LIST = [
  { 
    id: 1, 
    date: '2025년 11월 15일', 
    duration: '0:45', 
    thumbnail: '/path/to/thumb1.jpg',
    summary: '아이와 눈을 맞추며 "사랑해"라고 말하는 등 긍정적인 상호작용이 돋보였습니다.',
    aiResult: '목소리 톤이 안정적이며, 텍스트에서 "행복", "사랑" 등 긍정 키워드가 85% 감지되었습니다. 우울 징후는 보이지 않습니다.',
    strategy: '아주 좋습니다! 지금처럼 아이에게 긍정적인 표현을 자주 해주세요.'
  },
  { 
    id: 2, 
    date: '2025년 11월 10일', 
    duration: '1:20', 
    thumbnail: '/path/to/thumb2.jpg',
    summary: '아이가 장난감을 가지고 노는 모습을 지켜보며 간간히 대화를 나누었습니다.',
    aiResult: '목소리 톤이 다소 낮고, "힘들다", "지친다" 등의 단어가 3회 감지되었습니다. (주의 단계)',
    strategy: '육아에 지친 기색이 보입니다. 오늘은 10분 정도 혼자만의 시간을 가지며 따뜻한 차를 마셔보는 것은 어떨까요?'
  },
  { 
    id: 3, 
    date: '2025년 11월 1일', 
    duration: '0:30', 
    thumbnail: '/path/to/thumb3.jpg',
    summary: '아이에게 간단한 일상을 이야기했습니다.',
    aiResult: '감정 분석 결과 "평온" 상태(90%)입니다. 특이사항 없습니다.',
    strategy: '안정적인 상태입니다. 잘하고 계십니다.'
  },
];

function Home() {
  const [isCamOn, setIsCamOn] = useState(false);
  const [isListVisible, setIsListVisible] = useState(false);
  
  // ▼▼▼ 1. 새로운 상태 추가 ▼▼▼
  // 사용자가 분석을 위해 선택한 비디오 객체를 저장합니다.
  // null이면 '분석 상세' 뷰가 보이지 않습니다.
  const [selectedVideo, setSelectedVideo] = useState(null); 
  
  const videoRef = useRef(null);
  const streamRef = useRef(null);

  // ... (useEffect - 웹캠 켜고 끄는 로직은 변경 없음) ...
  useEffect(() => {
    if (isCamOn) {
      navigator.mediaDevices.getUserMedia({ video: true, audio: true })
        .then(stream => {
          if (videoRef.current) {
            videoRef.current.srcObject = stream;
            videoRef.current.play();
          }
          streamRef.current = stream;
        })
        .catch(err => {
          console.error("웹캠 오류:", err);
          alert("웹캠을 켤 수 없습니다. 브라우저 권한을 확인해주세요.");
          setIsCamOn(false);
        });
    } else {
      if (streamRef.current) {
        streamRef.current.getTracks().forEach(track => track.stop());
        streamRef.current = null;
      }
    }
    return () => {
      if (streamRef.current) {
        streamRef.current.getTracks().forEach(track => track.stop());
      }
    };
  }, [isCamOn]);


  // ... (핸들러 함수들 수정 및 추가) ...

  const handleShowList = () => {
    setIsListVisible(true);
    setSelectedVideo(null); // 혹시 모르니 상세 뷰는 끔
  };

  const handleWebcamStart = () => {
    setIsCamOn(true);
  };

  const handleWebcamStop = () => {
    setIsCamOn(false);
  };

  // '뒤로가기' (목록 -> 메인)
  const handleGoBackToMain = () => {
    setIsListVisible(false);
  };

  // ▼▼▼ 2. 'AI 분석' 버튼 클릭 핸들러 (신규) ▼▼▼
  const handleShowAnalysis = (video) => {
    console.log(`AI 분석 클릭: ${video.id}`);
    setSelectedVideo(video); // 뷰를 바꾸기 위해 선택된 비디오를 state에 저장
    setIsListVisible(false); // 목록 뷰는 숨김
  };

  // ▼▼▼ 3. '목록으로' 버튼 핸들러 (신규) ▼▼▼
  // (분석 상세 뷰 -> 목록 뷰)
  const handleBackToList = () => {
    setSelectedVideo(null); // 선택된 비디오를 비움
    setIsListVisible(true); // 목록 뷰를 다시 켬
  };

  return (
    <div className="home-container">
      {/* ... (좌측 사이드바 변경 없음) ... */}
      <div className="left-sidebar">
        <img src="/smile.png" alt="스마일 이모티콘" className="sidebar-icon" />
      </div>

      {/* ▼▼▼ 4. 중앙 컨텐츠 렌더링 로직 (4단계로 변경) ▼▼▼ */}
      <main className="home-main-content">
        {
          selectedVideo ? (
            /* --------------------------------- */
            /* (A) AI 분석 상세 화면 (NEW)       */
            /* --------------------------------- */
            <div className="analysis-view">
              <button onClick={handleBackToList} className="back-button">
                ← 목록으로
              </button>
              <h3>AI 분석 결과</h3>

              {/* 1. 크게 영상 나오기 (임시 플레이스홀더) */}
              <div className="video-player-wrapper">
                {/* <video src={selectedVideo.videoUrl} controls autoPlay /> */}
                <div className="video-placeholder">영상 재생 영역</div>
              </div>
              
              {/* 2. 요약본 */}
              <div className="analysis-section">
                <h4>영상 요약본</h4>
                <p>{selectedVideo.summary}</p>
              </div>
              
              {/* 3. AI 검증 결과 */}
              <div className="analysis-section">
                <h4>AI 검증 결과 (감정 분석)</h4>
                <p>{selectedVideo.aiResult}</p>
              </div>
              
              {/* 4. 대응법 */}
              <div className="analysis-section">
                <h4>멘탈 케어 대응법</h4>
                <p>{selectedVideo.strategy}</p>
              </div>
            </div>

          ) : isListVisible ? (
            /* --------------------------------- */
            /* (B) 영상 목록 화면                */
            /* --------------------------------- */
            <div className="video-list-view">
              <button onClick={handleGoBackToMain} className="back-button">
                ← 뒤로가기
              </button>
              <h3>영상 편지 목록</h3>
              <ul className="video-list">
                {DUMMY_VIDEO_LIST.map(video => (
                  <li key={video.id} className="video-list-item">
                    {/* ... (썸네일, 인포) ... */}
                    <div className="video-thumbnail">
                      <span>썸네일</span>
                    </div>
                    <div className="video-info">
                      <p className="video-date">{video.date}</p>
                      <p className="video-duration">길이: {video.duration}</p>
                    </div>
                    
                    {/* 버튼 래퍼 */}
                    <div className="video-item-buttons">
                      <button className="play-button">재생 ▶</button>
                      <button 
                        className="ai-button" 
                        // ▼▼▼ 5. 'AI 분석' 버튼에 새 핸들러 연결 ▼▼▼
                        onClick={() => handleShowAnalysis(video)}
                      >
                        AI 분석
                      </button>
                    </div>
                  </li>
                ))}
              </ul>
            </div>

          ) : isCamOn ? (
            /* --------------------------------- */
            /* (C) 웹캠 녹화 화면                */
            /* --------------------------------- */
            <div className="webcam-view">
              <h3>아이에게 영상 편지를 남겨주세요...</h3>
              <video 
                ref={videoRef} 
                autoPlay 
                playsInline 
                muted
              />
              <button 
                className="stop-button" 
                onClick={handleWebcamStop}
              >
                중지하기
              </button>
            </div>

          ) : (
            /* --------------------------------- */
            /* (D) 메인 화면 (기본)              */
            /* --------------------------------- */
            <> 
              <header className="home-header">
                <h1 className="logo-text">AI-LOG</h1>
              </header>
              <section 
                className="central-message-section" 
                onClick={handleShowList}
                role="button"
                tabIndex="0"
              >
                <div className="speech-bubble">
                  <p>아이에게 보여주는</p>
                  <p>영상 편지</p>
                </div>
              </section>
              <section className="microphone-section">
                <div 
                  className="microphone-icon-wrapper" 
                  onClick={handleWebcamStart}
                  role="button"
                  tabIndex="0"
                >
                  <img 
                    src="/video.png" 
                    alt="비디오 아이콘" 
                    className="microphone-icon" 
                  />
                </div>
              </section>
            </>
          )
        }
      </main>

      {/* ... (우측 사이드바 변경 없음) ... */}
      <div className="right-sidebar">
        <img src="/family.png" alt="가족 사진 액자" className="sidebar-icon" />
      </div>
    </div>
  );
}

export default Home;