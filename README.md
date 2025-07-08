# ゼロコスト日本語チャットアプリ

月額ゼロ円で運用可能な日本語対応チャットアプリのプロトタイプです。

## 機能

- 日本語でのチャット対応
- REST API エンドポイント (`/api/chat`)
- WebSocket リアルタイム通信 (`/api/chat/ws`)
- ローカル LLM (Ollama) を使用したコスト削減
- Web検索機能（プレースホルダー実装）

## セットアップ

### 1. 必要なソフトウェアのインストール

```bash
# Homebrew でパッケージをインストール
brew install pyenv ollama llama.cpp

# Python 3.11.9 をインストール
pyenv install 3.11.9
pyenv local 3.11.9

# Python 依存関係をインストール
pip install -r requirements.txt
```

### 2. Ollama の起動

```bash
# Ollama サーバーを起動
ollama serve

# 別のターミナルで利用可能なモデルを確認
ollama list
```

### 3. アプリケーションの起動

```bash
# FastAPI アプリケーションを起動
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

## 使用方法

### REST API でのチャット

```bash
curl -X POST "http://localhost:8000/api/chat" \
  -H "Content-Type: application/json" \
  -d '{"messages": [{"role": "user", "content": "こんにちは"}]}'
```

### WebSocket でのチャット

WebSocket エンドポイント: `ws://localhost:8000/api/chat/ws`

メッセージフォーマット:
```json
{
  "messages": [
    {"role": "user", "content": "こんにちは"}
  ]
}
```

### ヘルスチェック

```bash
curl http://localhost:8000/health
```

## テスト

統合テストを実行するには:

```bash
python test_api.py
```

## API エンドポイント

### POST /api/chat

チャットメッセージを送信し、AI の応答を取得します。

**リクエスト:**
```json
{
  "messages": [
    {"role": "user", "content": "ユーザーメッセージ"}
  ]
}
```

**レスポンス:**
```json
{
  "message": "AI の応答",
  "timestamp": 1234567890.123
}
```

### WebSocket /api/chat/ws

リアルタイムチャット通信用のWebSocketエンドポイント。

### GET /health

アプリケーションの健全性を確認します。

**レスポンス:**
```json
{
  "status": "healthy",
  "timestamp": 1234567890.123
}
```

## 技術スタック

- **Backend**: FastAPI 0.116.0 (Python 3.11.9)
- **LLM**: Ollama (現在は Qwen3:30B モデル)
- **WebSocket**: FastAPI WebSocket サポート
- **HTTP Client**: httpx
- **Web Search**: ddgs (将来実装予定)

## 開発状況

- [x] 基本的な FastAPI セットアップ
- [x] REST API エンドポイント
- [x] WebSocket サポート
- [x] Ollama との統合
- [x] 日本語対応
- [ ] DuckDuckGo Web検索の実装
- [ ] LangChain/LangGraph の統合
- [ ] フロントエンド UI の実装

## 注意事項

1. **モデルの変更**: 仕様書では ERNIE 4.5-Turbo が指定されていますが、利用できないため現在は Qwen3:30B を使用しています。
2. **Web検索**: 現在はモックデータを返すプレースホルダーです。
3. **パフォーマンス**: 初回起動時はモデルの読み込みに時間がかかる場合があります。

## トラブルシューティング

### Ollama が起動しない

```bash
# Ollama のステータスを確認
ollama list

# プロセスを確認
ps aux | grep ollama
```

### API が応答しない

```bash
# サーバーのログを確認
# uvicorn のログを確認してエラーメッセージを確認してください
```

### モデルが見つからない

```bash
# 利用可能なモデルを確認
ollama list

# 必要に応じて代替モデルを使用
# main.py の call_ollama 関数でモデル名を変更
``` 