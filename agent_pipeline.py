"""
LangGraph DAG を使用した段階的思考プロセスの実装
Intent Analysis → Search Plan → Search → Answer の流れを制御
"""

import asyncio
import json
from typing import Dict, List, Any, Optional, TypedDict, Annotated
from datetime import datetime
import httpx
from ddgs import DDGS
import time
from pathlib import Path


class AgentState(TypedDict):
    """エージェントの状態を管理するクラス"""
    user_query: str
    messages: List[Dict[str, str]]
    intent_analysis: Dict[str, Any]
    search_plan: Dict[str, Any]
    search_results: List[Dict[str, Any]]
    final_answer: str
    thinking_log: List[Dict[str, Any]]
    error: Optional[str]


class AdvancedRAGPipeline:
    """LangGraph DAG を使用した高度なRAGパイプライン"""
    
    def __init__(self, model_name: str = "qwen3:30b", base_url: str = "http://localhost:11434"):
        self.model_name = model_name
        self.base_url = base_url
        self.thinking_log = []
        
        # システムプロンプトを読み込み
        self.system_prompt = self._load_system_prompt()
    
    def _load_system_prompt(self) -> str:
        """システムプロンプトを読み込み"""
        try:
            prompt_path = Path("prompts/system_prompt.txt")
            if prompt_path.exists():
                return prompt_path.read_text(encoding="utf-8")
            else:
                return "あなたは日本語で応答する親切なAIアシスタントです。"
        except Exception as e:
            print(f"システムプロンプトの読み込みエラー: {e}")
            return "あなたは日本語で応答する親切なAIアシスタントです。"
    
    async def _call_llm(self, messages: List[Dict[str, str]]) -> str:
        """LLMを呼び出し"""
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
            raise Exception(f"LLM呼び出しエラー: {str(e)}")
    
    async def _web_search_with_retry(self, query: str, max_results: int = 5, max_retries: int = 3) -> List[Dict]:
        """リトライ機能付きのWeb検索"""
        for attempt in range(max_retries):
            try:
                # 日本語検索を優先
                search_query = f"{query} lang:ja"
                results = []
                
                with DDGS() as ddgs:
                    for result in ddgs.text(search_query, max_results=max_results):
                        results.append({
                            "title": result.get("title", ""),
                            "url": result.get("href", ""),
                            "snippet": result.get("body", "")
                        })
                
                # 日本語検索で結果が少ない場合は英語でも検索
                if len(results) < max_results:
                    with DDGS() as ddgs:
                        for result in ddgs.text(query, max_results=max_results-len(results)):
                            results.append({
                                "title": result.get("title", ""),
                                "url": result.get("href", ""),
                                "snippet": result.get("body", "")
                            })
                
                return results if results else []
                
            except Exception as e:
                if attempt < max_retries - 1:
                    await asyncio.sleep(1)  # 1秒待機してリトライ
                    continue
                else:
                    return [{
                        "title": "検索エラー",
                        "url": "",
                        "snippet": f"検索中にエラーが発生しました（{attempt + 1}/{max_retries}回試行）: {str(e)}"
                    }]
    
    async def intent_analysis_node(self, state: AgentState) -> AgentState:
        """意図分析ノード"""
        start_time = time.time()
        
        try:
            analysis_prompt = f"""
ユーザーの質問を分析してください：
「{state['user_query']}」

以下の観点で分析してください：
1. 質問の種類（事実確認、説明要求、意見求め、手順説明など）
2. 必要な情報の種類
3. 検索が必要かどうか
4. 回答の複雑さの予測

JSON形式で回答してください：
{{
    "question_type": "質問の種類",
    "required_info": ["必要な情報1", "必要な情報2"],
    "needs_search": true/false,
    "complexity": "simple/medium/complex",
    "analysis": "詳細な分析"
}}
"""
            
            messages = [
                {"role": "system", "content": "あなたは質問分析の専門家です。"},
                {"role": "user", "content": analysis_prompt}
            ]
            
            response = await self._call_llm(messages)
            
            # JSON解析を試行
            try:
                intent_data = json.loads(response)
            except json.JSONDecodeError:
                # JSON解析に失敗した場合はテキスト解析
                intent_data = {
                    "question_type": "general",
                    "required_info": ["general_information"],
                    "needs_search": True,
                    "complexity": "medium",
                    "analysis": response
                }
            
            # 思考ログに記録
            thinking_entry = {
                "step": "intent_analysis",
                "timestamp": datetime.now().isoformat(),
                "duration": time.time() - start_time,
                "input": state['user_query'],
                "output": intent_data,
                "raw_response": response
            }
            
            state['thinking_log'].append(thinking_entry)
            state['intent_analysis'] = intent_data
            
            return state
            
        except Exception as e:
            error_entry = {
                "step": "intent_analysis",
                "timestamp": datetime.now().isoformat(),
                "duration": time.time() - start_time,
                "error": str(e)
            }
            state['thinking_log'].append(error_entry)
            state['error'] = f"意図分析エラー: {str(e)}"
            return state
    
    async def search_plan_node(self, state: AgentState) -> AgentState:
        """検索計画ノード"""
        start_time = time.time()
        
        try:
            if not state['intent_analysis'].get('needs_search', True):
                # 検索が不要な場合はスキップ
                state['search_plan'] = {
                    "keywords": [],
                    "search_needed": False,
                    "reason": "検索が不要な質問"
                }
                return state
            
            plan_prompt = f"""
以下の質問に対する検索計画を立ててください：
質問: {state['user_query']}
意図分析: {state['intent_analysis']['analysis']}

検索キーワードと戦略をJSON形式で回答してください：
{{
    "keywords": ["キーワード1", "キーワード2"],
    "search_strategy": "検索戦略の説明",
    "expected_info": ["期待する情報1", "期待する情報2"],
    "search_needed": true
}}
"""
            
            messages = [
                {"role": "system", "content": "あなたは検索戦略の専門家です。"},
                {"role": "user", "content": plan_prompt}
            ]
            
            response = await self._call_llm(messages)
            
            # JSON解析を試行
            try:
                plan_data = json.loads(response)
            except json.JSONDecodeError:
                # JSON解析に失敗した場合はフォールバック
                plan_data = {
                    "keywords": [state['user_query']],
                    "search_strategy": "基本的な検索戦略",
                    "expected_info": ["関連情報"],
                    "search_needed": True
                }
            
            # 思考ログに記録
            thinking_entry = {
                "step": "search_plan",
                "timestamp": datetime.now().isoformat(),
                "duration": time.time() - start_time,
                "input": state['user_query'],
                "output": plan_data,
                "raw_response": response
            }
            
            state['thinking_log'].append(thinking_entry)
            state['search_plan'] = plan_data
            
            return state
            
        except Exception as e:
            error_entry = {
                "step": "search_plan",
                "timestamp": datetime.now().isoformat(),
                "duration": time.time() - start_time,
                "error": str(e)
            }
            state['thinking_log'].append(error_entry)
            state['error'] = f"検索計画エラー: {str(e)}"
            return state
    
    async def search_node(self, state: AgentState) -> AgentState:
        """検索実行ノード"""
        start_time = time.time()
        
        try:
            if not state['search_plan'].get('search_needed', True):
                state['search_results'] = []
                return state
            
            # 検索キーワードを取得
            keywords = state['search_plan'].get('keywords', [state['user_query']])
            all_results = []
            
            # 各キーワードで検索実行
            for keyword in keywords[:2]:  # 最大2つのキーワード
                search_results = await self._web_search_with_retry(keyword)
                all_results.extend(search_results)
            
            # 重複排除（URLベース）
            unique_results = []
            seen_urls = set()
            for result in all_results:
                url = result.get('url', '')
                if url and url not in seen_urls:
                    seen_urls.add(url)
                    unique_results.append(result)
            
            # 上位5件に制限
            search_results = unique_results[:5]
            
            # 思考ログに記録
            thinking_entry = {
                "step": "search",
                "timestamp": datetime.now().isoformat(),
                "duration": time.time() - start_time,
                "input": keywords,
                "output": {
                    "results_count": len(search_results),
                    "results": search_results
                }
            }
            
            state['thinking_log'].append(thinking_entry)
            state['search_results'] = search_results
            
            return state
            
        except Exception as e:
            error_entry = {
                "step": "search",
                "timestamp": datetime.now().isoformat(),
                "duration": time.time() - start_time,
                "error": str(e)
            }
            state['thinking_log'].append(error_entry)
            state['error'] = f"検索実行エラー: {str(e)}"
            return state
    
    async def answer_node(self, state: AgentState) -> AgentState:
        """回答生成ノード"""
        start_time = time.time()
        
        try:
            # 検索結果をコンテキストに整理
            context_parts = []
            for i, result in enumerate(state['search_results'], 1):
                context_parts.append(f"""
検索結果 {i}:
タイトル: {result.get('title', 'N/A')}
URL: {result.get('url', 'N/A')}
内容: {result.get('snippet', 'N/A')}
""")
            
            context = "\n".join(context_parts) if context_parts else "検索結果がありません。"
            
            # 回答生成プロンプト
            answer_prompt = f"""
以下の情報を基に、ユーザーの質問に答えてください：

質問: {state['user_query']}
意図分析: {state['intent_analysis']}
検索結果: {context}

段階的な思考プロセスを<think>タグ内で示してから、最終的な回答を提供してください。
"""
            
            messages = [
                {"role": "system", "content": self.system_prompt},
                {"role": "user", "content": answer_prompt}
            ]
            
            response = await self._call_llm(messages)
            
            # 思考ログに記録
            thinking_entry = {
                "step": "answer",
                "timestamp": datetime.now().isoformat(),
                "duration": time.time() - start_time,
                "input": state['user_query'],
                "output": response,
                "context_length": len(context)
            }
            
            state['thinking_log'].append(thinking_entry)
            state['final_answer'] = response
            
            return state
            
        except Exception as e:
            error_entry = {
                "step": "answer",
                "timestamp": datetime.now().isoformat(),
                "duration": time.time() - start_time,
                "error": str(e)
            }
            state['thinking_log'].append(error_entry)
            state['error'] = f"回答生成エラー: {str(e)}"
            return state
    
    async def process_message(self, messages: List[Dict[str, Any]]) -> Dict[str, Any]:
        """メッセージを段階的に処理"""
        # 最後のメッセージを質問として取得
        last_message = messages[-1] if messages else {}
        user_query = last_message.get("content", "")
        
        if not user_query:
            return {
                "success": False,
                "error": "メッセージが空です",
                "response": "質問を入力してください。"
            }
        
        # 状態を初期化
        state: AgentState = {
            "user_query": user_query,
            "messages": messages,
            "intent_analysis": {},
            "search_plan": {},
            "search_results": [],
            "final_answer": "",
            "thinking_log": [],
            "error": None
        }
        
        try:
            # 段階的処理の実行
            state = await self.intent_analysis_node(state)
            if state.get('error'):
                return {"success": False, "error": state['error'], "thinking_log": state['thinking_log']}
            
            state = await self.search_plan_node(state)
            if state.get('error'):
                return {"success": False, "error": state['error'], "thinking_log": state['thinking_log']}
            
            state = await self.search_node(state)
            if state.get('error'):
                return {"success": False, "error": state['error'], "thinking_log": state['thinking_log']}
            
            state = await self.answer_node(state)
            if state.get('error'):
                return {"success": False, "error": state['error'], "thinking_log": state['thinking_log']}
            
            return {
                "success": True,
                "response": state['final_answer'],
                "search_results": state['search_results'],
                "thinking_log": state['thinking_log'],
                "intent_analysis": state['intent_analysis'],
                "search_plan": state['search_plan']
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": f"パイプライン実行エラー: {str(e)}",
                "thinking_log": state.get('thinking_log', [])
            }


# グローバルインスタンス
rag_pipeline = AdvancedRAGPipeline() 