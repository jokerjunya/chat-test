"""
LangGraph + LangChain を使用したRAG処理エージェント
検索 → RAG → 生成のワークフローを制御
新しいモジュール構造（tools.py, llm.py, shared_state.py）に対応
"""

import asyncio
from typing import Dict, List, Any, Optional
import json

# 新しいモジュール構造からインポート
try:
    from tools import web_search_tool, web_search_function  # 新しいツールモジュール
    from llm import OllamaLLMClient, SimpleLLMClient  # 新しいLLMモジュール  
    from shared_state import AgentState, create_initial_state  # 新しい共有状態
    from agent_pipeline import AdvancedRAGPipeline
    from thinking_callback import ThinkingCallbackManager, ThinkingIntegration
    ADVANCED_PIPELINE_AVAILABLE = True
    NEW_MODULES_AVAILABLE = True
except ImportError as e:
    print(f"新しいモジュールのインポートエラー: {e}")
    # フォールバック用の古い実装をインポート
    from ddgs import DDGS
    import httpx
    ADVANCED_PIPELINE_AVAILABLE = False
    NEW_MODULES_AVAILABLE = False


# 後方互換性のため、新しいモジュールが利用できない場合のフォールバック実装
if not NEW_MODULES_AVAILABLE:
    class SimpleOllamaLLM:
        """シンプルなOllama通信クラス（フォールバック）"""
        
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
        """Web検索関数（フォールバック）"""
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
        # 新しいモジュール構造を使用
        if NEW_MODULES_AVAILABLE:
            self.llm = SimpleLLMClient()
        else:
            self.llm = SimpleOllamaLLM()
        
        # 高度なパイプラインが利用可能な場合は初期化
        if ADVANCED_PIPELINE_AVAILABLE:
            self.advanced_pipeline = AdvancedRAGPipeline()
            self.thinking_callback_manager = ThinkingCallbackManager()
            self.thinking_integration = ThinkingIntegration(
                self.advanced_pipeline, 
                self.thinking_callback_manager
            )
        else:
            self.advanced_pipeline = None
            self.thinking_callback_manager = None
            self.thinking_integration = None
    
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
            
            # Web検索を実行（新しいモジュール構造対応）
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
    
    async def process_message_with_thinking(self, messages: List[Dict[str, Any]]) -> Dict[str, Any]:
        """高度なパイプラインを使用してメッセージを処理（思考プロセス付き）"""
        if not ADVANCED_PIPELINE_AVAILABLE or not self.thinking_integration:
            # 高度なパイプラインが利用できない場合は通常処理にフォールバック
            result = await self.process_message(messages)
            result["thinking_mode"] = "fallback"
            return result
        
        try:
            # 高度なパイプラインで処理
            result = await self.thinking_integration.process_with_thinking(messages)
            result["thinking_mode"] = "advanced"
            return result
        except Exception as e:
            # エラーが発生した場合は通常処理にフォールバック
            result = await self.process_message(messages)
            result["thinking_mode"] = "fallback_error"
            result["advanced_error"] = str(e)
            return result
    
    def get_pipeline_info(self) -> Dict[str, Any]:
        """パイプラインの情報を取得"""
        return {
            "simple_pipeline": True,
            "advanced_pipeline": ADVANCED_PIPELINE_AVAILABLE,
            "thinking_callback": self.thinking_callback_manager is not None,
            "thinking_integration": self.thinking_integration is not None
        }


# 後方互換性のためのエイリアス
RAGAgent = SimpleRAGAgent

# 新しいモジュール構造で利用可能な場合のみエクスポート
if NEW_MODULES_AVAILABLE:
    # web_search_toolは新しいtools.pyからインポート済み
    pass
else:
    # フォールバック用の web_search_tool エイリアス
    web_search_tool = web_search_function


# グローバルエージェントインスタンス
rag_agent = SimpleRAGAgent() 