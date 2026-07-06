import streamlit as st
import asyncio
import os
import json
from groq import Groq  
import edge_tts
from streamlit_mic_recorder import speech_to_text

# =====================================================================
# CẤU HÌNH KHÓA API KEY CỦA BẠN TẠI ĐÂY
# =====================================================================
GROQ_API_KEY = st.secrets.get("GROQ_API_KEY")
client = Groq(api_key=GROQ_API_KEY)

# Chỉ thị hệ thống định hình hành vi Gia sư kiến tạo + Phân tích lỗi trực quan
PEDAGOGICAL_PROMPT = """
You are a warm, collaborative, and highly effective English peer tutor in an "AI Language Farm".
Your core objective is to help the user learn and practice English dynamically.

Adhere strictly to the following interaction rules:
1. Review the user's input. If they make a grammatical, spelling, or vocabulary mistake, DO NOT give the correct answer immediately.
2. Clearly point out the error (you can explicitly wrap the wrong phrase or rule explanation so the user can easily see it), explain the rule briefly using simple language, and encourage them to try correcting it in their next turn.
3. Keep responses highly focused, direct, and under 150 words. Avoid generic praise (e.g., "Good job!", "Excellent!").
4. Always end your turn with a level-appropriate, open-ended question based on the ongoing topic to keep the conversation going.
5. If the user fails to correct the mistake after 2-3 attempts, provide the direct correction and transition to a new topic.
"""

# Khởi tạo các trạng thái bộ nhớ đệm độc lập cho từng phiên người dùng
if "chat_history" not in st.session_state:
    st.session_state.chat_history = list()
if "last_processed_text" not in st.session_state:
    st.session_state.last_processed_text = ""
if "audio_bytes_to_play" not in st.session_state:
    st.session_state.audio_bytes_to_play = None

# TÍNH NĂNG GAME HÓA: Khởi tạo bộ đếm số bông hoa thu hoạch
if "flower_count" not in st.session_state:
    st.session_state.flower_count = 0

# Thiết lập cấu hình trang Streamlit
st.set_page_config(page_title="Gia Sư Tiếng Anh Nông Trại 🧑‍🌾🌸", page_icon="🌸", layout="centered")

# --- ĐOẠN CODE TRANG TRÍ GIAO DIỆN NÔNG TRẠI BẰNG CSS ---
st.markdown("""
<style>
    /* Toàn bộ nền ứng dụng */
    .stApp {
        background: linear-gradient(135deg, #E8F5E9 0%, #FFF8E1 100%)!important;
        font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
        color: #000000 !important;
    }
    
    p, span, label, div[data-testid="stMarkdownContainer"] {
        color: #000000 !important;
    }
    
    /* CĂN GIỮA VÀ TỐI ƯU TIÊU ĐỀ THEO KÍCH THƯỚC MÀN HÌNH */
    .center-header {
        text-align: center;
        margin-bottom: 15px;
    }
    .center-header h1 {
        color: #2E7D32 !important;
        font-weight: 800 !important;
        text-shadow: 2px 2px 4px rgba(46, 125, 50, 0.15) !important;
        font-size: 2.2rem !important;
    }
    .center-header p {
        font-size: 1.1rem;
        color: #555555 !important;
    }

    /* Khung hiển thị nông trại hoa hướng dương */
    .farm-status {
        background-color: rgba(255, 255, 255, 0.8);
        border: 2px dashed #FFCA28;
        border-radius: 15px;
        padding: 10px;
        text-align: center;
        margin-bottom: 20px;
        box-shadow: 0 4px 6px rgba(0,0,0,0.02);
    }
    .sunflowers {
        font-size: 1.6rem;
        letter-spacing: 3px;
        margin-top: 5px;
    }

    /* Thiết lập lại nút dọn dẹp */
    div.stButton > button {
        background: linear-gradient(135deg, #4CAF50 0%, #2E7D32 100%)!important;
        color: white!important;
        border-radius: 20px!important;
        border: none!important;
        padding: 10px 20px!important;
        font-weight: bold!important;
        box-shadow: 0 4px 15px rgba(76, 175, 80, 0.3)!important;
        transition: all 0.3s ease!important;
    }
    div.stButton > button:hover {
        transform: scale(1.05) translateY(-2px)!important;
    }

    .stExpander {
        background-color: rgba(255, 255, 255, 0.7)!important;
        border: 1px solid #C8E6C9!important;
        border-radius: 12px!important;
    }

    /* KHUNG CUỘN CHỨA NỘI DUNG CHÍNH (Tránh bị che khuất bởi thanh công cụ đáy) */
    .chat-scroll-area {
        margin-bottom: 130px;
        padding: 10px;
    }

    /* FIX THANH ĐIỀU KHIỂN CỐ ĐỊNH Ở ĐÁY MÀN HÌNH MƯỢT MÀ */
    .fixed-bottom-bar {
        position: fixed;
        bottom: 0;
        left: 0;
        right: 0;
        background: linear-gradient(135deg, rgba(232, 245, 233, 0.98) 0%, rgba(255, 248, 225, 0.98) 100%);
        padding: 15px 20px;
        box-shadow: 0 -5px 25px rgba(0,0,0,0.07);
        z-index: 999;
        border-top: 1px solid #C8E6C9;
    }
    .fixed-bottom-container {
        max-width: 700px;
        margin: 0 auto;
    }

    /* RESPONSIVE: ĐIỀU CHỈNH CHỮ PHÙ HỢP CHO ĐIỆN THOẠI & IPAD */
    @media (max-width: 768px) {
        .center-header h1 { font-size: 1.7rem !important; }
        .center-header p { font-size: 0.95rem; }
        div[data-testid="stChatMessage"] { font-size: 0.95rem !important; }
    }
</style>
""", unsafe_allow_html=True)

# Khởi tạo vùng nội dung chính
st.markdown('<div class="chat-scroll-area">', unsafe_allow_html=True)

# 1. TIÊU ĐỀ CĂN GIỮA ĐẸP MẮT
st.markdown("""
<div class="center-header">
    <h1>Gia Sư Tiếng Anh Nông Trại 🧑‍🌾🌸</h1>
    <p>Chăm sóc vườn tri thức Anh ngữ mỗi ngày cùng cành hoa đào thông thái.</p>
</div>
""", unsafe_allow_html=True)

# 2. KHU VỰC HIỂN THỊ NÔNG TRẠI GAME HÓA
# Tính toán số lượng hoa hiển thị thực tế trên màn hình (Tối đa 10 bông chu kỳ)
display_flowers = "🌻" * (st.session_state.flower_count % 10 if st.session_state.flower_count % 10 != 0 or st.session_state.flower_count == 0 else 10)
title_badge = f"🧑‍🌾 Cấp độ: Nông dân tập sự ({st.session_state.flower_count} 🌻)" if st.session_state.flower_count < 10 else f"🌟 Cấp độ: Chủ trang trại thông thái ({st.session_state.flower_count} 🌻)"

st.markdown(f"""
<div class="farm-status">
    <b style="color: #E65100;">{title_badge}</b>
    <div class="sunflowers">{display_flowers if st.session_state.flower_count > 0 else '🪹 Vườn trống (Hãy nói để trồng hoa)'}</div>
</div>
""", unsafe_allow_html=True)

st.markdown("<h3 style='text-align: center; color: #1B5E20;'>Luyện Nói Tiếng Anh Với Cành Hoa AI 🌸</h3>", unsafe_allow_html=True)

# HIỂN THỊ LẠI LỊCH SỬ TRÒ CHUYỆN TOÀN BỘ TRÊN MÀN HÌNH
for item in st.session_state.chat_history:
    if isinstance(item, (tuple, list)) and len(item) >= 2:
        speaker = item[0]  
        text = item[1]     
        translation = item[2] if len(item) >= 3 else None
        
        if speaker == "user":
            st.chat_message("user", avatar="🧑‍🌾").write(text)
        else:
            st.chat_message("assistant", avatar="🌸").write(text)
            if translation:
                with st.expander("🌐 Xem cành hoa dịch nghĩa"):
                    st.write(translation)

# PHÁT ÂM THANH TRỰC TIẾP TỪ BỘ NHỚ ĐỆM
if st.session_state.audio_bytes_to_play:
    st.audio(st.session_state.audio_bytes_to_play, format="audio/mp3", autoplay=True)
    st.session_state.audio_bytes_to_play = None

st.markdown('</div>', unsafe_allow_html=True) # Đóng khung nội dung chính

# 3. THANH ĐIỀU KHIỂN NEO CHẶT ĐÁY MÀN HÌNH (Đã xóa chữ "Lay r" dính lỗi trước đó)
st.markdown('<div class="fixed-bottom-bar"><div class="fixed-bottom-container">', unsafe_allow_html=True)

col1, col2 = st.columns([3.5, 1.5])
with col1:
    captured_text = speech_to_text(
        language='en',
        start_prompt="🎙️ Bắt đầu ghi âm nói",
        stop_prompt="⏹️ Dừng ghi âm",
        just_once=True,
        key='stt_module'
    )
with col2:
    if st.button("🧹 Xóa cuộc thoại", use_container_width=True):
        st.session_state.chat_history = list()
        st.session_state.last_processed_text = ""
        st.session_state.audio_bytes_to_play = None
        st.session_state.flower_count = 0  # Reset vườn hoa khi xóa cuộc thoại
        st.rerun()

st.markdown('</div></div>', unsafe_allow_html=True) # Đóng khung đáy

# --- XỬ LÝ LOGIC GỌI API KHI CÓ AUDIO MỚI ---
if captured_text and captured_text != st.session_state.last_processed_text:
    st.session_state.last_processed_text = captured_text
    st.session_state.chat_history.append(("user", captured_text, None))
    
    # Cộng thêm 1 bông hoa vào nông trại khi người dùng hoàn thành 1 câu nói thành công
    st.session_state.flower_count += 1
    
    # Hiệu ứng nổ bong bóng ăn mừng đặc biệt khi đạt mốc mỗi 10 bông hoa hướng dương
    if st.session_state.flower_count % 10 == 0:
        st.balloons()
    
    with st.spinner("Cành hoa đang suy nghĩ câu trả lời..."):
        try:
            groq_messages = [{"role": "system", "content": PEDAGOGICAL_PROMPT}]
            for speaker, text, _ in st.session_state.chat_history:
                role = "user" if speaker == "user" else "assistant"
                groq_messages.append({"role": role, "content": text})
                
            completion = client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=groq_messages,
                temperature=0.7,
            )
            ai_response_text = completion.choices[0].message.content
            
            # Thực hiện dịch ngầm sang tiếng Việt
            vi_translation = ""
            try:
                translate_prompt = f"Translate the following English text into natural, native-sounding Vietnamese. Return ONLY the translated text, do not add any intros or explanations:\n\n{ai_response_text}"
                translation_response = client.chat.completions.create(
                    model="llama-3.3-70b-versatile",
                    messages=[{"role": "user", "content": translate_prompt}],
                    temperature=0.3,
                )
                vi_translation = translation_response.choices[0].message.content
            except Exception as trans_err:
                vi_translation = f"(Không thể dịch tự động: {str(trans_err)})"
            
            st.session_state.chat_history.append(("ai", ai_response_text, vi_translation))
            
            # Chuyển âm thanh thành dòng byte chạy trực tiếp trên RAM
            async def generate_voice_stream(text):
                communicate = edge_tts.Communicate(text, voice="en-US-AvaNeural")
                audio_data = b""
                async for chunk in communicate.stream():
                    if chunk["type"] == "audio":
                        audio_data += chunk["data"]
                return audio_data
                
            st.session_state.audio_bytes_to_play = asyncio.run(generate_voice_stream(ai_response_text))
            st.rerun()
                
        except Exception as e:
            st.error(f"Lỗi kết nối hoặc xử lý API Groq: {str(e)}")
