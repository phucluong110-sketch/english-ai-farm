import streamlit as st
import asyncio
import os
import json
from google import genai
from google.genai import types
import edge_tts
from streamlit_mic_recorder import speech_to_text

# =====================================================================
# CẤU HÌNH KHÓA API KEY CỦA BẠN TẠI ĐÂY
# Hãy dán mã API Key cá nhân mới (bắt đầu bằng AIzaSy...) của bạn vào giữa hai dấu ngoặc kép
# =====================================================================
# Khởi tạo khóa API bảo mật từ Streamlit Secrets
GEMINI_API_KEY = st.secrets

# Khởi tạo client sử dụng bộ thư viện google-genai SDK mới nhất
client = genai.Client(api_key=GEMINI_API_KEY)

# Chỉ thị hệ thống định hình hành vi Gia sư kiến tạo (Constructivist Peer Tutor)
PEDAGOGICAL_PROMPT = """
You are a warm, collaborative, and highly effective English peer tutor.
Your core objective is to help the user learn and practice English dynamically.
Adhere strictly to the following interaction rules:
1. When the user makes a grammatical, spelling, or vocabulary mistake, DO NOT give the correct answer immediately.
2. Acknowledge their effort, point out the error, explain the rule briefly using simple language, and encourage them to try correcting it.
3. Keep responses highly focused, direct, and under 150 words. Avoid generic praise (e.g., "Good job!", "Excellent!").
4. Always end your turn with a level-appropriate, open-ended question based on the ongoing topic to keep the conversation going.
5. If the user fails to correct the mistake after 2-3 attempts, provide the direct correction and transition to a new topic.
"""

# Khởi tạo các trạng thái bộ nhớ đệm sử dụng list() để tránh bị lỗi hiển thị mất dấu ngoặc vuông
if "interaction_id" not in st.session_state:
    st.session_state.interaction_id = None
if "chat_history" not in st.session_state:
    st.session_state.chat_history = list()
# Biến kiểm tra chống trùng lặp yêu cầu gọi API
if "last_processed_text" not in st.session_state:
    st.session_state.last_processed_text = ""

# Thiết lập cấu hình trang Streamlit
st.set_page_config(page_title="Gia Sư Tiếng Anh Nông Trại 🧑‍🌾🌸", page_icon="🌸", layout="centered")

# --- ĐOẠN CODE TRANG TRÍ GIAO DIỆN NÔNG TRẠI BẰNG CSS ---
st.markdown("""
<style>
    /* Toàn bộ nền ứng dụng: Hiệu ứng chuyển màu mượt mà từ trời xanh dịu sang cỏ xanh non */
 .stApp {
        background: linear-gradient(135deg, #E8F5E9 0%, #FFF8E1 100%)!important;
        font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
    }
    
    /* Làm đẹp tiêu đề chính mang màu sắc của khu vườn */
    h1 {
        color: #2E7D32!important;
        font-family: 'Segoe UI', sans-serif!important;
        font-weight: 800!important;
        text-shadow: 2px 2px 4px rgba(46, 125, 50, 0.15)!important;
    }

    /* Thiết lập lại nút ghi âm và nút dọn dẹp */
    div.stButton > button {
        background: linear-gradient(135deg, #4CAF50 0%, #2E7D32 100%)!important;
        color: white!important;
        border-radius: 20px!important;
        border: none!important;
        padding: 12px 30px!important;
        font-weight: bold!important;
        box-shadow: 0 4px 15px rgba(76, 175, 80, 0.3)!important;
        transition: all 0.3s cubic-bezier(0.175, 0.885, 0.32, 1.275)!important;
    }
    div.stButton > button:hover {
        transform: scale(1.05) translateY(-3px)!important;
        box-shadow: 0 6px 20px rgba(46, 125, 50, 0.4)!important;
    }

    /* Chỉnh sửa kiểu dáng hộp Dịch Tiếng Việt */
 .stExpander {
        background-color: rgba(255, 255, 255, 0.6)!important;
        border: 1px solid #C8E6C9!important;
        border-radius: 12px!important;
        box-shadow: 0 2px 8px rgba(0,0,0,0.02)!important;
    }
</style>
""", unsafe_allow_html=True)

st.title("Gia Sư Tiếng Anh Nông Trại 🧑‍🌾🌸")
st.write("Chăm sóc vườn tri thức Anh ngữ mỗi ngày cùng cành hoa đào thông thái.")

# --- KHU VỰC GIAO TIẾP VÀ LUYỆN NÓI THỜI GIAN THỰC ---
st.header("Luyện Nói Tiếng Anh Với Cành Hoa AI 🌸")
st.write("Hãy nhấn nút ghi âm bên dưới và nói một câu tiếng Anh. Cành hoa thông thái sẽ lắng nghe và trò chuyện cùng bạn.")

# Thiết kế khu vực nút ghi âm và nút dọn dẹp hàng xóm sát nhau
col1, col2 = st.columns([4, 1])
with col1:
    captured_text = speech_to_text(
        language='en',
        start_prompt="⏺️ Bắt đầu ghi âm nói",
        stop_prompt="⏹️ Dừng ghi âm",
        just_once=True,
        key='stt_module'
    )
with col2:
    if st.button("🧹 Xóa cuộc thoại"):
        st.session_state.chat_history = list()
        st.session_state.interaction_id = None
        st.session_state.last_processed_text = ""
        st.rerun()

# Chỉ xử lý khi có câu thoại mới hoàn toàn để chống lặp trang
if captured_text and captured_text!= st.session_state.last_processed_text:
    st.session_state.last_processed_text = captured_text
    st.session_state.chat_history.append(("user", captured_text, None))
    
    with st.spinner("Cành hoa đang suy nghĩ câu trả lời..."):
        kwargs = {
            "model": "gemini-2.5-flash",
            "input": captured_text,
            "system_instruction": PEDAGOGICAL_PROMPT,
        }
        
        if st.session_state.interaction_id:
            kwargs["previous_interaction_id"] = st.session_state.interaction_id
            
        try:
            # Tạo một đối tượng tương tác mới
            interaction = client.interactions.create(**kwargs)
            
            st.session_state.interaction_id = interaction.id
            ai_response_text = interaction.output_text
            
            # Thực hiện dịch ngầm sang tiếng Việt
            vi_translation = ""
            try:
                translate_prompt = f"Translate the following English text into natural, native-sounding Vietnamese. Return ONLY the translated text, do not add any intros or explanations:\n\n{ai_response_text}"
                translation_response = client.models.generate_content(
                    model="gemini-2.5-flash",
                    contents=translate_prompt
                )
                vi_translation = translation_response.text
            except Exception as trans_err:
                vi_translation = f"(Không thể dịch tự động: {str(trans_err)})"
            
            st.session_state.chat_history.append(("ai", ai_response_text, vi_translation))
            
            # Chuyển đổi phản hồi văn bản của AI thành tệp âm thanh (TTS) bằng edge-tts
            async def generate_voice_file(text, output_path="ai_speech.mp3"):
                communicate = edge_tts.Communicate(text, voice="en-US-AvaNeural")
                await communicate.save(output_path)
                
            asyncio.run(generate_voice_file(ai_response_text))
                
        except Exception as e:
            st.error(f"Lỗi kết nối hoặc xử lý API: {str(e)}")
                
    # HIỂN THỊ LẠI LỊCH SỬ TRÒ CHUYỆN (ĐÃ SỬA LỖI INDEX CHUẨN XÁC)
    for item in st.session_state.chat_history:
        if isinstance(item, (tuple, list)) and len(item) >= 2:
            speaker = item  # Vai trò "user" hoặc "ai"
            text = item[1]     # Câu thoại
            translation = item[2] if len(item) >= 3 else None  # ĐÃ SỬA: Lấy chính xác bản dịch tiếng Việt ở vị trí thứ 3 (chỉ mục index 2)
            
            if speaker == "user":
                st.chat_message("user", avatar="🧑‍🌾").write(text)
            else:
                st.chat_message("assistant", avatar="🌸").write(text)
                if translation:
                    with st.expander("🌐 Xem cành hoa dịch nghĩa"):
                        st.write(translation)
        
if os.path.exists("ai_speech.mp3") and captured_text:
    st.audio("ai_speech.mp3", format="audio/mp3", autoplay=True)
    try:
        os.remove("ai_speech.mp3")
    except PermissionError:
        pass