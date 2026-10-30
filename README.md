# knowledge2music

学習内容をAIで要約し、歌詞を作成して、ACE-Step（fal.ai）でボーカル付きの曲を生成するStreamlitアプリです。授業での発表を目的としたプロトタイプです。

## Windowsでの起動方法

プロジェクトフォルダーでPowerShellを開き、次のコマンドを実行します。

```powershell
py -m venv .venv
.venv\Scripts\python.exe -m pip install -r requirements.txt
```

`.streamlit/secrets.toml` がない場合は、サンプルから作成します。

```powershell
Copy-Item .streamlit\secrets.example.toml .streamlit\secrets.toml
```

`secrets.toml` に Gemini APIキーと fal.ai APIキーを設定してください。fal.aiのAPIキーは[ダッシュボード](https://fal.ai/dashboard/keys)で作成できます。音楽生成にはfal.aiの利用可能なクレジットが必要です。secretsファイルやAPIキーを共有したり、スライドやソースコードに掲載したりしないでください。

アプリを起動します。

```powershell
.venv\Scripts\python.exe -m streamlit run app.py
```

## デモの流れ

1. 言語で「日本語」を選びます。
2. Google OAuthが未設定の場合は、メールアドレス形式の文字列を入力してデモモードに進みます。Googleアカウントの本人確認は行いません。
3. 学習内容を入力またはアップロードし、音楽スタイルを選択して生成ボタンを押します。
4. 要約、曲名、スタイル、歌詞を確認します。
5. 「曲を生成」を押し、処理完了後にアプリ内で再生またはWAVファイルをダウンロードします。
6. 必要に応じて、手元のMP3/WAVファイルをライブラリに追加します。

## 料金とデータについて

fal.aiのACE-Step APIは生成した音声の長さに応じて課金されます。現在の目安は1秒あたり約**$0.0002**で、60秒の音声は約**$0.012**です。実際の料金は生成された音声の長さによって変わります。アプリからfal.aiに送信するのは、生成済みの音楽スタイルと歌詞です。元の学習資料は送信しません。APIキーは`.streamlit/secrets.toml`から読み込み、ソースコードやスライド、チャットに記載しないでください。

## 主なライブラリ

必要なPythonパッケージは`requirements.txt`に記載されています。
