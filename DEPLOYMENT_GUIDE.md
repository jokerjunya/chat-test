# ゼロコスト日本語チャットアプリ - デプロイメントガイド

完成したシステムのデプロイメントと運用方法を説明します。

## 🚀 完成機能

### ✅ 実装完了機能
- [x] **DuckDuckGo Web検索**: 実際の検索結果を取得
- [x] **LangGraph + LangChain統合**: 検索→RAG→生成のワークフロー
- [x] **ストリーミング応答**: リアルタイムトークンストリーミング
- [x] **Next.js フロントエンド**: モダンなUI/UX
- [x] **WebSocket統合**: リアルタイム通信
- [x] **KPI測定システム**: レイテンシ、BLEU、DDGリクエスト数の監視
- [x] **日本語対応**: 完全な日本語インターフェース

### 🎯 目標達成状況
| 指標 | 目標 | 現状 |
|------|------|------|
| レイテンシ（128 tok） | ≤ 6 s | 測定中 |
| 日本語 BLEU | ≥ 0.85 | 測定中 |
| DDG リクエスト/日 | ≤ 250 | 監視中 |

## 🏗️ システム構成

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Frontend      │    │   Backend       │    │   AI/Search     │
│   (Next.js)     │◄──►│   (FastAPI)     │◄──►│   (Ollama)      │
│                 │    │                 │    │   (DuckDuckGo)  │
│ - React UI      │    │ - REST API      │    │ - Qwen3:30B     │
│ - WebSocket     │    │ - WebSocket     │    │ - Web Search    │
│ - Streaming     │    │ - LangGraph     │    │ - KPI Monitor   │
└─────────────────┘    └─────────────────┘    └─────────────────┘
```

## 📦 デプロイメント手順

### 1. 環境セットアップ

```bash
# 1. リポジトリクローン
git clone <repository-url>
cd chat-test2

# 2. Python 環境構築
pyenv install 3.11.9
pyenv local 3.11.9
pip install -r requirements.txt

# 3. Ollama インストール・設定
brew install ollama
ollama serve  # バックグラウンドで起動
ollama pull qwen3:30b  # モデルをダウンロード

# 4. フロントエンド セットアップ
cd frontend
npm install
npm run build
```

### 2. サーバー起動

```bash
# バックエンド起動
cd ..
uvicorn main:app --host 0.0.0.0 --port 8000

# フロントエンド起動（別ターミナル）
cd frontend
npm start
```

### 3. アクセス確認

- **フロントエンド**: http://localhost:3000
- **バックエンド API**: http://localhost:8000
- **API ドキュメント**: http://localhost:8000/docs

## 🔧 設定オプション

### 環境変数

```bash
# .env ファイル作成
OLLAMA_MODEL=qwen3:30b
OLLAMA_BASE_URL=http://localhost:11434
SEARCH_MAX_RESULTS=5
KPI_MONITORING=true
```

### 設定ファイル

```python
# config.py
SETTINGS = {
    "model_name": "qwen3:30b",
    "max_search_results": 5,
    "max_context_length": 4096,
    "stream_timeout": 60,
    "kpi_retention_days": 30
}
```

## 📊 KPI監視

### KPI確認方法

```bash
# 日次統計
curl http://localhost:8000/api/kpi/stats

# パフォーマンスレポート
curl http://localhost:8000/api/kpi/report

# データエクスポート
curl -X POST http://localhost:8000/api/kpi/export
```

### KPI ダッシュボード

フロントエンドに管理画面を追加する場合：

```javascript
// pages/admin/kpi.js
import { useState, useEffect } from 'react'

export default function KPIDashboard() {
  const [stats, setStats] = useState(null)
  
  useEffect(() => {
    fetch('/api/kpi/stats')
      .then(res => res.json())
      .then(setStats)
  }, [])
  
  return (
    <div>
      <h1>KPI ダッシュボード</h1>
      {stats && (
        <div>
          <p>平均レイテンシ: {stats.avg_latency_ms}ms</p>
          <p>日次検索数: {stats.search_requests}</p>
          <p>エラー率: {stats.error_rate * 100}%</p>
        </div>
      )}
    </div>
  )
}
```

## 🔄 運用とメンテナンス

### 日次チェック項目

1. **システム状態確認**
   ```bash
   curl http://localhost:8000/health
   ```

2. **KPI確認**
   ```bash
   curl http://localhost:8000/api/kpi/report
   ```

3. **ログ監視**
   ```bash
   tail -f uvicorn.log
   ```

### 定期メンテナンス

#### 週次タスク
- KPI データのバックアップ
- システムリソース使用量確認
- エラーログ分析

#### 月次タスク
- モデルの性能評価
- 検索結果の品質確認
- セキュリティアップデート

### トラブルシューティング

#### よくある問題と解決策

1. **Ollama 接続エラー**
   ```bash
   # Ollama サービス状態確認
   ps aux | grep ollama
   
   # 再起動
   pkill ollama
   ollama serve
   ```

2. **WebSocket 接続失敗**
   ```javascript
   // フロントエンド: 接続リトライ機能
   const connectWithRetry = () => {
     const ws = new WebSocket('ws://localhost:8000/api/chat/stream')
     ws.onclose = () => {
       setTimeout(connectWithRetry, 5000)
     }
   }
   ```

3. **検索結果が取得できない**
   ```bash
   # DuckDuckGo アクセス確認
   python -c "from ddgs import DDGS; print(DDGS().text('test', max_results=1))"
   ```

## 🚀 本番運用への移行

### スケーリング対応

1. **負荷分散**
   ```nginx
   upstream backend {
       server localhost:8000;
       server localhost:8001;
       server localhost:8002;
   }
   ```

2. **データベース導入**
   ```python
   # PostgreSQL で KPI データを永続化
   from sqlalchemy import create_engine
   
   engine = create_engine('postgresql://user:pass@localhost/kpi_db')
   ```

3. **コンテナ化**
   ```dockerfile
   # Dockerfile
   FROM python:3.11-slim
   
   COPY requirements.txt .
   RUN pip install -r requirements.txt
   
   COPY . .
   CMD ["uvicorn", "main:app", "--host", "0.0.0.0"]
   ```

### セキュリティ対策

1. **認証機能追加**
2. **HTTPS 対応**
3. **API レート制限**
4. **入力検証強化**

## 📈 性能最適化

### 推奨設定

```python
# 本番環境設定
PRODUCTION_CONFIG = {
    "workers": 4,
    "max_connections": 1000,
    "timeout": 30,
    "log_level": "info",
    "access_log": True
}
```

### 監視設定

```yaml
# docker-compose.yml
version: '3.8'
services:
  app:
    build: .
    ports:
      - "8000:8000"
    environment:
      - LOG_LEVEL=info
    volumes:
      - ./logs:/app/logs
  
  prometheus:
    image: prom/prometheus
    ports:
      - "9090:9090"
    volumes:
      - ./prometheus.yml:/etc/prometheus/prometheus.yml
```

## 🎯 まとめ

このシステムは以下の特徴を持つ完全なゼロコストチャットアプリです：

- **完全無料**: 外部有料APIを使用せず
- **高性能**: ローカルLLMによる高速応答
- **日本語対応**: 完全な日本語インターフェース
- **Web検索統合**: リアルタイム検索結果の活用
- **監視機能**: 包括的なKPI測定
- **拡張性**: 本番環境へのスケール対応

運用開始後は定期的なKPI確認と性能監視を行い、継続的な改善を実施してください。 