"""
ストリーミング応答エージェント
WebSocketでリアルタイムトークンストリーミングを提供
新しいモジュール構造（tools.py, llm.py）に対応
"""

import asyncio
import json
from typing import Dict, List, Any, AsyncGenerator

# 新しいモジュール構造からインポート
try:
    from tools import web_search_function
    from llm import OllamaLLMClient
    NEW_MODULES_AVAILABLE = True
except ImportError:
    print("新しいモジュールが利用できません。フォールバック実装を使用します。")
    # フォールバック用の古い実装をインポート
    import httpx
    from ddgs import DDGS
    from langgraph_agent import web_search_function
    NEW_MODULES_AVAILABLE = False


class StreamingAgent:
    """ストリーミング応答エージェント"""
    
    def __init__(self, model_name: str = "qwen3:30b"):
        self.model_name = model_name
        self.base_url = "http://localhost:11434"
        
        # 新しいモジュール構造を使用
        if NEW_MODULES_AVAILABLE:
            self.llm_client = OllamaLLMClient(model_name=model_name)
        else:
            self.llm_client = None
    
    async def stream_ollama_response(self, messages: List[Dict[str, Any]]) -> AsyncGenerator[str, None]:
        """Ollamaからストリーミング応答を取得"""
        try:
            # 新しいモジュール構造を使用
            if NEW_MODULES_AVAILABLE and self.llm_client:
                # 新しいLLMクライアントを使用してストリーミング
                async for token in self.llm_client.stream_response(messages):
                    yield token
            else:
                # フォールバック実装
                async for token in self._fallback_stream_response(messages):
                    yield token
                
        except Exception as e:
            yield f"エラー: {str(e)}"
    
    async def _fallback_stream_response(self, messages: List[Dict[str, Any]]) -> AsyncGenerator[str, None]:
        """フォールバック用のストリーミング応答"""
        try:
            # システムプロンプトを追加
            system_prompt = {
                "role": "system",
                "content": "あなたは日本語で応答する親切なAIアシスタントです。質問に対して正確で有用な回答を提供してください。"
            }
            
            ollama_messages = [system_prompt] + messages
            
            async with httpx.AsyncClient() as client:
                async with client.stream(
                    "POST",
                    f"{self.base_url}/api/chat",
                    json={
                        "model": self.model_name,
                        "messages": ollama_messages,
                        "stream": True
                    },
                    timeout=60.0
                ) as response:
                    if response.status_code != 200:
                        yield f"エラー: Ollama API エラー ({response.status_code})"
                        return
                    
                    async for line in response.aiter_lines():
                        if line.strip():
                            try:
                                data = json.loads(line)
                                if "message" in data and "content" in data["message"]:
                                    content = data["message"]["content"]
                                    if content:
                                        yield content
                                
                                # 応答が完了したかチェック
                                if data.get("done", False):
                                    break
                                    
                            except json.JSONDecodeError:
                                continue
                                
        except httpx.TimeoutException:
            yield "エラー: タイムアウトが発生しました"
        except Exception as e:
            yield f"エラー: {str(e)}"
    
    async def process_with_streaming(self, messages: List[Dict[str, Any]]) -> Dict[str, Any]:
        """メッセージを処理してストリーミング準備"""
        try:
            # 最後のメッセージから検索クエリを抽出
            last_message = messages[-1] if messages else {}
            query = last_message.get("content", "")
            
            # Web検索を実行
            search_results = await web_search_function(query)
            
            # 検索結果をコンテキストに変換
            context_parts = []
            for i, result in enumerate(search_results[:3], 1):
                context_parts.append(f"""
検索結果 {i}:
タイトル: {result.get('title', 'N/A')}
URL: {result.get('url', 'N/A')}
内容: {result.get('snippet', 'N/A')}
""")
            
            context = "\n".join(context_parts)
            
            # コンテキスト付きプロンプトを作成
            enhanced_messages = [
                {
                    "role": "system",
                    "content": f"""以下の検索結果を参考にして、ユーザーの質問に正確で有用な回答を提供してください。
検索結果に関連する情報がない場合は、一般的な知識で回答してください。

検索結果:
{context}"""
                }
            ] + messages
            
            return {
                "success": True,
                "messages": enhanced_messages,
                "search_results": search_results
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "messages": messages,
                "search_results": []
            }
    
    async def stream_response(self, messages: List[Dict[str, Any]]) -> AsyncGenerator[Dict[str, Any], None]:
        """完全なストリーミング応答処理"""
        try:
            # 検索と前処理
            yield {"type": "status", "content": "検索中..."}
            
            processed = await self.process_with_streaming(messages)
            
            if not processed["success"]:
                yield {"type": "error", "content": processed["error"]}
                return
            
            # 検索結果を送信
            yield {
                "type": "search_results",
                "content": processed["search_results"]
            }
            
            # 生成開始
            yield {"type": "status", "content": "回答を生成中..."}
            
            # ストリーミング応答
            full_response = ""
            async for token in self.stream_ollama_response(processed["messages"]):
                if token.startswith("エラー:"):
                    yield {"type": "error", "content": token}
                    return
                
                full_response += token
                yield {"type": "token", "content": token}
            
            # 完了通知
            yield {
                "type": "completed",
                "content": full_response,
                "search_results": processed["search_results"]
            }
            
        except Exception as e:
            yield {"type": "error", "content": f"処理エラー: {str(e)}"}


# グローバルストリーミングエージェントインスタンス
streaming_agent = StreamingAgent() 