import streamlit as st
import time
import csv
import os
import re
import requests
from datetime import datetime
from bs4 import BeautifulSoup
from pypdf import PdfReader
import docx
from PIL import Image
from google import genai

# --- 1. ページ設定とロゴ ---
st.set_page_config(
    page_title="knowledge2music",
    page_icon="🎵",
    layout="centered"
)

# --- 2. 多言語表示 (JP - VI - EN) ---
translations = {
    "JP": {
        "tagline": "学習内容をAIで要約し、覚えやすい音楽に変えるプラットフォーム",
        "author_label": "制作者：",
        "login_title": "🔐 ログインして始める",
        "login_desc": "Googleアカウントでログインしてください（OAuth 2.0）。",
        "login_demo_desc": "デモモードです。Google OAuth は設定されていないため、メールアドレス形式を入力すると試用できます。Google認証は行われません。",
        "login_email_label": "デモ用メールアドレス:",
        "btn_demo_login": "デモモードで続ける",
        "demo_badge": "ℹ️ デモモード: Google OAuth による本人確認は無効です。",
        "btn_google_login": "Googleでログイン (Google Login)",
        "btn_logout": "ログアウト",
        "welcome_user": "ようこそ、",
        "security_badge": "🛡️ Google OAuth 2.0でログイン中",
        "login_invalid_demo": "⚠️ デモ用にメールアドレス形式で入力してください。",
        "tab_text": "📝 テキスト入力",
        "tab_file": "📄 ファイル",
        "tab_img": "🖼️ 画像",
        "tab_url": "🔗 リンク",
        "text_prompt": "暗記したい学習内容をここに貼り付けてください:",
        "file_prompt": "ドキュメントをアップロード (PDF, DOCX, TXT)",
        "img_prompt": "ノートや教科書の画像をアップロード (PNG, JPG)",
        "url_prompt": "学習ページのURLを貼り付けてください:",
        "prompt_section": "🎛️ 曲のスタイルとプロンプト設定 (Prompt)",
        "genre_label": "音楽ジャンル:",
        "vibe_label": "曲の雰囲気・テンポ:",
        "vocal_label": "ボーカルスタイル:",
        "custom_prompt_label": "AIへの追加リクエスト (Custom Prompt):",
        "custom_prompt_placeholder": "例: 年号と重要なキーワードを韻を踏んで強調してください...",
        "btn_generate": "1. 要約と歌詞を作成 🚀",
        "status_reading": "Gemini AIが学習内容を要約し、歌詞と音楽スタイルを作成中...",
        "error_no_data": "⚠️ 学習内容を入力してください（テキスト、ファイル、画像、またはURL）。",
        "error_cooldown": "⏳ 連続リクエスト防止のため、あと {sec} 秒お待ちください。",
        "step2_title": "🎸 2. アプリ内でボーカル曲を生成",
        "step2_guide": "タイトル、スタイル、歌詞を使って、この画面で曲を生成します。",
        "btn_generate_audio": "🎵 曲を生成 (ACE-Step · fal.ai)",
        "status_generating_audio": "fal.aiで曲を生成中です。キューの状況によって少し時間がかかります...",
        "audio_ready": "✅ 曲を生成して保存しました。",
        "audio_error": "曲を生成できませんでした:",
        "audio_quota_note": "fal.aiのACE-Step APIを使います。60秒の曲なら料金の目安は約$0.012で、実際の生成時間に応じて課金されます。生成済みのスタイルタグと歌詞のみを送信します。",
        "fal_key_hint": "[fal.aiでAPIキーを作成](https://fal.ai/dashboard/keys)し、`.streamlit/secrets.toml` に `FAL_KEY = \"...\"` と設定してアプリを再起動してください。キーを共有しないでください。",
        "fal_key_missing": "`.streamlit/secrets.toml` に `FAL_KEY` が設定されていません。",
        "fal_billing_hint": "fal.aiのアカウントに利用可能なクレジットがあるか確認してください。",
        "step3_title": "🎧 3. Webプレーヤーと曲のライブラリ",
        "upload_mp3_label": "再生・保存するMP3/WAVファイルをアップロード:",
        "saved_songs_label": "📂 保存済みの曲から選択:",
        "feedback_title": "💬 ご意見・フィードバック",
        "feedback_rate": "アプリの評価:",
        "feedback_input": "改善点やご感想をお聞かせください:",
        "feedback_btn": "フィードバックを送信",
        "feedback_thanks": "✅ 貴重なご意見をありがとうございます！",
        "summary_label": "📌 学習内容の要約",
        "song_title_label": "🏷️ 曲名",
        "music_style_label": "🎸 音楽スタイル",
        "lyrics_label": "🎤 歌詞",
        "playing_label": "再生中：",
        "download_label": "⬇️ ダウンロード",
        "url_error": "URLを読み込めませんでした: {error}",
        "gemini_key_missing": "⚠️ `.streamlit/secrets.toml` に GEMINI_API_KEY が設定されていません。",
        "model_list_error": "❌ APIキーでモデル一覧を取得できませんでした: {error}",
        "generation_success": "✅ {model} で生成しました。",
        "no_available_model": "このAPIキーで利用できるテキスト生成モデルがありません。",
        "models_failed": "{count} 個のモデルを試しましたが、すべて失敗しました（{models}）。最初のエラー: {detail}",
        "generation_error": "❌ 生成エラー：",
        "unknown_error": "不明なエラー",
        "fallback_title": "Knowledge2Musicの曲",
        "genre_options": {
            "J-Pop / Anime Opening": "J-Pop／アニメ主題歌",
            "Rap / Boom-Bap Hip-Hop": "ラップ／ブーンバップ・ヒップホップ",
            "Pop Ballad": "ポップバラード",
            "Lofi Chill Hop": "ローファイ・チルホップ",
            "EDM / Future Bass": "EDM／フューチャーベース",
            "Acoustic Folk": "アコースティック・フォーク"
        },
        "vibe_options": {
            "Catchy & Easy to Memorize": "覚えやすく、耳に残る",
            "Upbeat & Energetic": "明るくエネルギッシュ",
            "Humorous & Fun": "ユーモラスで楽しい",
            "Emotional & Melodic": "感情豊かでメロディアス"
        },
        "vocal_options": {
            "Clear Female Vocal": "透明感のある女性ボーカル",
            "Energetic Male Vocal": "エネルギッシュな男性ボーカル",
            "Male & Female Duet": "男女デュエット",
            "Melodic Rap Flow": "メロディック・ラップ"
        }
    },
    "VI": {
        "tagline": "Nền tảng AI tóm tắt kiến thức và chuyển hóa thành âm nhạc dễ nhớ",
        "author_label": "Tác giả:",
        "login_title": "🔐 Đăng nhập để sử dụng",
        "login_desc": "Để đảm bảo an toàn và bảo mật, vui lòng đăng nhập thông qua tài khoản Google (Xác thực OAuth 2.0).",
        "login_demo_desc": "Chế độ demo: Google OAuth chưa được cấu hình. Nhập địa chỉ có dạng email để vào thử; hệ thống không xác thực tài khoản Google.",
        "login_email_label": "Email dùng cho demo:",
        "btn_demo_login": "Vào thử chế độ demo",
        "demo_badge": "ℹ️ Chế độ demo: chưa xác minh danh tính bằng Google OAuth.",
        "btn_google_login": "Đăng nhập bằng Google",
        "btn_logout": "Đăng xuất",
        "welcome_user": "Xin chào, ",
        "security_badge": "🛡️ Đăng nhập bằng Google OAuth 2.0",
        "login_invalid_demo": "⚠️ Hãy nhập địa chỉ có dạng email để vào chế độ demo.",
        "tab_text": "📝 Nhập văn bản",
        "tab_file": "📄 Tải File",
        "tab_img": "🖼️ Tải Ảnh",
        "tab_url": "🔗 Nhập Link",
        "text_prompt": "Dán nội dung bài học cần ghi nhớ vào đây:",
        "file_prompt": "Kéo thả tài liệu vào đây (PDF, DOCX, TXT)",
        "img_prompt": "Kéo thả ảnh chụp trang sách/vở vào đây (PNG, JPG)",
        "url_prompt": "Dán đường link (URL) trang web bài học:",
        "prompt_section": "🎛️ Tùy chỉnh bài hát theo ý muốn (Prompt)",
        "genre_label": "Thể loại nhạc:",
        "vibe_label": "Giai điệu / Cảm xúc:",
        "vocal_label": "Chất giọng ca sĩ:",
        "custom_prompt_label": "Yêu cầu riêng cho AI (Custom Prompt):",
        "custom_prompt_placeholder": "VD: Hãy viết theo kiểu rap vần đôi, nhấn mạnh các mốc thời gian và công thức...",
        "btn_generate": "1. Tóm tắt & sáng tác lời bài hát 🚀",
        "status_reading": "Gemini AI đang tóm tắt kiến thức và sáng tác lời bài hát...",
        "error_no_data": "⚠️ Bạn chưa cung cấp nội dung bài học. Vui lòng nhập chữ, tải file, ảnh hoặc link!",
        "error_cooldown": "⏳ Hệ thống chống spam: Vui lòng đợi {sec} giây trước khi tạo tiếp.",
        "step2_title": "🎸 2. Tạo bài hát ngay trong ứng dụng",
        "step2_guide": "Ứng dụng dùng tiêu đề, phong cách và lời bài hát để tạo audio có giọng hát ngay tại đây.",
        "btn_generate_audio": "🎵 Tạo bài hát (ACE-Step · fal.ai, ~$0.012/60 giây)",
        "status_generating_audio": "fal.ai đang tạo bài hát; có thể mất một lúc tùy hàng đợi...",
        "audio_ready": "✅ Đã tạo và lưu bài hát.",
        "audio_error": "Không tạo được bài hát:",
        "audio_quota_note": "Dùng API ACE-Step của fal.ai. Bài 60 giây ước tính khoảng $0.012; phí tính theo thời lượng audio tạo ra. App chỉ gửi thẻ phong cách và lời bài hát đã tạo.",
        "fal_key_hint": "Tạo [API key trên fal.ai](https://fal.ai/dashboard/keys), thêm `FAL_KEY = \"...\"` vào `.streamlit/secrets.toml`, rồi khởi động lại app. Đừng chia sẻ key.",
        "fal_key_missing": "Chưa có `FAL_KEY` trong `.streamlit/secrets.toml`.",
        "fal_billing_hint": "Kiểm tra tài khoản fal.ai còn credit khả dụng không.",
        "step3_title": "🎧 3. Trình phát nhạc và thư viện trên Web",
        "upload_mp3_label": "Tải lên file MP3/WAV để phát và lưu trong thư viện:",
        "saved_songs_label": "📂 Hoặc mở lại các bài hát đã lưu trên Web:",
        "feedback_title": "💬 Góp ý cải thiện Web",
        "feedback_rate": "Đánh giá của bạn:",
        "feedback_input": "Nhập ý kiến đóng góp của bạn tại đây:",
        "feedback_btn": "Gửi góp ý",
        "feedback_thanks": "✅ Cảm ơn bạn đã góp ý! Dữ liệu đã được lưu lại.",
        "summary_label": "📌 Tóm tắt kiến thức",
        "song_title_label": "🏷️ Tên bài hát",
        "music_style_label": "🎸 Phong cách nhạc",
        "lyrics_label": "🎤 Lời bài hát",
        "playing_label": "Đang phát:",
        "download_label": "⬇️ Tải xuống",
        "url_error": "Không thể tải URL: {error}",
        "gemini_key_missing": "⚠️ Chưa cấu hình GEMINI_API_KEY trong `.streamlit/secrets.toml`.",
        "model_list_error": "❌ Không thể lấy danh sách model bằng API key: {error}",
        "generation_success": "✅ Đã tạo thành công bằng model: {model}",
        "no_available_model": "Tài khoản API key này hiện không có model tạo văn bản khả dụng.",
        "models_failed": "Đã thử {count} model nhưng đều thất bại ({models}). Lỗi đầu tiên: {detail}",
        "generation_error": "❌ Lỗi tạo nội dung:",
        "unknown_error": "Không xác định",
        "fallback_title": "Bài hát Knowledge2Music",
        "genre_options": {
            "J-Pop / Anime Opening": "J-Pop / Nhạc mở đầu anime",
            "Rap / Boom-Bap Hip-Hop": "Rap / Boom-Bap Hip-Hop",
            "Pop Ballad": "Pop Ballad",
            "Lofi Chill Hop": "Lofi Chill Hop",
            "EDM / Future Bass": "EDM / Future Bass",
            "Acoustic Folk": "Acoustic Folk"
        },
        "vibe_options": {
            "Catchy & Easy to Memorize": "Bắt tai, dễ ghi nhớ",
            "Upbeat & Energetic": "Sôi động, tràn đầy năng lượng",
            "Humorous & Fun": "Hài hước, vui nhộn",
            "Emotional & Melodic": "Giàu cảm xúc, du dương"
        },
        "vocal_options": {
            "Clear Female Vocal": "Giọng nữ trong trẻo",
            "Energetic Male Vocal": "Giọng nam sôi động",
            "Male & Female Duet": "Song ca nam nữ",
            "Melodic Rap Flow": "Rap giai điệu"
        }
    },
    "EN": {
        "tagline": "AI platform that summarizes study materials into catchy music",
        "author_label": "Author:",
        "login_title": "🔐 Sign in to continue",
        "login_desc": "For your security, please sign in with your Google account (Protected by OAuth 2.0).",
        "login_demo_desc": "Demo mode: Google OAuth is not configured. Enter an email-shaped address to continue; Google identity is not verified.",
        "login_email_label": "Demo email address:",
        "btn_demo_login": "Continue in demo mode",
        "demo_badge": "ℹ️ Demo mode: Google OAuth identity verification is off.",
        "btn_google_login": "Sign in with Google",
        "btn_logout": "Sign out",
        "welcome_user": "Welcome, ",
        "security_badge": "🛡️ Signed in with Google OAuth 2.0",
        "login_invalid_demo": "⚠️ Enter an email-shaped address to continue in demo mode.",
        "tab_text": "📝 Text Input",
        "tab_file": "📄 File Upload",
        "tab_img": "🖼️ Image Upload",
        "tab_url": "🔗 URL Input",
        "text_prompt": "Paste your study content here:",
        "file_prompt": "Drop your document here (PDF, DOCX, TXT)",
        "img_prompt": "Drop your image here (PNG, JPG)",
        "url_prompt": "Paste the website URL:",
        "prompt_section": "🎛️ Customize Song Style (Prompt)",
        "genre_label": "Music Genre:",
        "vibe_label": "Mood / Tempo:",
        "vocal_label": "Vocal Style:",
        "custom_prompt_label": "Custom Prompt for AI:",
        "custom_prompt_placeholder": "e.g., Make it a catchy rap with double rhymes, focusing on key dates...",
        "btn_generate": "1. Summarize & Write Song Lyrics 🚀",
        "status_reading": "Gemini AI is summarizing and composing structured lyrics...",
        "error_no_data": "⚠️ Please provide study content via text, file, image, or URL!",
        "error_cooldown": "⏳ Anti-spam protection: Please wait {sec} seconds before generating again.",
        "step2_title": "🎸 2. Generate a song in the app",
        "step2_guide": "The app uses the generated title, style, and lyrics to create vocals here.",
        "btn_generate_audio": "🎵 Generate song (ACE-Step · fal.ai, ~$0.012/60 sec)",
        "status_generating_audio": "fal.ai is generating the song; queue time may vary...",
        "audio_ready": "✅ Song generated and saved.",
        "audio_error": "Could not generate the song:",
        "audio_quota_note": "Uses fal.ai's ACE-Step API. A 60-second song costs about $0.012; billing follows the generated audio duration. Only generated style tags and lyrics are sent.",
        "fal_key_hint": "Create a [fal.ai API key](https://fal.ai/dashboard/keys), add `FAL_KEY = \"...\"` to `.streamlit/secrets.toml`, then restart the app. Do not share the key.",
        "fal_key_missing": "`FAL_KEY` is missing from `.streamlit/secrets.toml`.",
        "fal_billing_hint": "Check that your fal.ai account has available credits.",
        "step3_title": "🎧 3. Web audio player and library",
        "upload_mp3_label": "Upload an MP3/WAV file to play and save it in the library:",
        "saved_songs_label": "📂 Or select from previously saved songs:",
        "feedback_title": "💬 Feedback & Suggestions",
        "feedback_rate": "Rate our web app:",
        "feedback_input": "Share your ideas to help us improve:",
        "feedback_btn": "Submit Feedback",
        "feedback_thanks": "✅ Thank you! Your feedback has been saved.",
        "summary_label": "📌 Study Summary",
        "song_title_label": "🏷️ Song Title",
        "music_style_label": "🎸 Music Style",
        "lyrics_label": "🎤 Lyrics",
        "playing_label": "Playing:",
        "download_label": "⬇️ Download",
        "url_error": "Could not load URL: {error}",
        "gemini_key_missing": "⚠️ GEMINI_API_KEY is not configured in `.streamlit/secrets.toml`.",
        "model_list_error": "❌ Could not list models with this API key: {error}",
        "generation_success": "✅ Generated successfully with model: {model}",
        "no_available_model": "No text generation models are available for this API key.",
        "models_failed": "All {count} models failed ({models}). First error: {detail}",
        "generation_error": "❌ Generation error:",
        "unknown_error": "Unknown",
        "fallback_title": "Knowledge2Music Song",
        "genre_options": {
            "J-Pop / Anime Opening": "J-Pop / Anime Opening",
            "Rap / Boom-Bap Hip-Hop": "Rap / Boom-Bap Hip-Hop",
            "Pop Ballad": "Pop Ballad",
            "Lofi Chill Hop": "Lofi Chill Hop",
            "EDM / Future Bass": "EDM / Future Bass",
            "Acoustic Folk": "Acoustic Folk"
        },
        "vibe_options": {
            "Catchy & Easy to Memorize": "Catchy & Easy to Memorize",
            "Upbeat & Energetic": "Upbeat & Energetic",
            "Humorous & Fun": "Humorous & Fun",
            "Emotional & Melodic": "Emotional & Melodic"
        },
        "vocal_options": {
            "Clear Female Vocal": "Clear Female Vocal",
            "Energetic Male Vocal": "Energetic Male Vocal",
            "Male & Female Duet": "Male & Female Duet",
            "Melodic Rap Flow": "Melodic Rap Flow"
        }
    }
}

# --- 3. セッション状態の初期化 ---
if "lang" not in st.session_state:
    st.session_state["lang"] = "JP"
if "authenticated" not in st.session_state:
    st.session_state["authenticated"] = False
if "user_email" not in st.session_state:
    st.session_state["user_email"] = ""
if "last_request_time" not in st.session_state:
    st.session_state["last_request_time"] = 0.0
if "song_data" not in st.session_state:
    st.session_state["song_data"] = None
if "generated_audio_path" not in st.session_state:
    st.session_state["generated_audio_path"] = None

t = translations[st.session_state["lang"]]

# --- 4. ヘッダー：ロゴ、制作者、言語選択 ---
top_col1, top_col2 = st.columns([4, 1])
with top_col1:
    st.markdown(
        f"""
        <div style="display:flex; align-items:center; gap:12px;">
            <div style="background: linear-gradient(135deg, #6366f1, #ec4899); padding: 10px 16px; border-radius: 12px; color: white; font-weight: 800; font-size: 24px; letter-spacing: 0.5px;">
                🎵 knowledge2music
            </div>
        </div>
        <p style="margin-top: 6px; margin-bottom: 2px; color: #666; font-size: 14px;">{t["tagline"]}</p>
        <p style="margin-top: 0px; font-size: 13px; color: #888;">
            ✍️ <b>{t["author_label"]}</b> Le Van Linh
        </p>
        """,
        unsafe_allow_html=True
    )

with top_col2:
    language_options = {"日本語": "JP", "Tiếng Việt": "VI", "English": "EN"}
    language_labels = list(language_options.keys())
    current_language_label = next(
        label for label, code in language_options.items()
        if code == st.session_state["lang"]
    )
    selected_language_label = st.selectbox(
        "🌐 言語",
        options=language_labels,
        index=language_labels.index(current_language_label),
        label_visibility="collapsed"
    )
    selected_lang = language_options[selected_language_label]
    if selected_lang != st.session_state["lang"]:
        st.session_state["lang"] = selected_lang
        st.rerun()

st.markdown("---")

# --- 5. Googleログインとセキュリティ ---
def get_secret_safe(key_name):
    try:
        return st.secrets.get(key_name, None)
    except Exception:
        return None


FAL_ACE_STEP_QUEUE_URL = "https://queue.fal.run/fal-ai/ace-step"


def generate_audio_with_fal(song_data, duration=60):
    """Generate a song through fal.ai and return its bytes, MIME type, and extension."""
    api_key = get_secret_safe("FAL_KEY")
    if not api_key or not str(api_key).strip():
        raise RuntimeError("FAL_KEY is missing from Streamlit secrets.")

    headers = {
        "Authorization": f"Key {str(api_key).strip()}",
        "Content-Type": "application/json",
    }
    payload = {
        "tags": str(song_data["tags"])[:500],
        "lyrics": str(song_data["lyrics"])[:6000],
        "duration": duration,
        "number_of_steps": 27,
    }

    submit_response = requests.post(
        FAL_ACE_STEP_QUEUE_URL,
        headers=headers,
        json=payload,
        timeout=(15, 120),
    )
    if submit_response.status_code in {401, 403}:
        raise RuntimeError("fal.ai rejected FAL_KEY. Check the API key in Streamlit secrets.")
    if submit_response.status_code == 402:
        raise RuntimeError("fal.ai account has no available credits.")
    submit_response.raise_for_status()
    job = submit_response.json()

    status_url = job.get("status_url")
    response_url = job.get("response_url")
    cancel_url = job.get("cancel_url")
    if not status_url or not response_url:
        raise RuntimeError("fal.ai did not return the queue URLs for this request.")

    deadline = time.monotonic() + 600
    while time.monotonic() < deadline:
        status_response = requests.get(status_url, headers=headers, timeout=(15, 30))
        if status_response.status_code in {401, 403}:
            raise RuntimeError("fal.ai rejected FAL_KEY while checking the generation status.")
        status_response.raise_for_status()
        status_data = status_response.json()

        if status_data.get("status") == "COMPLETED":
            if status_data.get("error"):
                raise RuntimeError(str(status_data["error"]))
            break
        time.sleep(2)
    else:
        if cancel_url:
            try:
                requests.put(cancel_url, headers=headers, timeout=(10, 15))
            except requests.RequestException:
                pass
        raise RuntimeError("fal.ai generation did not finish within 10 minutes; the request was cancelled.")

    result_response = requests.get(response_url, headers=headers, timeout=(15, 60))
    result_response.raise_for_status()
    result = result_response.json()
    audio_item = result.get("audio") or {}
    audio_url = audio_item.get("url")
    if not audio_url:
        raise RuntimeError("fal.ai finished but did not return an audio file.")

    audio_response = requests.get(audio_url, timeout=(15, 120))
    audio_response.raise_for_status()
    if not audio_response.content:
        raise RuntimeError("fal.ai returned an empty audio file.")

    content_type = audio_item.get("content_type") or audio_response.headers.get("Content-Type", "audio/wav")
    if ";" in content_type:
        content_type = content_type.split(";", 1)[0].strip()
    file_name = audio_item.get("file_name") or audio_url.split("?", 1)[0]
    extension = os.path.splitext(file_name)[1].lower()
    if extension not in {".wav", ".mp3", ".flac", ".ogg"}:
        extension = ".mp3" if content_type in {"audio/mpeg", "audio/mp3"} else ".wav"
    return audio_response.content, content_type, extension

auth_cfg = get_secret_safe("auth")
oauth_configured = bool(auth_cfg and "client_id" in auth_cfg)
is_native_logged_in = getattr(st.user, "is_logged_in", False)

if not st.session_state["authenticated"] and not is_native_logged_in:
    st.subheader(t["login_title"])
    st.info(t["login_desc"] if oauth_configured else t["login_demo_desc"])

    demo_email_input = ""
    if not oauth_configured:
        demo_email_input = st.text_input(
            t["login_email_label"],
            value="",
            placeholder="demo@example.com"
        )

    login_button_text = t["btn_google_login"] if oauth_configured else t["btn_demo_login"]
    if st.button(f"🔵 {login_button_text}", use_container_width=True):
        if oauth_configured:
            st.login()
        else:
            if demo_email_input.strip() and "@" in demo_email_input:
                st.session_state["authenticated"] = True
                st.session_state["user_email"] = demo_email_input.strip()
                st.rerun()
            else:
                st.error(t["login_invalid_demo"])

    st.caption(t["security_badge"] if oauth_configured else t["demo_badge"])
    st.stop()

# --- 6. サイドバー：アカウントとフィードバック ---
with st.sidebar:
    st.markdown("### 🎵 knowledge2music")
    st.caption(f"**{t['author_label']}** Le Van Linh")
    
    current_user = getattr(st.user, "email", None) or st.session_state["user_email"]
    st.success(f"{t['welcome_user']} **{current_user}**")
    st.caption(t["security_badge"] if oauth_configured else t["demo_badge"])

    if st.button(t["btn_logout"], use_container_width=True):
        if is_native_logged_in:
            st.logout()
        st.session_state["authenticated"] = False
        st.session_state["user_email"] = ""
        st.rerun()

    st.markdown("---")
    st.subheader(t["feedback_title"])
    with st.form("feedback_form", clear_on_submit=True):
        rating = st.slider(
            t["feedback_rate"], min_value=1, max_value=5, value=5, format="%d ⭐"
        )
        feedback_text = st.text_area(t["feedback_input"], max_chars=300)
        submitted = st.form_submit_button(
            t["feedback_btn"], use_container_width=True
        )
        
        if submitted and feedback_text.strip():
            file_exists = os.path.isfile("feedback.csv")
            with open("feedback.csv", mode="a", newline="", encoding="utf-8") as f:
                writer = csv.writer(f)
                if not file_exists:
                    writer.writerow(["Timestamp", "User", "Rating", "Comment"])
                ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                writer.writerow([ts, current_user, rating, feedback_text.strip()])
            st.success(t["feedback_thanks"])

# --- 7. 学習内容の入力（4つのタブ） ---
tab1, tab2, tab3, tab4 = st.tabs(
    [t["tab_text"], t["tab_file"], t["tab_img"], t["tab_url"]]
)

extracted_text = ""
pil_image = None

with tab1:
    text_input = st.text_area(t["text_prompt"], height=150, max_chars=5000)
    if text_input.strip():
        extracted_text += text_input.strip() + "\n"

with tab2:
    uploaded_file = st.file_uploader(
        t["file_prompt"], type=["txt", "pdf", "docx"]
    )
    if uploaded_file is not None:
        st.success(f"📄 {uploaded_file.name}")
        ext = uploaded_file.name.split(".")[-1].lower()
        if ext == "txt":
            raw_txt = uploaded_file.read().decode("utf-8", errors="ignore")
            extracted_text += raw_txt + "\n"
        elif ext == "pdf":
            reader = PdfReader(uploaded_file)
            for page in reader.pages:
                extracted_text += (page.extract_text() or "") + "\n"
        elif ext == "docx":
            doc = docx.Document(uploaded_file)
            for para in doc.paragraphs:
                extracted_text += para.text + "\n"

with tab3:
    uploaded_image = st.file_uploader(
        t["img_prompt"], type=["png", "jpg", "jpeg"]
    )
    if uploaded_image is not None:
        pil_image = Image.open(uploaded_image)
        st.image(pil_image, use_container_width=True)

with tab4:
    url_input = st.text_input(t["url_prompt"], max_chars=300)
    if url_input.strip():
        try:
            resp = requests.get(url_input.strip(), timeout=8)
            soup = BeautifulSoup(resp.text, "html.parser")
            page_txt = soup.get_text(separator=" ", strip=True)[:4000]
            extracted_text += page_txt + "\n"
        except Exception as e:
            st.warning(t["url_error"].format(error=e))

st.markdown("---")

# --- 8. プロンプトと音楽スタイルの設定 ---
st.subheader(t["prompt_section"])

col_p1, col_p2, col_p3 = st.columns(3)
with col_p1:
    genre = st.selectbox(
        t["genre_label"],
        [
            "J-Pop / Anime Opening",
            "Rap / Boom-Bap Hip-Hop",
            "Pop Ballad",
            "Lofi Chill Hop",
            "EDM / Future Bass",
            "Acoustic Folk"
        ],
        format_func=lambda option: t["genre_options"][option]
    )
with col_p2:
    vibe = st.selectbox(
        t["vibe_label"],
        [
            "Catchy & Easy to Memorize",
            "Upbeat & Energetic",
            "Humorous & Fun",
            "Emotional & Melodic"
        ],
        format_func=lambda option: t["vibe_options"][option]
    )
with col_p3:
    vocal_style = st.selectbox(
        t["vocal_label"],
        [
            "Clear Female Vocal",
            "Energetic Male Vocal",
            "Male & Female Duet",
            "Melodic Rap Flow"
        ],
        format_func=lambda option: t["vocal_options"][option]
    )

custom_prompt = st.text_input(
    t["custom_prompt_label"],
    placeholder=t["custom_prompt_placeholder"],
    max_chars=500
)

# --- 9. ステップ1：Geminiで要約と歌詞を作成 ---
if st.button(t["btn_generate"], type="primary", use_container_width=True):
    now = time.time()
    cooldown = 5

    if now - st.session_state["last_request_time"] < cooldown:
        remaining = int(cooldown - (now - st.session_state["last_request_time"]))
        st.warning(t["error_cooldown"].format(sec=remaining))
    elif not extracted_text.strip() and pil_image is None:
        st.error(t["error_no_data"])
    else:
        api_key = get_secret_safe("GEMINI_API_KEY")
        if not api_key:
            st.error(t["gemini_key_missing"])
            st.stop()

        st.session_state["last_request_time"] = now

        try:
            client = genai.Client(api_key=api_key.strip())
            lang_map = {"JP": "Japanese", "VI": "Vietnamese", "EN": "English"}
            lang_name = lang_map[st.session_state["lang"]]

            with st.spinner(t["status_reading"]):
                system_instruction = f"""
                You are an expert educational songwriter writing a complete, memorable song for an AI music generator.
                Output Language for Summary, Title, and Lyrics: {lang_name}.
                Music Genre: {genre}.
                Mood/Tempo: {vibe}.
                Vocal Style: {vocal_style}.
                User's Custom Request: {custom_prompt}.

                Strictly format your output using EXACTLY these 4 headers:
                ===TITLE===
                (A short, catchy song title in {lang_name})

                ===SUMMARY===
                (3 to 5 bullet points summarizing the core facts, dates, or formulas to memorize)

                ===STYLE_TAGS===
                (Comma-separated English music style tags, max 120 characters, e.g.: {genre}, {vibe}, {vocal_style}, catchy hook, clear pronunciation)

                ===LYRICS===
                (Structured song lyrics in {lang_name} with section labels like [Intro], [Verse 1], [Chorus], [Verse 2], [Chorus], [Outro]. Make the rhymes catchy so students can memorize the facts.)
                """

                contents = [system_instruction]
                if extracted_text.strip():
                    contents.append(f"Study Material:\n{extracted_text}")
                if pil_image is not None:
                    contents.append(pil_image)

                # APIキーで利用可能なモデル一覧をGoogleサーバーから取得
                available_models = []
                try:
                    for m in client.models.list():
                        m_name = getattr(m, "name", "")
                        actions = (
                            getattr(m, "supported_actions", None)
                            or getattr(m, "supported_generation_methods", None)
                            or []
                        )
                        # 画像・音声・埋め込みモデルを除外し、テキスト生成用のGeminiモデルだけを選択
                        skip_keywords = ["tts", "image", "imagen", "veo", "embedding", "aqa", "audio", "robotics", "computer-use"]
                        if "gemini" in m_name.lower() and not any(k in m_name.lower() for k in skip_keywords):
                            if not actions or "generateContent" in actions:
                                available_models.append(m_name)
                except Exception as list_err:
                    st.error(t["model_list_error"].format(error=list_err))
                    st.stop()

                # 高速で利用枠を節約できるFlashモデルを優先
                available_models.sort(
                    key=lambda x: (0 if "flash" in x.lower() else 1, x),
                    reverse=False
                )

                if not available_models:
                    raise RuntimeError(t["no_available_model"])

                response = None
                error_logs = []

                for tm in available_models:
                    try:
                        response = client.models.generate_content(
                            model=tm,
                            contents=contents
                        )
                        if response and response.text:
                            st.toast(t["generation_success"].format(model=tm))
                            break
                    except Exception as err:
                        error_logs.append(f"{tm}: {err}")
                        continue

                if response is None:
                    # 最初のモデルのエラーを表示して原因を確認
                    raise RuntimeError(
                        t["models_failed"].format(
                            count=len(available_models),
                            models=", ".join(available_models[:4]) + "...",
                            detail=error_logs[0] if error_logs else t["unknown_error"],
                        )
                    )

                raw_out = response.text

                # 生成結果を各セクションに分割
                title_val = t["fallback_title"]
                summary_val = ""
                tags_val = f"{genre}, {vibe}, {vocal_style}, catchy melody"
                lyrics_val = raw_out.strip()

                if "===LYRICS===" in raw_out:
                    before_lyr, lyrics_val = raw_out.split("===LYRICS===", 1)
                    if "===STYLE_TAGS===" in before_lyr:
                        before_tags, tags_val = before_lyr.split("===STYLE_TAGS===", 1)
                    else:
                        before_tags = before_lyr

                    if "===SUMMARY===" in before_tags:
                        before_sum, summary_val = before_tags.split("===SUMMARY===", 1)
                        title_val = before_sum.replace("===TITLE===", "").strip()
                    else:
                        summary_val = before_tags.strip()

                st.session_state["generated_audio_path"] = None
                st.session_state["song_data"] = {
                    "title": title_val.strip(),
                    "summary": summary_val.strip(),
                    "tags": tags_val.strip(),
                    "lyrics": lyrics_val.strip()
                }
        except Exception as e:
            st.error(f"{t['generation_error']} {e}")

# --- 10. ステップ2：結果を表示してアプリ内で曲を生成 ---
if st.session_state["song_data"] is not None:
    data = st.session_state["song_data"]
    st.markdown("---")
    st.subheader(t["step2_title"])
    st.caption(t["step2_guide"])

    col_s1, col_s2 = st.columns([1, 1])
    with col_s1:
        st.markdown(f"#### {t['summary_label']}")
        st.info(data["summary"])

        st.markdown(f"#### {t['song_title_label']}")
        st.code(data["title"], language="text")

        st.markdown(f"#### {t['music_style_label']}")
        st.code(data["tags"], language="text")

        st.caption(t["audio_quota_note"])
        fal_key_configured = bool(get_secret_safe("FAL_KEY"))
        if not fal_key_configured:
            st.info(t["fal_key_hint"])
        if st.button(
            t["btn_generate_audio"],
            type="primary",
            use_container_width=True,
            disabled=not fal_key_configured,
        ):
            with st.spinner(t["status_generating_audio"]):
                try:
                    audio_bytes, audio_mime, audio_extension = generate_audio_with_fal(data)
                    safe_title = re.sub(r"[^\w-]+", "_", data["title"], flags=re.UNICODE).strip("_-")[:60]
                    if not safe_title:
                        safe_title = "knowledge_song"
                    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                    filename = f"{safe_title}_{timestamp}{audio_extension}"
                    os.makedirs("saved_songs", exist_ok=True)
                    generated_path = os.path.join("saved_songs", filename)
                    with open(generated_path, "wb") as audio_file:
                        audio_file.write(audio_bytes)
                    st.session_state["generated_audio_path"] = generated_path
                    st.session_state["generated_audio_mime"] = audio_mime
                    st.success(t["audio_ready"])
                except Exception as exc:
                    error_detail = str(exc)
                    st.error(f"{t['audio_error']} {error_detail}")
                    lower_error = error_detail.lower()
                    if "fal_key" in lower_error or "401" in lower_error or "403" in lower_error:
                        st.info(t["fal_key_hint"])
                    elif "credit" in lower_error or "402" in lower_error or "payment" in lower_error:
                        st.info(t["fal_billing_hint"])

    with col_s2:
        st.markdown(f"#### {t['lyrics_label']}")
        st.code(data["lyrics"], language="text")

    generated_path = st.session_state.get("generated_audio_path")
    if generated_path and os.path.isfile(generated_path):
        with open(generated_path, "rb") as generated_file:
            generated_audio = generated_file.read()
        generated_mime = st.session_state.get("generated_audio_mime") or (
            "audio/wav" if generated_path.lower().endswith(".wav") else "audio/mpeg"
        )
        st.audio(generated_audio, format=generated_mime)
        st.download_button(
            label=f"{t['download_label']} {os.path.basename(generated_path)}",
            data=generated_audio,
            file_name=os.path.basename(generated_path),
            mime=generated_mime,
            use_container_width=True,
        )

# --- 11. ステップ3：Webプレーヤーと曲の保存 ---
st.markdown("---")
st.subheader(t["step3_title"])

os.makedirs("saved_songs", exist_ok=True)

uploaded_mp3 = st.file_uploader(
    t["upload_mp3_label"],
    type=["mp3", "wav"]
)

if uploaded_mp3 is not None:
    save_path = os.path.join("saved_songs", uploaded_mp3.name)
    with open(save_path, "wb") as f:
        f.write(uploaded_mp3.getbuffer())
    st.success(f"🎵 {t['playing_label']} **{uploaded_mp3.name}**")
    upload_mime = "audio/wav" if uploaded_mp3.name.lower().endswith(".wav") else "audio/mpeg"
    st.audio(uploaded_mp3, format=upload_mime)

saved_files = sorted(
    [f for f in os.listdir("saved_songs") if f.endswith((".mp3", ".wav"))],
    reverse=True
)

if saved_files:
    selected_song = st.selectbox(t["saved_songs_label"], saved_files)
    song_full_path = os.path.join("saved_songs", selected_song)
    with open(song_full_path, "rb") as sf:
        song_bytes = sf.read()
    song_mime = "audio/wav" if selected_song.lower().endswith(".wav") else "audio/mpeg"
    st.audio(song_bytes, format=song_mime)
    st.download_button(
        label=f"{t['download_label']} {selected_song}",
        data=song_bytes,
        file_name=selected_song,
        mime=song_mime,
        use_container_width=True
    )
