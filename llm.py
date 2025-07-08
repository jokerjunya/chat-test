"""
統一されたOllama LLMクライアント
通常応答とストリーミング応答の両方をサポートする統合LLM通信モジュール
"""

import asyncio
import json
from typing import Dict, List, Any, AsyncGenerator, Optional
import httpx
from pathlib import Path


class OllamaLLMClient:
    """統一されたOllama LLMクライアント"""
    
    def __init__(self, 
                 model_name: str = "qwen3:30b", 
                 base_url: str = "http://localhost:11434",
                 timeout: float = 30.0):
        self.model_name = model_name
        self.base_url = base_url
        self.timeout = timeout
        self.default_system_prompt = self._load_default_system_prompt()
    
    def _load_default_system_prompt(self) -> str:
        """デフォルトシステムプロンプトを読み込み"""
        try:
            prompt_path = Path("prompts/system_prompt.txt")
            if prompt_path.exists():
                return prompt_path.read_text(encoding="utf-8")
            else:
                return "あなたは日本語で応答する親切なAIアシスタントです。質問に対して正確で有用な回答を提供してください。"
        except Exception as e:
            print(f"システムプロンプトの読み込みエラー: {e}")
            return "あなたは日本語で応答する親切なAIアシスタントです。質問に対して正確で有用な回答を提供してください。"
    
    async def generate_response(self, 
                              messages: List[Dict[str, str]], 
                              system_prompt: Optional[str] = None,
                              include_system: bool = True) -> str:
        """
        通常の応答を生成
        
        Args:
            messages: メッセージのリスト
            system_prompt: カスタムシステムプロンプト（Noneの場合はデフォルトを使用）
            include_system: システムプロンプトを含めるかどうか
            
        Returns:
            生成された応答文字列
        """
        try:
            # メッセージを準備
            ollama_messages = self._prepare_messages(messages, system_prompt, include_system)
            
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.base_url}/api/chat",
                    json={
                        "model": self.model_name,
                        "messages": ollama_messages,
                        "stream": False
                    },
                    timeout=self.timeout
                )
                
                if response.status_code != 200:
                    raise Exception(f"Ollama API エラー: {response.status_code}")
                
                result = response.json()
                return result["message"]["content"]
                
        except Exception as e:
            raise Exception(f"LLM生成エラー: {str(e)}")
    
    async def stream_response(self, 
                            messages: List[Dict[str, str]], 
                            system_prompt: Optional[str] = None,
                            include_system: bool = True) -> AsyncGenerator[str, None]:
        """
        ストリーミング応答を生成
        
        Args:
            messages: メッセージのリスト
            system_prompt: カスタムシステムプロンプト
            include_system: システムプロンプトを含めるかどうか
            
        Yields:
            生成されたトークンの文字列
        """
        try:
            # メッセージを準備
            ollama_messages = self._prepare_messages(messages, system_prompt, include_system)
            
            async with httpx.AsyncClient() as client:
                async with client.stream(
                    "POST",
                    f"{self.base_url}/api/chat",
                    json={
                        "model": self.model_name,
                        "messages": ollama_messages,
                        "stream": True
                    },
                    timeout=self.timeout
                ) as response:
                    if response.status_code != 200:
                        raise Exception(f"Ollama API エラー: {response.status_code}")
                    
                    async for line in response.aiter_lines():
                        if line:
                            try:
                                data = json.loads(line)
                                if "message" in data and "content" in data["message"]:
                                    content = data["message"]["content"]
                                    if content:
                                        yield content
                                
                                # ストリーミング完了を確認
                                if data.get("done", False):
                                    break
                                    
                            except json.JSONDecodeError:
                                continue
                                
        except Exception as e:
            raise Exception(f"ストリーミング生成エラー: {str(e)}")
    
    def _prepare_messages(self, 
                         messages: List[Dict[str, str]], 
                         system_prompt: Optional[str] = None,
                         include_system: bool = True) -> List[Dict[str, str]]:
        """
        Ollama用のメッセージフォーマットを準備
        
        Args:
            messages: 元のメッセージリスト
            system_prompt: カスタムシステムプロンプト
            include_system: システムプロンプトを含めるかどうか
            
        Returns:
            Ollama用にフォーマットされたメッセージリスト
        """
        ollama_messages = []
        
        # システムプロンプトを追加
        if include_system:
            prompt = system_prompt if system_prompt is not None else self.default_system_prompt
            if prompt:
                ollama_messages.append({
                    "role": "system",
                    "content": prompt
                })
        
        # 既存のメッセージを追加
        ollama_messages.extend(messages)
        
        return ollama_messages
    
    async def health_check(self) -> bool:
        """
        Ollamaサーバーのヘルスチェック
        
        Returns:
            サーバーが利用可能かどうか
        """
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(f"{self.base_url}/api/version", timeout=5.0)
                return response.status_code == 200
        except:
            return False
    
    async def get_model_info(self) -> Dict[str, Any]:
        """
        使用中のモデル情報を取得
        
        Returns:
            モデル情報の辞書
        """
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.base_url}/api/show",
                    json={"name": self.model_name},
                    timeout=10.0
                )
                
                if response.status_code == 200:
                    return response.json()
                else:
                    return {"error": f"モデル情報取得エラー: {response.status_code}"}
                    
        except Exception as e:
            return {"error": f"モデル情報取得エラー: {str(e)}"}


class SimpleLLMClient:
    """シンプルなLLMクライアント（後方互換性用）"""
    
    def __init__(self, model_name: str = "qwen3:30b", base_url: str = "http://localhost:11434"):
        self.client = OllamaLLMClient(model_name, base_url)
    
    async def generate_response(self, messages: List[Dict[str, str]]) -> str:
        """後方互換性のための簡単なインターフェース"""
        return await self.client.generate_response(messages)


# グローバルインスタンス
default_llm_client = OllamaLLMClient()
simple_llm_client = SimpleLLMClient()


# 便利な関数群
async def generate_llm_response(messages: List[Dict[str, str]], 
                              model_name: str = "qwen3:30b",
                              system_prompt: Optional[str] = None) -> str:
    """簡単なLLM応答生成"""
    client = OllamaLLMClient(model_name)
    return await client.generate_response(messages, system_prompt)


async def stream_llm_response(messages: List[Dict[str, str]], 
                            model_name: str = "qwen3:30b",
                            system_prompt: Optional[str] = None) -> AsyncGenerator[str, None]:
    """簡単なLLMストリーミング応答生成"""
    client = OllamaLLMClient(model_name)
    async for token in client.stream_response(messages, system_prompt):
        yield token


async def check_ollama_health() -> bool:
    """Ollamaサーバーのヘルスチェック"""
    return await default_llm_client.health_check()


# エイリアス（後方互換性）
SimpleOllamaLLM = SimpleLLMClient 