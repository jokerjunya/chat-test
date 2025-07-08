"""
LangGraph + LangChain を使用したRAG処理エージェント
検索 → RAG → 生成のワークフローを制御
"""

import asyncio
from typing import Dict, List, Any, Optional
import json
import httpx
from ddgs import DDGS


class SimpleOllamaLLM:
    """シンプルなOllama通信クラス"""
    
    def __init__(self, model_name: str = "qwen3:30b", base_url: str = "http://localhost:11434"):
        self.model_name = model_name
        self.base_url = base_url
    
    async def generate_response(self, messages: List[Dict[str, str]]) -> str:
        """非同期でOllamaからレスポンスを生成"""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.base_url}/api/chat",
                    json={
                        "model": self.model_name,
                        "messages": messages,
                        "stream": False
                    },
                    timeout=30.0
                )
                
                if response.status_code != 200:
                    raise Exception(f"Ollama API エラー: {response.status_code}")
                
                result = response.json()
                return result["message"]["content"]
                
        except Exception as e:
            raise Exception(f"LLM生成エラー: {str(e)}")


async def web_search_function(query: str, max_results: int = 5) -> List[Dict]:
    """Web検索関数（ツールデコレータを使わない直接実装）"""
    try:
        search_query = f"{query} lang:ja"
        results = []
        
        with DDGS() as ddgs:
            for result in ddgs.text(search_query, max_results=max_results):
                results.append({
                    "title": result.get("title", ""),
                    "url": result.get("href", ""),
                    "snippet": result.get("body", "")
                })
        
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
        return [{"title": "検索エラー", "url": "", "snippet": f"検索中にエラーが発生しました: {str(e)}"}]


class SimpleRAGAgent:
    """シンプルなRAG処理エージェント（LangGraphを使わない直接実装）"""
    
    def __init__(self):
        self.llm = SimpleOllamaLLM()
    
    async def process_message(self, messages: List[Dict[str, Any]]) -> Dict[str, Any]:
        """メッセージを処理してレスポンスを生成"""
        try:
            # 1. 検索フェーズ
            last_message = messages[-1] if messages else {}
            query = last_message.get("content", "")
            
            if not query:
                return {
                    "success": False,
                    "error": "メッセージが空です",
                    "response": "質問を入力してください。"
                }
            
            # Web検索を実行
            search_results = await web_search_function(query)
            
            # 2. コンテキスト化フェーズ
            context_parts = []
            for i, result in enumerate(search_results[:3], 1):  # 上位3件
                context_parts.append(f"""
検索結果 {i}:
タイトル: {result.get('title', 'N/A')}
URL: {result.get('url', 'N/A')}
内容: {result.get('snippet', 'N/A')}
""")
            
            context = "\n".join(context_parts)
            
            # 3. 生成フェーズ
            # システムプロンプトを含むメッセージを構築
            system_message = {
                "role": "system",
                "content": f"""あなたは日本語で応答する親切なAIアシスタントです。
以下の検索結果を参考にして、ユーザーの質問に正確で有用な回答を提供してください。
検索結果に関連する情報がない場合は、一般的な知識で回答してください。

検索結果:
{context}"""
            }
            
            # メッセージを構築
            llm_messages = [system_message] + messages
            
            # LLMで応答生成
            response = await self.llm.generate_response(llm_messages)
            
            return {
                "success": True,
                "response": response,
                "search_results": search_results,
                "context": context
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "response": "申し訳ございません。処理中にエラーが発生しました。"
            }


# グローバルエージェントインスタンス
rag_agent = SimpleRAGAgent() 