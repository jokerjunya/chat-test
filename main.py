import asyncio
import json
from typing import Dict, List, Optional
from fastapi import FastAPI, WebSocket, HTTPException, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import uvicorn
import httpx
import time
from langgraph_agent import rag_agent
from streaming_agent import streaming_agent
from kpi_monitor import kpi_monitor, calculate_bleu_score
from thinking_parser import ThinkingParser

app = FastAPI(
    title="ゼロコストチャットアプリ",
    description="日本語対応のWebSearch付きチャットアプリ",
    version="1.0.0"
)

# 思考分離パーサーの初期化
thinking_parser = ThinkingParser()

# CORS設定
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# リクエストモデル
class ChatMessage(BaseModel):
    role: str
    content: str

class ChatRequest(BaseModel):
    messages: List[ChatMessage]

class ChatResponse(BaseModel):
    message: str
    timestamp: float

# WebSocketマネージャー
class WebSocketManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)

    async def send_personal_message(self, message: str, websocket: WebSocket):
        await websocket.send_text(message)

    async def broadcast(self, message: str):
        for connection in self.active_connections:
            await connection.send_text(message)

manager = WebSocketManager()

# Ollamaとの通信関数
async def call_ollama(messages: List[ChatMessage], model: str = "qwen3:30b") -> str:
    """Ollamaを使用してLLMからの応答を取得"""
    try:
        # Ollamaのエンドポイントに送信するフォーマット
        ollama_messages = [{"role": msg.role, "content": msg.content} for msg in messages]
        
        # システムプロンプトを追加
        system_prompt = {
            "role": "system",
            "content": "あなたは日本語で応答する親切なAIアシスタントです。質問に対して正確で有用な回答を提供してください。"
        }
        
        ollama_messages.insert(0, system_prompt)
        
        async with httpx.AsyncClient() as client:
            response = await client.post(
                "http://localhost:11434/api/chat",
                json={
                    "model": model,
                    "messages": ollama_messages,
                    "stream": False
                },
                timeout=30.0
            )
            
            if response.status_code != 200:
                raise HTTPException(status_code=500, detail="Ollama API エラー")
            
            result = response.json()
            return result["message"]["content"]
            
    except httpx.TimeoutException:
        raise HTTPException(status_code=504, detail="Ollama API タイムアウト")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ollama API エラー: {str(e)}")

# DuckDuckGo Web検索機能
async def search_web(query: str, max_results: int = 5) -> List[Dict]:
    """DuckDuckGo を使用してWeb検索を実行"""
    try:
        from ddgs import DDGS
        
        # 日本語検索を優先するようにクエリを調整
        search_query = f"{query} lang:ja"
        
        results = []
        with DDGS() as ddgs:
            for result in ddgs.text(search_query, max_results=max_results):
                results.append({
                    "title": result.get("title", ""),
                    "url": result.get("href", ""),
                    "snippet": result.get("body", "")
                })
        
        # 検索結果がない場合は英語でも検索
        if not results:
            with DDGS() as ddgs:
                for result in ddgs.text(query, max_results=max_results):
                    results.append({
                        "title": result.get("title", ""),
                        "url": result.get("href", ""),
                        "snippet": result.get("body", "")
                    })
        
        return results
        
    except Exception as e:
        print(f"Web検索エラー: {str(e)}")
        # エラー時はフォールバック
        return [
            {
                "title": "検索結果を取得できませんでした",
                "url": "",
                "snippet": f"検索クエリ: {query} の結果を取得できませんでした。"
            }
        ]

# REST APIエンドポイント
@app.post("/api/chat", response_model=ChatResponse)
async def chat_endpoint(request: ChatRequest):
    """チャットメッセージを処理する REST エンドポイント"""
    # KPI測定開始
    start_time = kpi_monitor.start_measurement()
    
    try:
        # メッセージを辞書形式に変換
        messages = [{"role": msg.role, "content": msg.content} for msg in request.messages]
        
        # RAGエージェントでメッセージを処理
        result = await rag_agent.process_message(messages)
        
        if not result.get("success", False):
            # エラーの場合のKPI記録
            error_msg = result.get("error", "不明なエラー")
            kpi_monitor.record_measurement(
                start_time=start_time,
                token_count=0,
                search_requests=0,
                error_occurred=True,
                error_message=error_msg
            )
            raise HTTPException(status_code=500, detail=error_msg)
        
        # 成功の場合のKPI記録
        response_text = result["response"]
        token_count = len(response_text.split())  # 簡易的なトークン数
        search_count = len(result.get("search_results", []))
        
        kpi_monitor.record_measurement(
            start_time=start_time,
            token_count=token_count,
            search_requests=search_count,
            error_occurred=False
        )
        
        # 思考分離処理
        parsed_response = thinking_parser.parse_response(response_text)
        formatted_response = thinking_parser.format_for_frontend(parsed_response)
        
        return {
            "message": formatted_response["message"],
            "thinking": formatted_response["thinking"],
            "has_thinking": formatted_response["has_thinking"],
            "search_results": result.get("search_results", []),
            "timestamp": time.time()
        }
        
    except Exception as e:
        # 例外発生時のKPI記録
        kpi_monitor.record_measurement(
            start_time=start_time,
            token_count=0,
            search_requests=0,
            error_occurred=True,
            error_message=str(e)
        )
        raise HTTPException(status_code=500, detail=f"チャット処理エラー: {str(e)}")

# WebSocketエンドポイント（標準）
@app.websocket("/api/chat/ws")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocketでリアルタイムチャット"""
    await manager.connect(websocket)
    try:
        while True:
            # メッセージを受信
            data = await websocket.receive_text()
            message_data = json.loads(data)
            
            # ChatRequestとして解析
            request = ChatRequest(**message_data)
            
            # 応答を送信
            await manager.send_personal_message("処理中...", websocket)
            
            # メッセージを辞書形式に変換
            messages = [{"role": msg.role, "content": msg.content} for msg in request.messages]
            
            # RAGエージェントでメッセージを処理
            result = await rag_agent.process_message(messages)
            
            if result.get("success", False):
                # 思考分離処理
                response_text = result.get("response", "応答を生成できませんでした")
                parsed_response = thinking_parser.parse_response(response_text)
                formatted_response = thinking_parser.format_for_frontend(parsed_response)
                
                # 構造化されたレスポンスを送信
                await manager.send_personal_message(
                    json.dumps({
                        "type": "message",
                        "message": formatted_response["message"],
                        "thinking": formatted_response["thinking"],
                        "has_thinking": formatted_response["has_thinking"],
                        "search_results": result.get("search_results", []),
                        "timestamp": time.time()
                    }, ensure_ascii=False),
                    websocket
                )
            else:
                error_msg = result.get("error", "不明なエラー")
                await manager.send_personal_message(
                    json.dumps({
                        "type": "error",
                        "message": f"エラー: {error_msg}",
                        "timestamp": time.time()
                    }, ensure_ascii=False),
                    websocket
                )
            
    except WebSocketDisconnect:
        manager.disconnect(websocket)
    except Exception as e:
        await manager.send_personal_message(f"エラー: {str(e)}", websocket)

# WebSocketエンドポイント（ストリーミング）
@app.websocket("/api/chat/stream")
async def websocket_streaming_endpoint(websocket: WebSocket):
    """WebSocketでストリーミングチャット"""
    await manager.connect(websocket)
    try:
        while True:
            # メッセージを受信
            data = await websocket.receive_text()
            message_data = json.loads(data)
            
            # ChatRequestとして解析
            request = ChatRequest(**message_data)
            
            # メッセージを辞書形式に変換
            messages = [{"role": msg.role, "content": msg.content} for msg in request.messages]
            
            # ストリーミングエージェントでメッセージを処理
            response_chunks = []
            async for chunk in streaming_agent.stream_response(messages):
                # 通常のストリーミング処理
                await manager.send_personal_message(json.dumps(chunk, ensure_ascii=False), websocket)
                # 最終処理のために一時保存
                if chunk.get("type") == "completed":
                    response_chunks.append(chunk.get("content", ""))
            
            # 最終的な応答に対して思考分離処理
            if response_chunks:
                final_response = ''.join(response_chunks)
                parsed_response = thinking_parser.parse_response(final_response)
                if parsed_response.get("has_thinking"):
                    # 思考が含まれている場合は、思考情報を送信
                    await manager.send_personal_message(
                        json.dumps({
                            "type": "thinking_update",
                            "thinking": parsed_response["thinking"],
                            "has_thinking": True
                        }, ensure_ascii=False),
                        websocket
                    )
            
    except WebSocketDisconnect:
        manager.disconnect(websocket)
    except Exception as e:
        await manager.send_personal_message(json.dumps({
            "type": "error",
            "content": f"エラー: {str(e)}"
        }, ensure_ascii=False), websocket)

# ヘルスチェック
@app.get("/health")
async def health_check():
    """ヘルスチェックエンドポイント"""
    return {"status": "healthy", "timestamp": time.time()}

# KPIエンドポイント
@app.get("/api/kpi/stats")
async def get_kpi_stats():
    """KPI統計を取得"""
    return kpi_monitor.get_daily_stats()

@app.get("/api/kpi/report")
async def get_kpi_report():
    """KPIレポートを取得"""
    return kpi_monitor.get_performance_report()

@app.post("/api/kpi/export")
async def export_kpi_metrics():
    """KPI測定結果をエクスポート"""
    filename = kpi_monitor.export_metrics()
    return {"filename": filename, "message": "KPI測定結果をエクスポートしました"}

# サーバー起動
if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=True) 