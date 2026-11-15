import base64
import json
import time
import csv
import os
import re
import requests
import socket
from datetime import datetime
from io import BytesIO
from urllib.parse import urljoin, urlparse

import streamlit as st
from bs4 import BeautifulSoup
from pypdf import PdfReader
import docx
from PIL import Image, ImageOps
from google import genai
from lyric_video import THEMES, audio_duration, estimate_cues, render_lyric_video, scene_timeline, validate_cues
from video_background import generate_background

GEMINI_MODELS = ("gemini-4-hydrogen", "gemini-3.5-flash-lite")
MORE_GENRES = {
    "J-Rock / Anime Rock": ("Jロック／アニメロック", "J-Rock / Rock anime"),
    "K-Pop / Dance Pop": ("K-Pop／ダンスポップ", "K-Pop / Dance Pop"),
    "V-Pop": ("V-Pop（ベトナムのポップス）", "V-Pop"),
    "Pop Rock": ("ポップロック", "Pop Rock"),
    "Indie Rock": ("インディーロック", "Indie Rock"),
    "Pop Punk": ("ポップパンク", "Pop Punk"),
    "Heavy Metal": ("ヘヴィメタル", "Heavy Metal"),
    "R&B / Soul": ("R&B／ソウル", "R&B / Soul"),
    "Trap / Drill": ("トラップ／ドリル", "Trap / Drill"),
    "Jazz / Swing": ("ジャズ／スウィング", "Jazz / Swing"),
    "Blues": ("ブルース", "Blues"),
    "Funk / Disco": ("ファンク／ディスコ", "Funk / Disco"),
    "House / Techno": ("ハウス／テクノ", "House / Techno"),
    "Drum & Bass": ("ドラムンベース", "Drum & Bass"),
    "Synthwave / City Pop": ("シンセウェイヴ／シティポップ", "Synthwave / City Pop"),
    "Reggae / Dub": ("レゲエ／ダブ", "Reggae / Dub"),
    "Bolero": ("ボレロ", "Bolero"),
    "Cinematic / Orchestral": ("映画音楽／オーケストラ", "Nhạc phim / Giao hưởng"),
}
MAX_VIDEO_SCENES = 3

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
        "login_demo_desc": "デモモードです。入力済みのデモ用メールアドレスのまま進めます。Google認証は行われません。",
        "login_email_label": "デモ用メールアドレス:",
        "btn_demo_login": "デモモードで続ける",
        "demo_sample_button": "🧪 サンプルで試す（API不要）",
        "demo_sample_caption": "これは要約・歌詞の表示例です。音声は生成せず、APIも呼び出していません。",
        "api_keys_title": "🔑 APIキー（このセッションのみ）",
        "gemini_api_key_label": "Gemini APIキー（要約・歌詞用）",
        "gemini_model_used": "使用したモデル：{model}",
        "fal_api_key_label": "fal.ai APIキー（音楽生成用）",
        "api_keys_privacy": "キーはアプリサーバーのセッションメモリで使い、ファイルには保存しません。各サービスにはアプリサーバー経由で送信されます。信頼できるアプリでのみ入力してください。利用料はキーの所有者に請求されます。",
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
        "file_prompt": "複数のドキュメントをアップロード (PDF, DOCX, TXT)",
        "img_prompt": "ノートや教科書の画像を複数アップロード (PNG, JPG)",
        "image_read_error": "画像を読み込めませんでした: {name}",
        "url_prompt": "学習ページのURLを貼り付けてください:",
        "prompt_section": "🎛️ 曲のスタイルとプロンプト設定 (Prompt)",
        "genre_label": "音楽ジャンル:",
        "custom_genre": "ジャンルを自由入力",
        "custom_genre_required": "音楽ジャンルを入力してください。",
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
        "btn_generate_audio": "🎵 曲を生成",
        "btn_generate_video": "🎬 歌詞動画を作成",
        "video_settings": "歌詞動画の設定",
        "video_timing": "歌詞と表示時刻を調整",
        "video_background_mode": "背景の種類",
        "video_background_modes": {"simple": "テーマ・画像", "ai": "AI動画 · LTX-2.5（無料枠）"},
        "video_prompt": "曲に合わせた映像の指示",
        "video_prompt_example": "Verse: 暗い教室で論理回路がゆっくり光る\nChorus: 青い光が回路全体を走る",
        "video_ai_note": "Verse・Chorusなど区間ごとに、最大3種類の短い背景映像を指定できます。映像は音声と別に生成し、各区間で繰り返します。指示と曲のジャンル・雰囲気は共有GPUを使う公開のHugging Face Spaceに送信されます。",
        "video_ai_limit": "AI背景を作れるのは最初の3種類です。残りにはテーマ背景を使用しました。",
        "video_ai_unavailable": "一部のAI背景を作成できなかったため、その区間にはテーマ背景を使用しました。",
        "video_scene_unmatched": "歌詞の区間名と一致する映像指示がありませんでした。Verse・Chorusなどの区間名を確認してください。",
        "video_waveform": "音に反応する波形を表示",
        "video_show_lyrics": "動画に歌詞を表示",
        "video_section": "歌詞の区間",
        "video_ai_rendering": "AIで背景動画を生成しています…",
        "video_background": "背景画像（任意）",
        "video_theme": "テーマカラー",
        "video_themes": {"night": "ネイビー", "plum": "プラム", "forest": "フォレスト"},
        "video_reuse": "この曲の音声を使います。曲の生成料金は追加されません。",
        "video_timing_note": "表示時刻は目安です。秒数や歌詞を調整し、もう一度「歌詞動画を作成」を押すと反映されます。",
        "video_start": "表示開始（秒）",
        "video_caption": "表示する歌詞",
        "video_rendering": "歌詞動画を作成しています…",
        "video_error": "歌詞動画を作成できませんでした",
        "video_preview": "歌詞動画",
        "video_download": "⬇️ MP4をダウンロード",
        "status_generating_audio": "選択したサービスで曲を生成中です...",
        "audio_ready": "✅ 曲を生成して保存しました。",
        "audio_error": "曲を生成できませんでした:",
        "audio_fallback_hint": "保存済みの曲は、下のライブラリから再生できます。",
        "audio_provider_label": "🎛️ 音楽生成サービスを選択",
        "audio_provider_options": {
            "fal_ace_step": "ACE-Step（fal.ai・低価格）",
            "fal_minimax": "MiniMax Music 3.0（fal.ai）",
            "fal_mureka_v8": "Mureka V8（fal.ai・歌詞を指定）",
            "fal_lyria_35": "Google Lyria 3.5（fal.ai・フル曲）",
            "local_acestep": "ACE-Step（自分のPC・ローカルAPI）"
        },
        "audio_provider_notes": {
            "fal_ace_step": "長所：fal.aiで手軽に使え、現在約$0.0002/秒（60秒で約$0.012）。短所：歌声の明瞭さや歌詞の再現は曲によって差があります。FAL_KEYとクレジットが必要で、他のfal.aiモデルと残高を共有します。",
            "fal_minimax": "長所：歌詞とスタイルを個別に指定でき、生成は最長60秒。料金は約$0.002/秒（60秒で約$0.12）。短所：長い歌詞は最後まで歌われないことがあり、ベトナム語の発音は未確認です。FAL_KEYとクレジットが必要です。",
            "fal_mureka_v8": "長所：歌詞を専用入力欄で指定でき、最大5,000文字。短所：ベトナム語は公式対応言語一覧にありません。歌詞を入力した場合は現在$0.045/曲です。FAL_KEYとクレジットが必要で、共有アプリでは設定アカウントに請求されます。",
            "fal_lyria_35": "長所：数分の構成付きフル曲を生成し、日本語に対応。短所：歌詞をプロンプトに含める方式なので、歌詞が完全一致する保証はありません。ベトナム語は公式対応言語一覧にありません。現在$0.10/回。FAL_KEYとクレジットが必要で、共有アプリでは設定アカウントに請求されます。",
            "local_acestep": "長所：APIの従量料金なしで自分のPC上に生成できます。短所：ACE-Step 1.5 APIサーバーの導入が必要で、目安はVRAM 4GB以上（LM使用時6GB以上）と約10GBの空き容量です。PC性能、電気代、設定作業が必要で、歌声の明瞭さは保証されません。クラウドアプリから利用する場合は別途公開接続が必要です。"
        },
        "audio_quota_note": "タイトル、音楽スタイル、歌詞を音楽生成サービスに送信します。元の学習資料は送信しません。料金・待ち時間・必要な機器を確認して選んでください。",
        "music_copyright_warning": "著作権の注意：AIが作った曲でも、既存曲のメロディーや歌詞に似ることがあります。入力には利用できる歌詞を使い、公開・商用利用の前に曲を聴いて利用条件を確認してください。既存曲によく似ている場合は、権利を確認するまで公開を控えてください。",
        "music_model_terms_link": "モデルの公式ページ",
        "music_fal_terms_link": "fal.aiの利用規約",
        "vietnamese_vocal_warning": "⚠️ ベトナム語の歌詞は、モデルや歌詞によって発音が不明瞭になる場合があります。聞き取りやすさを重視する場合は、別のサービスも試してください。",
        "fal_key_hint": "左側のAPIキー入力欄に自分のキーを入力してください。ローカル版では `.streamlit/secrets.toml` にも設定できます。fal.aiの利用料はキーの所有者に請求されます。",
        "fal_key_missing": "左側のAPIキー入力欄にfal.aiのキーを入力してください。",
        "fal_billing_hint": "fal.aiのアカウントに利用可能なクレジットがあるか確認してください。",
        "local_api_url_hint": "ACE-Step APIサーバーを起動してから選択してください。接続先は `.streamlit/secrets.toml` の `ACESTEP_LOCAL_URL` で設定できます（初期値: `http://127.0.0.1:8001`）。認証を有効にしたサーバーでは `ACESTEP_LOCAL_API_KEY` も設定してください。",
        "local_api_unavailable": "ローカルのACE-Step APIサーバーに接続できません。先にサーバーを起動し、設定したURLとポートを確認してください。",
        "minimax_lyrics_limit": "このアプリからMiniMax Music 3.0に送れる歌詞は3,500文字までです。歌詞を短くするか、別のサービスを選んでください。",
        "mureka_lyrics_limit": "Mureka V8は歌詞が5,000文字までです。歌詞を短くしてください。",
        "lyria_lyrics_limit": "Lyria 3.5に送る歌詞は5,000文字までにしてください。",
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
        "gemini_key_missing": "⚠️ 左側の「APIキー」にGemini APIキーを入力してください。ローカル版では secrets.toml にも設定できます。",
        "generation_success": "✅ {model} で生成しました。",
        "gemini_empty_response": "テキストが返されませんでした。",
        "models_failed": "{count} 個のモデルを試しましたが、すべて失敗しました（{models}）。最初のエラー: {detail}",
        "generation_error": "❌ 生成エラー：",
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
        "login_demo_desc": "Chế độ demo: email dùng thử đã được điền sẵn. Bấm nút để tiếp tục; hệ thống không xác thực tài khoản Google.",
        "login_email_label": "Email dùng cho demo:",
        "btn_demo_login": "Vào thử chế độ demo",
        "demo_sample_button": "🧪 Thử bằng ví dụ (không cần API)",
        "demo_sample_caption": "Đây là ví dụ tóm tắt và lời bài hát; ứng dụng không tạo audio và không gọi API.",
        "api_keys_title": "🔑 API key (chỉ trong phiên này)",
        "gemini_api_key_label": "Gemini API key (tóm tắt và lời bài hát)",
        "gemini_model_used": "Model đã dùng · {model}",
        "fal_api_key_label": "fal.ai API key (tạo nhạc)",
        "api_keys_privacy": "Key được dùng trong bộ nhớ phiên của máy chủ ứng dụng, không ghi vào file; key được gửi qua máy chủ đến dịch vụ tương ứng. Chỉ nhập key trên ứng dụng bạn tin tưởng. Phí sử dụng do chủ key thanh toán.",
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
        "file_prompt": "Kéo thả một hoặc nhiều tài liệu vào đây (PDF, DOCX, TXT)",
        "img_prompt": "Kéo thả một hoặc nhiều ảnh chụp trang sách/vở vào đây (PNG, JPG)",
        "image_read_error": "Không đọc được ảnh: {name}",
        "url_prompt": "Dán đường link (URL) trang web bài học:",
        "prompt_section": "🎛️ Tùy chỉnh bài hát theo ý muốn (Prompt)",
        "genre_label": "Thể loại nhạc:",
        "custom_genre": "Tự nhập thể loại",
        "custom_genre_required": "Hãy nhập thể loại nhạc.",
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
        "btn_generate_audio": "🎵 Tạo nhạc",
        "btn_generate_video": "🎬 Tạo video lời bài hát",
        "video_settings": "Cài đặt video lời bài hát",
        "video_timing": "Chỉnh lời và thời điểm hiển thị",
        "video_background_mode": "Kiểu nền",
        "video_background_modes": {"simple": "Tông màu hoặc ảnh", "ai": "Video AI · LTX-2.5 (hạn mức miễn phí)"},
        "video_prompt": "Chỉ dẫn video theo bài hát",
        "video_prompt_example": "Verse: lớp học tối, mạch logic sáng dần\nChorus: ánh đèn xanh chạy qua toàn bộ mạch",
        "video_ai_note": "Ghi chỉ dẫn cho cả bài hoặc theo từng đoạn như Verse và Chorus. LTX tạo tối đa 3 cảnh nền ngắn độc lập với audio, rồi app lặp cảnh theo đoạn. Chỉ dẫn, thể loại và không khí bài hát được gửi đến một Hugging Face Space công khai có hạn mức GPU miễn phí.",
        "video_ai_limit": "App chỉ tạo 3 cảnh AI đầu tiên. Các cảnh còn lại dùng nền theo tông màu đã chọn.",
        "video_ai_unavailable": "Một số cảnh AI không tạo được. Các đoạn đó dùng nền theo tông màu đã chọn.",
        "video_scene_unmatched": "Chỉ dẫn chưa khớp với đoạn nào trong lời bài hát. Kiểm tra lại tên đoạn, ví dụ Verse hoặc Chorus.",
        "video_waveform": "Hiện sóng âm chạy theo nhạc",
        "video_show_lyrics": "Hiện lời bài hát trên video",
        "video_section": "Đoạn lời",
        "video_ai_rendering": "AI đang tạo cảnh nền…",
        "video_background": "Ảnh nền (tùy chọn)",
        "video_theme": "Tông màu",
        "video_themes": {"night": "Xanh đêm", "plum": "Tím mận", "forest": "Xanh rừng"},
        "video_reuse": "Video dùng lại bài đã tạo, không phát sinh thêm phí tạo nhạc.",
        "video_timing_note": "Mốc thời gian là ước tính. Sửa số giây hoặc câu chữ rồi bấm Tạo video lời bài hát để áp dụng.",
        "video_start": "Bắt đầu (giây)",
        "video_caption": "Lời hiện trên video",
        "video_rendering": "Đang dựng video lời bài hát…",
        "video_error": "Không dựng được video lời bài hát",
        "video_preview": "Video lời bài hát",
        "video_download": "⬇️ Tải MP4",
        "status_generating_audio": "Đang tạo bài hát bằng dịch vụ đã chọn...",
        "audio_ready": "✅ Đã tạo và lưu bài hát.",
        "audio_error": "Không tạo được bài hát:",
        "audio_fallback_hint": "Bạn vẫn có thể phát các bài đã lưu trong thư viện bên dưới.",
        "audio_provider_label": "🎛️ Chọn dịch vụ tạo nhạc",
        "audio_provider_options": {
            "fal_ace_step": "ACE-Step (fal.ai · chi phí thấp)",
            "fal_minimax": "MiniMax Music 3.0 (fal.ai)",
            "fal_mureka_v8": "Mureka V8 (fal.ai · nhập lời riêng)",
            "fal_lyria_35": "Google Lyria 3.5 (fal.ai · bài hoàn chỉnh)",
            "local_acestep": "ACE-Step (máy cá nhân · Local API)"
        },
        "audio_provider_notes": {
            "fal_ace_step": "Ưu điểm: dễ dùng qua fal.ai, giá hiện khoảng $0.0002/giây (60 giây khoảng $0.012). Hạn chế: độ rõ của giọng hát và mức giữ nguyên lời có thể khác nhau giữa các bài. Cần FAL_KEY và credit; dùng chung số dư với các model fal.ai khác.",
            "fal_minimax": "Ưu điểm: có ô nhập riêng cho lời và phong cách, tạo tối đa 60 giây. Giá khoảng $0.002/giây ($0.12 nếu đủ 60 giây). Hạn chế: lời dài có thể không được hát hết và độ rõ tiếng Việt chưa được kiểm chứng. Cần FAL_KEY và credit.",
            "fal_mureka_v8": "Ưu điểm: có ô nhập lời riêng, hỗ trợ tối đa 5.000 ký tự. Hạn chế: tiếng Việt không có trong danh sách ngôn ngữ được công bố, nên chưa đảm bảo phát âm. Khi gửi lời, giá hiện tại là $0.045/bài. Cần FAL_KEY và credit; nếu dùng app chung, phí tính vào tài khoản đã cấu hình.",
            "fal_lyria_35": "Ưu điểm: tạo bài hoàn chỉnh dài vài phút, có hỗ trợ tiếng Nhật. Hạn chế: app gửi lời trong prompt nên model có thể sửa hoặc bỏ sót lời; tiếng Việt không có trong danh sách ngôn ngữ được công bố. Giá hiện tại là $0.10/lần. Cần FAL_KEY và credit; app chung tính phí vào tài khoản đã cấu hình.",
            "local_acestep": "Ưu điểm: không tính phí API theo từng lần tạo và có thể chạy trên máy cá nhân. Hạn chế: phải cài ACE-Step 1.5 API server; tham khảo VRAM từ 4GB (6GB nếu dùng LM), khoảng 10GB dung lượng trống. Cần máy đủ mạnh, điện và thời gian thiết lập; chất lượng vocal không được bảo đảm. Nếu app chạy trên cloud, 127.0.0.1 là máy chủ cloud, không phải máy của người dùng.",
        },
        "audio_quota_note": "Ứng dụng gửi tiêu đề, phong cách nhạc và lời bài hát để tạo audio; không gửi tài liệu học gốc đến dịch vụ tạo nhạc. Hãy chọn theo chi phí, thời gian chờ và thiết bị của bạn.",
        "music_copyright_warning": "Lưu ý bản quyền: Nhạc AI có thể giống giai điệu hoặc lời của bài có sẵn. Hãy dùng lời bạn có quyền sử dụng, nghe lại bản tạo ra và xem điều khoản của model trước khi đăng hoặc dùng thương mại. Nếu bài quá giống một bài có sẵn, hãy kiểm tra quyền sử dụng trước khi đăng.",
        "music_model_terms_link": "Trang chính thức của model",
        "music_fal_terms_link": "Điều khoản của fal.ai",
        "vietnamese_vocal_warning": "⚠️ Một số model có thể hát lời tiếng Việt không rõ; kết quả tùy model và lời bài hát. Nếu cần nghe rõ, hãy thử dịch vụ khác và kiểm tra lời trước khi sử dụng.",
        "fal_key_hint": "Hãy nhập key cá nhân ở mục API key bên trái; bản chạy cục bộ cũng có thể đặt trong `.streamlit/secrets.toml`. Phí fal.ai tính cho chủ sở hữu key.",
        "fal_key_missing": "Hãy nhập key fal.ai cá nhân ở mục API key bên trái.",
        "fal_billing_hint": "Kiểm tra tài khoản fal.ai còn credit khả dụng không.",
        "local_api_url_hint": "Hãy khởi chạy ACE-Step API server trước. Có thể cấu hình địa chỉ trong `.streamlit/secrets.toml` bằng `ACESTEP_LOCAL_URL` (mặc định `http://127.0.0.1:8001`). Nếu server bật xác thực, hãy thêm `ACESTEP_LOCAL_API_KEY`.",
        "local_api_unavailable": "Không kết nối được với ACE-Step API server cục bộ. Hãy khởi chạy server trước và kiểm tra URL/cổng đã cấu hình.",
        "minimax_lyrics_limit": "App gửi tối đa 3.500 ký tự lời sang MiniMax Music 3.0. Hãy rút ngắn lời hoặc chọn dịch vụ khác.",
        "mureka_lyrics_limit": "Mureka V8 giới hạn lời bài hát ở 5.000 ký tự. Hãy rút ngắn lời.",
        "lyria_lyrics_limit": "Lời gửi cho Lyria 3.5 cần tối đa 5.000 ký tự.",
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
        "gemini_key_missing": "⚠️ Hãy nhập Gemini API key ở mục API key bên trái; bản chạy cục bộ cũng có thể đặt trong secrets.toml.",
        "generation_success": "✅ Đã tạo thành công bằng model: {model}",
        "gemini_empty_response": "Model không trả về văn bản.",
        "models_failed": "Đã thử {count} model nhưng đều thất bại ({models}). Lỗi đầu tiên: {detail}",
        "generation_error": "❌ Lỗi tạo nội dung:",
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
        "login_demo_desc": "Demo mode: a sample email is already filled in. Click the button to continue; Google identity is not verified.",
        "login_email_label": "Demo email address:",
        "btn_demo_login": "Continue in demo mode",
        "demo_sample_button": "🧪 Try the sample (no API needed)",
        "demo_sample_caption": "This is a sample summary and lyric output. It does not create audio or call an API.",
        "api_keys_title": "🔑 API keys (this session only)",
        "gemini_api_key_label": "Gemini API key (summary and lyrics)",
        "gemini_model_used": "Model used · {model}",
        "fal_api_key_label": "fal.ai API key (music generation)",
        "api_keys_privacy": "Keys are used in this app server's session memory, not written to files, and sent through the server to the selected service. Enter keys only in an app you trust. Usage is billed to the key owner.",
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
        "file_prompt": "Drop one or more documents here (PDF, DOCX, TXT)",
        "img_prompt": "Upload one or more study images (PNG, JPG)",
        "image_read_error": "Could not read image: {name}",
        "url_prompt": "Paste the website URL:",
        "prompt_section": "🎛️ Customize Song Style (Prompt)",
        "genre_label": "Music Genre:",
        "custom_genre": "Enter your own genre",
        "custom_genre_required": "Enter a music genre.",
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
        "btn_generate_audio": "🎵 Generate music",
        "btn_generate_video": "🎬 Create lyric video",
        "video_settings": "Lyric video settings",
        "video_timing": "Edit lyrics and timing",
        "video_background_mode": "Background type",
        "video_background_modes": {"simple": "Theme or image", "ai": "AI video · LTX-2.5 (free quota)"},
        "video_prompt": "Video direction for this song",
        "video_prompt_example": "Verse: a dark classroom with a circuit slowly lighting up\nChorus: blue light sweeps across the circuit",
        "video_ai_note": "Write directions for the whole song or use section names such as Verse and Chorus. Up to three short background scenes are generated separately from the audio and loop within their sections. The directions, genre and mood are sent to a public Hugging Face Space with a free GPU quota.",
        "video_ai_limit": "The first three AI scenes were used. Other sections use the selected color theme.",
        "video_ai_unavailable": "Some AI scenes could not be generated. Those sections use the selected color theme.",
        "video_scene_unmatched": "No scene directions matched the lyrics. Check the section names, such as Verse or Chorus.",
        "video_waveform": "Show an audio-reactive waveform",
        "video_show_lyrics": "Show lyrics on the video",
        "video_section": "Lyric section",
        "video_ai_rendering": "Generating the background clip…",
        "video_background": "Background image (optional)",
        "video_theme": "Color theme",
        "video_themes": {"night": "Midnight", "plum": "Plum", "forest": "Forest"},
        "video_reuse": "The video uses the existing song, with no additional music generation fee.",
        "video_timing_note": "Timing is estimated. Edit the seconds or lyrics and click Create lyric video again to apply changes.",
        "video_start": "Start time (seconds)",
        "video_caption": "On-screen lyrics",
        "video_rendering": "Rendering the lyric video…",
        "video_error": "Could not render the lyric video",
        "video_preview": "Lyric video",
        "video_download": "⬇️ Download MP4",
        "status_generating_audio": "Generating with the selected service...",
        "audio_ready": "✅ Song generated and saved.",
        "audio_error": "Could not generate the song:",
        "audio_fallback_hint": "You can still play saved songs from the library below.",
        "audio_provider_label": "🎛️ Choose a music service",
        "audio_provider_options": {
            "fal_ace_step": "ACE-Step (fal.ai · low cost)",
            "fal_minimax": "MiniMax Music 3.0 (fal.ai)",
            "fal_mureka_v8": "Mureka V8 (fal.ai · custom lyrics)",
            "fal_lyria_35": "Google Lyria 3.5 (fal.ai · full song)",
            "local_acestep": "ACE-Step (your computer · Local API)"
        },
        "audio_provider_notes": {
            "fal_ace_step": "Pros: easy to access through fal.ai and currently about $0.0002/sec ($0.012 for 60 sec). Cons: vocal clarity and lyric fidelity can vary by song. Requires FAL_KEY and credits shared with the other fal.ai models.",
            "fal_minimax": "Pros: separate lyrics and style inputs, with up to 60 seconds of audio. About $0.002/second ($0.12 for 60 seconds). Cons: long lyrics may be cut short, and Vietnamese pronunciation has yet to be verified. Requires FAL_KEY and credits.",
            "fal_mureka_v8": "Pros: separate lyrics input, up to 5,000 characters. Cons: Vietnamese is not in the published language list, so pronunciation is not assured. Current price with supplied lyrics is $0.045/song. Requires FAL_KEY and fal.ai credits; shared apps charge the configured account.",
            "fal_lyria_35": "Pros: generates structured full songs up to a few minutes and supports Japanese. Cons: lyrics are embedded in the prompt, so exact wording may change; Vietnamese is not in the published language list. Current price is $0.10/generation. Requires FAL_KEY and credits; shared apps charge the configured account.",
            "local_acestep": "Pros: no per-generation API fee and can run on your own computer. Cons: requires a separate ACE-Step 1.5 API server; reference hardware is at least 4GB VRAM (6GB with LM) and about 10GB free disk space. Hardware, electricity, setup time, and vocal quality are still factors. In a cloud-hosted app, 127.0.0.1 points to the cloud server, not your computer.",
        },
        "audio_quota_note": "The music service receives the generated title, style, and lyrics; the original study material is not sent to it. Choose based on cost, waiting time, and available hardware.",
        "music_copyright_warning": "Copyright notice: AI music can resemble existing melodies or lyrics. Use lyrics you have the right to use, listen to the generated track, and check the model's terms before publishing or commercial use. If it closely resembles an existing song, check the rights before sharing it.",
        "music_model_terms_link": "Official model page",
        "music_fal_terms_link": "fal.ai terms of service",
        "vietnamese_vocal_warning": "⚠️ Vietnamese lyrics may be hard to understand depending on the model and wording. If clear pronunciation matters, try another service and review the lyrics before using the song.",
        "fal_key_hint": "Enter your own key in API keys in the sidebar; for a local app, you can also set it in `.streamlit/secrets.toml`. fal.ai usage is billed to the key owner.",
        "fal_key_missing": "Enter your own fal.ai key in API keys in the sidebar.",
        "fal_billing_hint": "Check that your fal.ai account has available credits.",
        "local_api_url_hint": "Start the ACE-Step API server first. Set its address in `.streamlit/secrets.toml` as `ACESTEP_LOCAL_URL` (default: `http://127.0.0.1:8001`). If the server requires authentication, also set `ACESTEP_LOCAL_API_KEY`.",
        "local_api_unavailable": "The local ACE-Step API server is not reachable. Start it first and check the configured URL and port.",
        "minimax_lyrics_limit": "The app sends up to 3,500 lyric characters to MiniMax Music 3.0. Shorten the lyrics or choose another service.",
        "mureka_lyrics_limit": "Mureka V8 supports up to 5,000 lyric characters. Shorten the lyrics.",
        "lyria_lyrics_limit": "Lyrics sent to Lyria 3.5 must be 5,000 characters or fewer.",
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
        "gemini_key_missing": "⚠️ Enter a Gemini API key in API keys in the sidebar; for a local app, you can also set it in secrets.toml.",
        "generation_success": "✅ Generated successfully with model: {model}",
        "gemini_empty_response": "The model returned no text.",
        "models_failed": "All {count} models failed ({models}). First error: {detail}",
        "generation_error": "❌ Generation error:",
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


def get_runtime_key(key_name):
    """Prefer a per-session key, then fall back to the configured secret."""
    session_key_names = {
        "GEMINI_API_KEY": "session_gemini_api_key",
        "FAL_KEY": "session_fal_api_key",
    }
    session_key = st.session_state.get(session_key_names.get(key_name, ""), "")
    if session_key and str(session_key).strip():
        return str(session_key).strip()
    return get_secret_safe(key_name)


def reset_generated_media():
    st.session_state["generated_audio_path"] = None
    st.session_state.pop("generated_audio_mime", None)
    st.session_state.pop("video_timing", None)
    st.session_state.pop("generated_video", None)
    st.session_state.pop("video_ai_clips", None)
    st.session_state.pop("video_scene_notices", None)


def get_demo_song(language):
    """Return a clearly labeled, prewritten example that works without API keys."""
    examples = {
        "JP": {
            "title": "論理ゲート・リズム",
            "summary": "ANDは両方が1のとき1、ORは少なくとも片方が1なら1、XORは入力が異なるとき1、NOTは入力を反転します。",
            "tags": "J-Pop, Anime Opening, 160 BPM, Clear female vocal, energetic, educational",
            "lyrics": "[Verse]\nANDは二つ そろったら1\nORはどちらか 1なら1\nXORは違えば 光る1\nNOTでひっくり返そう\n\n[Chorus]\nAND OR XOR NOT\n0と1を組み合わせ\n真理値表をたどれば\n論理のルールが見えてくる",
        },
        "VI": {
            "title": "Nhịp điệu cổng logic",
            "summary": "AND cho kết quả 1 khi cả hai đầu vào đều là 1; OR cho 1 khi có ít nhất một đầu vào là 1; XOR cho 1 khi hai đầu vào khác nhau; NOT đảo đầu vào.",
            "tags": "J-Pop, Anime Opening, 160 BPM, Clear female vocal, energetic, educational",
            "lyrics": "[Verse]\nAND cần hai số một cùng lên\nOR chỉ cần một là sáng đèn\nXOR khác nhau thì bật tín hiệu\nNOT đảo ngược, nhớ thật lâu\n\n[Chorus]\nAND, OR, XOR, NOT\nGhép số không với số một\nTheo bảng chân trị từng dòng\nQuy tắc logic nằm trong lòng",
        },
        "EN": {
            "title": "Logic Gate Rhythm",
            "summary": "AND is 1 only when both inputs are 1. OR is 1 when either input is 1. XOR is 1 when inputs differ. NOT reverses its input.",
            "tags": "J-Pop, Anime Opening, 160 BPM, Clear female vocal, energetic, educational",
            "lyrics": "[Verse]\nAND needs two ones to light the way\nOR needs one, then it's okay\nXOR shines when the inputs disagree\nNOT flips the bit for you and me\n\n[Chorus]\nAND, OR, XOR, NOT\nZeros and ones connect the dots\nFollow the truth table through\nLogic starts to make sense to you",
        },
    }
    return {
        **examples.get(language, examples["JP"]),
        "genre": "J-Pop / Anime Opening",
        "mood": "Upbeat & Energetic",
        "is_demo_sample": True,
    }


FAL_QUEUE_BASE_URL = "https://queue.fal.run/"
MINIMAX_LYRICS_LIMIT = 3500
FAL_MUSIC_ENDPOINTS = {
    "fal_ace_step": "fal-ai/ace-step",
    "fal_minimax": "minimax/music-3",
    "fal_mureka_v8": "mureka/v8/generate/song",
    "fal_lyria_35": "google/lyria-3.5",
}


def fal_response_error(response):
    """Return a concise fal.ai error without exposing request headers or API keys."""
    detail = ""
    try:
        body = response.json()
        if isinstance(body, dict):
            detail = body.get("detail") or body.get("message") or body.get("error") or ""
            if isinstance(detail, (dict, list)):
                detail = json.dumps(detail, ensure_ascii=False)
        elif body:
            detail = str(body)
    except ValueError:
        detail = response.text.strip()

    detail = re.sub(r"\s+", " ", str(detail)).strip()[:500]
    if not detail:
        detail = "No additional error details were returned."
    return f"fal.ai returned HTTP {response.status_code}: {detail}"


def generate_audio_with_fal(song_data, model="fal_ace_step", duration=60):
    """Generate a song with a fal.ai model and return bytes, MIME type, and extension."""
    api_key = get_runtime_key("FAL_KEY")
    if not api_key or not str(api_key).strip():
        raise RuntimeError("FAL_KEY is missing from Streamlit secrets.")

    endpoint = FAL_MUSIC_ENDPOINTS.get(model)
    if not endpoint:
        raise RuntimeError("The selected fal.ai music model is not supported.")

    headers = {
        "Authorization": f"Key {str(api_key).strip()}",
        "Content-Type": "application/json",
    }
    music_prompt = f"{song_data.get('title', '')}; {song_data['tags']}".strip("; ")
    lyrics = str(song_data["lyrics"])
    if model == "fal_minimax":
        if len(lyrics) > MINIMAX_LYRICS_LIMIT:
            raise RuntimeError(f"The app sends up to {MINIMAX_LYRICS_LIMIT:,} lyric characters to MiniMax Music 3.0.")
        # MiniMax drops text on the same line as a section tag.
        minimax_lyrics = re.sub(
            r"(?im)^[ \t]*\[(intro|verse|pre-chorus|chorus|post-chorus|bridge|instrumental|solo|outro)(?: +[0-9]+)?\][ \t]*(?:\r?\n)?",
            lambda match: f"[{match[1].lower()}]\n",
            lyrics,
        )
        payload = {
            "prompt": music_prompt[:2000],
            "lyrics": minimax_lyrics,
            "duration": duration,
            "enable_safety_checker": True,
        }
    elif model == "fal_mureka_v8":
        if len(lyrics) > 5000:
            raise RuntimeError("Mureka V8 supports up to 5,000 lyric characters.")
        payload = {
            "prompt": music_prompt[:1024],
            "lyrics": lyrics,
            "enable_safety_checker": True,
        }
    elif model == "fal_lyria_35":
        if len(lyrics) > 5000:
            raise RuntimeError("Lyria 3.5 supports lyrics up to 5,000 characters in this app.")
        prompt = (
            "Create a complete, structured song in the same language as the lyrics below. "
            "Use them as the exact words to sing. "
            "Preserve the wording and line order; do not translate, omit, or add lyric lines. "
            f"Title: {song_data.get('title', '')}. Style: {song_data['tags']}.\n\nLyrics:\n{lyrics}"
        )
        payload = {"prompt": prompt, "enable_safety_checker": True}
    else:
        payload = {
            "tags": music_prompt[:500],
            "lyrics": str(song_data["lyrics"])[:6000],
            "duration": duration,
            "number_of_steps": 27,
        }

    submit_response = requests.post(
        urljoin(FAL_QUEUE_BASE_URL, endpoint),
        headers=headers,
        json=payload,
        timeout=(15, 120),
    )
    if submit_response.status_code == 401:
        raise RuntimeError(f"Invalid or expired FAL_KEY. {fal_response_error(submit_response)}")
    if submit_response.status_code == 403:
        raise RuntimeError(f"fal.ai denied this key or model permission. {fal_response_error(submit_response)}")
    if submit_response.status_code == 402:
        raise RuntimeError(f"fal.ai account has no available credits. {fal_response_error(submit_response)}")
    if not submit_response.ok:
        raise RuntimeError(fal_response_error(submit_response))
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
        if not status_response.ok:
            raise RuntimeError(fal_response_error(status_response))
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
    if not result_response.ok:
        raise RuntimeError(fal_response_error(result_response))
    result_response.raise_for_status()
    result = result_response.json()
    audio_item = result.get("audio") or {}
    if isinstance(audio_item, str):
        audio_url = audio_item
        audio_item = {}
    else:
        audio_url = audio_item.get("url") if isinstance(audio_item, dict) else None
    if not audio_url:
        raise RuntimeError("fal.ai finished but did not return an audio file.")

    audio_response = requests.get(audio_url, timeout=(15, 120))
    audio_response.raise_for_status()
    if not audio_response.content:
        raise RuntimeError("fal.ai returned an empty audio file.")

    content_type = (
        audio_item.get("content_type") if isinstance(audio_item, dict) else None
    ) or audio_response.headers.get("Content-Type", "audio/wav")
    if ";" in content_type:
        content_type = content_type.split(";", 1)[0].strip()
    file_name = audio_item.get("file_name") or audio_url.split("?", 1)[0]
    extension = os.path.splitext(file_name)[1].lower()
    if extension not in {".wav", ".mp3", ".flac", ".ogg"}:
        extension = ".mp3" if content_type in {"audio/mpeg", "audio/mp3"} else ".wav"
    return audio_response.content, content_type, extension


def local_acestep_api_is_reachable():
    """Check whether the configured local ACE-Step API host accepts connections."""
    base_url = str(
        get_secret_safe("ACESTEP_LOCAL_URL") or "http://127.0.0.1:8001"
    ).strip()
    parsed = urlparse(base_url)
    if parsed.scheme not in {"http", "https"} or not parsed.hostname:
        return False

    try:
        port = parsed.port or (443 if parsed.scheme == "https" else 80)
        with socket.create_connection((parsed.hostname, port), timeout=0.5):
            return True
    except (OSError, ValueError):
        return False


def generate_audio_with_local_acestep(song_data, duration=60, vocal_language="ja"):
    """Generate a song through a locally running ACE-Step REST API server."""
    base_url = str(
        get_secret_safe("ACESTEP_LOCAL_URL") or "http://127.0.0.1:8001"
    ).strip().rstrip("/")
    if not base_url.startswith(("http://", "https://")):
        raise RuntimeError("ACESTEP_LOCAL_URL must start with http:// or https://.")

    headers = {}
    api_key = get_secret_safe("ACESTEP_LOCAL_API_KEY")
    if api_key and str(api_key).strip():
        headers["Authorization"] = f"Bearer {str(api_key).strip()}"

    payload = {
        "prompt": f"{song_data.get('title', '')}; {song_data['tags']}".strip("; ")[:2000],
        "lyrics": str(song_data["lyrics"])[:4096],
        "audio_duration": duration,
        "batch_size": 1,
        "thinking": False,
        "vocal_language": vocal_language,
        "audio_format": "mp3",
    }
    submit_response = requests.post(
        f"{base_url}/release_task", headers=headers, json=payload, timeout=(10, 60)
    )
    submit_response.raise_for_status()
    submit_data = submit_response.json()
    task_id = (submit_data.get("data") or {}).get("task_id")
    if not task_id:
        detail = submit_data.get("error") or submit_data.get("message") or submit_data
        raise RuntimeError(f"Local ACE-Step did not return a task ID: {detail}")

    deadline = time.monotonic() + 900
    while time.monotonic() < deadline:
        result_response = requests.post(
            f"{base_url}/query_result",
            headers=headers,
            json={"task_id_list": [task_id]},
            timeout=(10, 30),
        )
        result_response.raise_for_status()
        result_data = result_response.json().get("data") or []
        if result_data:
            record = result_data[0]
            status = int(record.get("status", 0))
            if status == 2:
                raise RuntimeError(
                    str(record.get("error") or record.get("result") or "Local ACE-Step generation failed.")
                )
            if status == 1:
                raw_result = record.get("result") or []
                if isinstance(raw_result, str):
                    try:
                        raw_result = json.loads(raw_result)
                    except json.JSONDecodeError as exc:
                        raise RuntimeError("Local ACE-Step returned an unreadable result.") from exc
                if isinstance(raw_result, dict):
                    audio_item = raw_result
                elif isinstance(raw_result, list) and raw_result:
                    audio_item = raw_result[0]
                else:
                    raise RuntimeError("Local ACE-Step completed without an audio file.")

                file_ref = audio_item.get("file") or audio_item.get("url")
                if not file_ref:
                    raise RuntimeError("Local ACE-Step completed without an audio file URL.")
                if str(file_ref).startswith(("http://", "https://")):
                    audio_url = str(file_ref)
                    audio_response = requests.get(audio_url, timeout=(15, 120))
                elif str(file_ref).startswith("/v1/audio"):
                    audio_url = urljoin(f"{base_url}/", str(file_ref).lstrip("/"))
                    audio_response = requests.get(
                        audio_url, headers=headers, timeout=(15, 120)
                    )
                else:
                    audio_response = requests.get(
                        f"{base_url}/v1/audio",
                        headers=headers,
                        params={"path": str(file_ref)},
                        timeout=(15, 120),
                    )
                audio_response.raise_for_status()
                if not audio_response.content:
                    raise RuntimeError("Local ACE-Step returned an empty audio file.")
                content_type = audio_response.headers.get("Content-Type", "audio/mpeg")
                if ";" in content_type:
                    content_type = content_type.split(";", 1)[0].strip()
                extension = ".wav" if content_type in {"audio/wav", "audio/x-wav"} else ".mp3"
                return audio_response.content, content_type, extension
        time.sleep(2)

    raise RuntimeError("Local ACE-Step did not finish within 15 minutes.")

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
            value="demo@knowledge2music.app",
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
        st.session_state["session_gemini_api_key"] = ""
        st.session_state["session_fal_api_key"] = ""
        st.rerun()

    st.markdown("---")
    with st.expander(t["api_keys_title"], expanded=False):
        st.text_input(
            t["gemini_api_key_label"],
            type="password",
            key="session_gemini_api_key",
        )
        st.text_input(
            t["fal_api_key_label"],
            type="password",
            key="session_fal_api_key",
        )
        st.caption(t["api_keys_privacy"])

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
pil_images = []

with tab1:
    text_input = st.text_area(t["text_prompt"], height=150, max_chars=5000)
    if text_input.strip():
        extracted_text += text_input.strip() + "\n"

with tab2:
    uploaded_files = st.file_uploader(
        t["file_prompt"],
        type=["txt", "pdf", "docx"],
        accept_multiple_files=True,
    )
    for uploaded_file in uploaded_files:
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
    uploaded_images = st.file_uploader(
        t["img_prompt"],
        type=["png", "jpg", "jpeg"],
        accept_multiple_files=True,
    )
    image_names = []
    for uploaded_image in uploaded_images:
        try:
            with Image.open(uploaded_image) as opened_image:
                prepared_image = ImageOps.exif_transpose(opened_image).convert("RGB")
            prepared_image.thumbnail((1536, 1536))
            pil_images.append(prepared_image)
            image_names.append(uploaded_image.name)
        except Exception:
            st.warning(t["image_read_error"].format(name=uploaded_image.name))

    if pil_images:
        image_columns = st.columns(min(4, len(pil_images)))
        for index, (image, image_name) in enumerate(zip(pil_images, image_names)):
            with image_columns[index % len(image_columns)]:
                st.image(image, caption=image_name, use_container_width=True)

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
    genre_options = dict(t["genre_options"])
    genre_language_index = {"JP": 0, "VI": 1}.get(st.session_state["lang"])
    genre_options.update({
        name: labels[genre_language_index] if genre_language_index is not None else name
        for name, labels in MORE_GENRES.items()
    })
    genre_options["custom"] = t["custom_genre"]
    genre = st.selectbox(
        t["genre_label"], list(genre_options), format_func=genre_options.get, key="music_genre",
    )
    if genre == "custom":
        genre = st.text_input(t["custom_genre"], max_chars=90, key="custom_genre").strip()
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

if st.button(t["demo_sample_button"], use_container_width=True):
    st.session_state["song_data"] = get_demo_song(st.session_state["lang"])
    reset_generated_media()
    st.rerun()

# --- 9. ステップ1：Geminiで要約と歌詞を作成 ---
if st.button(t["btn_generate"], type="primary", use_container_width=True):
    now = time.time()
    cooldown = 5

    if now - st.session_state["last_request_time"] < cooldown:
        remaining = int(cooldown - (now - st.session_state["last_request_time"]))
        st.warning(t["error_cooldown"].format(sec=remaining))
    elif not genre:
        st.error(t["custom_genre_required"])
    elif not extracted_text.strip() and not pil_images:
        st.error(t["error_no_data"])
    else:
        api_key = get_runtime_key("GEMINI_API_KEY")
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
                Base the summary and lyrics on the study material. Keep definitions, formulas, numbers,
                and exceptions accurate. Include the most important facts from the summary in the chorus.

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

                contents = [{"type": "text", "text": system_instruction}]
                if extracted_text.strip():
                    contents.append({"type": "text", "text": f"Study Material:\n{extracted_text}"})
                for image in pil_images:
                    with BytesIO() as buffer:
                        image.save(buffer, format="PNG")
                        contents.append({
                            "type": "image",
                            "mime_type": "image/png",
                            "data": base64.b64encode(buffer.getvalue()).decode("ascii"),
                        })

                errors = []
                for model in GEMINI_MODELS:
                    try:
                        interaction = client.interactions.create(
                            model=model,
                            input=contents,
                            store=False,
                            timeout=45,
                        )
                        raw_out = (interaction.output_text or "").strip()
                        if raw_out:
                            break
                        errors.append(f"{model}: {t['gemini_empty_response']}")
                    except Exception as err:
                        errors.append(f"{model}: {err}")
                else:
                    raise RuntimeError(
                        t["models_failed"].format(
                            count=len(GEMINI_MODELS),
                            models=", ".join(GEMINI_MODELS),
                            detail=errors[0],
                        )
                    )

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

                tags_val = tags_val.strip()
                if genre.casefold() not in tags_val.casefold():
                    tags_val = ", ".join(part for part in (genre, tags_val) if part)
                reset_generated_media()
                st.session_state["song_data"] = {
                    "title": title_val.strip(),
                    "summary": summary_val.strip(),
                    "tags": tags_val,
                    "genre": genre,
                    "mood": vibe,
                    "lyrics": lyrics_val.strip(),
                    "is_demo_sample": False,
                    "gemini_model": model,
                }
                st.toast(t["generation_success"].format(model=model))
        except Exception as e:
            st.error(f"{t['generation_error']} {e}")

# --- 10. ステップ2：結果を表示してアプリ内で曲を生成 ---
if st.session_state["song_data"] is not None:
    data = st.session_state["song_data"]
    st.markdown("---")
    st.subheader(t["step2_title"])
    st.caption(t["step2_guide"])
    if data.get("is_demo_sample"):
        st.info(t["demo_sample_caption"])
    elif data.get("gemini_model"):
        st.caption(t["gemini_model_used"].format(model=data["gemini_model"]))

    with st.expander(t["video_settings"], expanded=True):
        video_theme = st.selectbox(t["video_theme"], list(THEMES), format_func=t["video_themes"].get)
        video_show_lyrics = st.checkbox(t["video_show_lyrics"], value=True, key="video_show_lyrics")
        video_waveform = st.checkbox(t["video_waveform"], value=True, key="video_waveform")
        video_mode = st.radio(t["video_background_mode"], ["simple", "ai"], format_func=t["video_background_modes"].get)
        video_background = None
        video_prompt = ""
        if video_mode == "ai":
            video_prompt = st.text_area(
                t["video_prompt"], placeholder=t["video_prompt_example"], max_chars=850, key="video_prompt",
            ).strip()
            st.caption(t["video_ai_note"] + " [LTX-2.5](https://huggingface.co/spaces/Lightricks/LTX-2.5)")
        else:
            video_background = st.file_uploader(
                t["video_background"], type=["jpg", "jpeg", "png", "webp"],
                key="video_background", max_upload_size=12,
            )

    col_s1, col_s2 = st.columns([1, 1])
    with col_s1:
        st.markdown(f"#### {t['summary_label']}")
        st.info(data["summary"])

        st.markdown(f"#### {t['song_title_label']}")
        st.code(data["title"], language="text")

        st.markdown(f"#### {t['music_style_label']}")
        st.code(data["tags"], language="text")

        audio_provider = st.selectbox(
            t["audio_provider_label"],
            options=list(t["audio_provider_options"].keys()),
            format_func=lambda provider: t["audio_provider_options"][provider],
            key="audio_provider",
        )
        st.info(t["audio_provider_notes"][audio_provider])
        st.caption(t["audio_quota_note"])
        st.warning(t["music_copyright_warning"])
        fal_endpoint = FAL_MUSIC_ENDPOINTS.get(audio_provider)
        if fal_endpoint:
            st.caption(
                f"[{t['music_model_terms_link']}](https://fal.ai/models/{fal_endpoint}) · "
                f"[{t['music_fal_terms_link']}](https://fal.ai/legal/terms-of-service)"
            )
        else:
            st.caption(f"[{t['music_model_terms_link']}](https://huggingface.co/ACE-Step/Ace-Step1.5)")
        if st.session_state["lang"] == "VI":
            st.warning(t["vietnamese_vocal_warning"])

        fal_key_configured = bool(get_runtime_key("FAL_KEY"))
        provider_needs_fal = fal_endpoint is not None
        minimax_lyrics_too_long = (
            audio_provider == "fal_minimax" and len(data["lyrics"]) > MINIMAX_LYRICS_LIMIT
        )
        mureka_lyrics_too_long = (
            audio_provider == "fal_mureka_v8" and len(data["lyrics"]) > 5000
        )
        lyria_lyrics_too_long = (
            audio_provider == "fal_lyria_35" and len(data["lyrics"]) > 5000
        )

        if provider_needs_fal and not fal_key_configured:
            st.info(t["fal_key_hint"])
        local_api_available = True
        if audio_provider == "local_acestep":
            st.info(t["local_api_url_hint"])
            local_api_available = local_acestep_api_is_reachable()
            if not local_api_available:
                st.warning(t["local_api_unavailable"])
        if minimax_lyrics_too_long:
            st.warning(t["minimax_lyrics_limit"])
        if mureka_lyrics_too_long:
            st.warning(t["mureka_lyrics_limit"])
        if lyria_lyrics_too_long:
            st.warning(t["lyria_lyrics_limit"])

        audio_disabled = (
            (provider_needs_fal and not fal_key_configured)
            or minimax_lyrics_too_long
            or mureka_lyrics_too_long
            or lyria_lyrics_too_long
            or (audio_provider == "local_acestep" and not local_api_available)
        )
        audio_path = st.session_state.get("generated_audio_path")
        has_audio = bool(audio_path and os.path.isfile(audio_path))
        music_requested = st.button(
            t["btn_generate_audio"], type="primary", width="stretch", disabled=audio_disabled
        )
        video_requested = st.button(
            t["btn_generate_video"], width="stretch",
            disabled=(audio_disabled and not has_audio) or (video_mode == "ai" and not video_prompt),
        )
        if has_audio:
            st.caption(t["video_reuse"])

        if music_requested or (video_requested and not has_audio):
            with st.spinner(t["status_generating_audio"]):
                try:
                    if audio_provider == "local_acestep":
                        vocal_language = {
                            "JP": "ja",
                            "VI": "vi",
                            "EN": "en",
                        }.get(st.session_state["lang"], "ja")
                        audio_bytes, audio_mime, audio_extension = generate_audio_with_local_acestep(
                            data,
                            duration=60,
                            vocal_language=vocal_language,
                        )
                    else:
                        audio_bytes, audio_mime, audio_extension = generate_audio_with_fal(
                            data,
                            model=audio_provider,
                            duration=60,
                        )
                    safe_title = re.sub(r"[^\w-]+", "_", data["title"], flags=re.UNICODE).strip("_-")[:60]
                    if not safe_title:
                        safe_title = "knowledge_song"
                    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
                    filename = f"{safe_title}_{timestamp}{audio_extension}"
                    os.makedirs("saved_songs", exist_ok=True)
                    generated_path = os.path.join("saved_songs", filename)
                    with open(generated_path, "wb") as audio_file:
                        audio_file.write(audio_bytes)
                    reset_generated_media()
                    st.session_state["generated_audio_path"] = generated_path
                    st.session_state["generated_audio_mime"] = audio_mime
                    st.success(t["audio_ready"])
                except Exception as exc:
                    error_detail = str(exc)
                    st.error(f"{t['audio_error']} {error_detail}")
                    if os.path.isdir("saved_songs") and any(
                        name.lower().endswith((".mp3", ".wav"))
                        for name in os.listdir("saved_songs")
                    ):
                        st.caption(t["audio_fallback_hint"])
                    lower_error = error_detail.lower()
                    if "fal_key" in lower_error or "401" in lower_error or "403" in lower_error:
                        st.info(t["fal_key_hint"])
                    elif "credit" in lower_error or "402" in lower_error or "payment" in lower_error:
                        st.info(t["fal_billing_hint"])

    with col_s2:
        st.markdown(f"#### {t['lyrics_label']}")
        st.code(data["lyrics"], language="text")

    generated_path = st.session_state.get("generated_audio_path")
    has_audio = bool(generated_path and os.path.isfile(generated_path))
    if has_audio:
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
            key="generated_song_download",
            use_container_width=True,
        )

    timing = st.session_state.get("video_timing") if has_audio else None
    if timing:
        if timing["cues"] and "section" not in timing["cues"][0]:
            sections = estimate_cues(data["lyrics"], timing["duration"])
            if len(sections) == len(timing["cues"]):
                for cue, new_cue in zip(timing["cues"], sections):
                    cue["section"] = new_cue["section"]
        with st.expander(t["video_timing"]):
            st.caption(t["video_timing_note"])
            cues = st.data_editor(
                timing["cues"],
                column_config={
                    "start": st.column_config.NumberColumn(
                        t["video_start"], min_value=0, max_value=timing["duration"], step=0.01, required=True,
                    ),
                    "lyrics": st.column_config.TextColumn(t["video_caption"], width="large", required=True),
                    "section": st.column_config.TextColumn(t["video_section"]),
                },
                key=f"video_timing:{generated_path}",
                disabled=["section"],
                hide_index=True,
                width="stretch",
            )

    if video_requested and has_audio:
        try:
            new_timing = timing is None
            if new_timing:
                duration = audio_duration(generated_path)
                cues = estimate_cues(data["lyrics"], duration)
                timing = {"duration": duration, "cues": cues}
                st.session_state["video_timing"] = timing

            scenes = None
            notices = []
            if video_mode == "ai":
                validate_cues(cues, timing["duration"])
                timeline = scene_timeline(video_prompt, cues, data.get("genre", ""), data.get("mood", ""))
                prompts = list(dict.fromkeys(prompt for _, prompt in timeline if prompt))
                if not prompts:
                    notices.append("video_scene_unmatched")
                if len(prompts) > MAX_VIDEO_SCENES:
                    notices.append("video_ai_limit")
                prompts = prompts[:MAX_VIDEO_SCENES]
                cache = st.session_state.get("video_ai_clips", {})
                clips = {prompt: cache[prompt] for prompt in prompts if prompt in cache}
                st.session_state["video_ai_clips"] = clips
                if any(prompt not in clips for prompt in prompts):
                    with st.spinner(t["video_ai_rendering"]):
                        for prompt in prompts:
                            if prompt in clips:
                                continue
                            try:
                                clips[prompt] = generate_background(prompt)
                            except Exception:
                                notices.append("video_ai_unavailable")
                                break
                scenes = [(start, clips.get(prompt)) for start, prompt in timeline]

            with st.spinner(t["video_rendering"]):
                if video_background:
                    with Image.open(video_background) as background:
                        background.thumbnail((1920, 1080))
                        video_bytes = render_lyric_video(
                            generated_path, data["title"], timing["duration"], cues, video_theme,
                            image=background, waveform=video_waveform, show_lyrics=video_show_lyrics,
                        )
                else:
                    video_bytes = render_lyric_video(
                        generated_path, data["title"], timing["duration"], cues, video_theme,
                        scenes=scenes, waveform=video_waveform, show_lyrics=video_show_lyrics,
                    )
            st.session_state["generated_video"] = video_bytes
            st.session_state["video_scene_notices"] = notices
            if new_timing:
                st.rerun()
        except Exception as exc:
            st.error(f"{t['video_error']} · {exc}")

    video_bytes = st.session_state.get("generated_video") if has_audio else None
    if video_bytes:
        st.markdown(f"#### {t['video_preview']}")
        for notice in st.session_state.get("video_scene_notices", []):
            st.warning(t[notice])
        st.video(video_bytes, format="video/mp4")
        st.download_button(
            t["video_download"],
            data=video_bytes,
            file_name=f"{os.path.splitext(os.path.basename(generated_path))[0]}_lyrics.mp4",
            mime="video/mp4",
            key="generated_video_download",
            width="stretch",
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
        key="library_song_download",
        use_container_width=True
    )

