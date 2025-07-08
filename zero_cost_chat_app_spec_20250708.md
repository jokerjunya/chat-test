# Zero‑Cost Japanese Chat Web App with Web Search — Development Specification (2025‑07‑08)

## 1. Purpose & Scope

M3 Max (64 GB) MacBook Pro 環境で「月額ゼロ円 / 高品質 / 日本語対応 / Web検索付き」の ChatGPT‑ライクな Web アプリを最小構成で構築し、社内 PoC→小規模運用へ拡張する。

## 2. Core Requirements

| 区分  | 要件         |
| --- | ---------- |
| 言語  | UI・応答とも日本語 |
| LLM |            |

| **ERNIE 4.5 Turbo**（4‑bit Q5\_K\_M ≈ 19 GB）をローカル推論 |                                      |
| -------------------------------------------------- | ------------------------------------ |
| Web検索                                              | **DuckDuckGo** (`ddgs` ライブラリ)        |
| オーケストレーション                                         | **LangChain 0.10.x + LangGraph 0.3** |
| コスト                                                | 外部有料 API を使用しない                      |

## 3. Tech Stack

| レイヤ         | コンポーネント                                | 備考                                   |
| ----------- | -------------------------------------- | ------------------------------------ |
| Frontend    | Next.js 14 · Tailwind CSS              | WebSocket でトークンストリーム受信               |
| Backend     | FastAPI 1.1 (Python 3.11)              | 軽量 ASGI                              |
| LLM Runtime | Ollama 0.1.38 / llama.cpp v0.6 (Metal) | `ollama pull ernie:4.5-turbo-q5_K_M` |
| Search Tool | `ddgs` (DuckDuckGo)                    | API キー不要                             |
| Agent       | LangChain + LangGraph                  | DAG で Tool ↔︎ LLM                    |

## 4. Architecture Overview

```
Browser (React)
   │  WebSocket / REST
   ▼
FastAPI server ── LangGraph DAG
   ├─ DuckDuckGo Search Tool
   └─ ERNIE 4.5 Turbo (Ollama)
```

## 5. Setup Steps

```bash
# System packages
brew upgrade llama.cpp ollama
brew install pyenv

# Model
aollama pull ernie:4.5-turbo-q5_K_M

# Python env
pyenv install 3.11.9
pyenv local 3.11.9
pip install fastapi uvicorn langchain langgraph ddgs websockets
```

## 6. API Design

- **POST /api/chat** — ボディ `{ "messages": [ ... ] }`
- SSE または WebSocket でトークンをストリーム送信。

## 7. Prompt & Search Flow

1. System Prompt にアプリ目的・出力スタイルを明示。
2. 各ユーザ入力を `ddgs` で検索（上位 5 件）。
3. URL とスニペットをコンテキストとして ERNIE に渡す。
4. LangGraph DAG で「検索→RAG→生成」を制御。

## 8. KPI

| 指標                   | 目標     |
| -------------------- | ------ |
| レイテンシ（128 tok）       | ≤ 6 s  |
| 日本語 BLEU (vs GPT‑4o) | ≥ 0.85 |
| DDG リクエスト/日          | ≤ 250  |

## 9. CursorAI / Claude 4 Sonnet Collaboration Guidelines

| 観点            | 推奨                                    |
| ------------- | ------------------------------------- |
| モデル指定         | `model: "claude-4.0-sonnet"` を明記      |
| コンテキスト長       | 安全上限 120 k tokens、長文は分割依頼             |
| System Prompt | 日本語出力 / コードは fenced blocks / シークレット禁止 |
| ファイル出力        | `--- path/to/file.ext ---` 形式を要求      |
| タスク分割         | ディレクトリ設計 → モジュール実装 → テスト の段階化         |
| ライブラリ版        | ローカル環境と合わせて指定                         |
| エラー対応         | 全ログ + 最小パッチ再依頼の 2 ステップ                |
| 評価基準          | テスト通過やレイテンシなど定量指標を共有                  |

## 10. 7‑Day Roadmap

| Day | 目標                   |
| --- | -------------------- |
| 0‑1 | 環境構築・モデル起動           |
| 2‑3 | FastAPI + WS/REST    |
| 4‑5 | Next.js UI + ストリーム連携 |
| 6   | LangGraph + ddgs 統合  |
| 7   | KPI 測定 & ドキュメント整備    |

## 11. License

すべて Apache‑2.0 または MIT — 商用利用可。

---

