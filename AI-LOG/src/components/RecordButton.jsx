import React from 'react';
import RecordButton from '../components/RecordButton.jsx';
// <== import './Home.css'; 줄은 삭제했습니다. (App.css에서 관리)

function Home() {
  
  const todayFeedback = {
    mood: "happy",
    message: "오늘 목소리에 햇살이 가득해요! 아이도 행복했을 거예요."
  };

  return (
    <div className="home-container">
      <main className="home-main">
        
        <section className="welcome-section">
          <h2>오늘 아이에게 어떤 이야기를 남겨볼까요?</h2>
          <p>엄마의 목소리와 마음을 'AI-Log'가 함께 기록할게요.</p>
        </section>

        <section className="record-section">
          <RecordButton type="voice" />
          <RecordButton type="text" />
        </section>

        <section className="feedback-section">
          <h3>오늘의 마음 날씨</h3>
          <p>{todayFeedback.message}</p>
        </section>

      </main>
    </div>
  );
}

export default Home;