"""
統一されたWeb検索ツール
LangChain @tool デコレータを使用して、全システムで共通のWeb検索機能を提供
"""

import asyncio
from typing import Dict, List, Any
from langchain.tools import tool
from ddgs import DDGS


@tool
async def web_search_tool(query: str, max_results: int = 5) -> List[Dict[str, Any]]:
    """
    DuckDuckGo を使用してWeb検索を実行する統一ツール
    
    Args:
        query: 検索クエリ
        max_results: 最大検索結果数（デフォルト: 5）
        
    Returns:
        検索結果のリスト。各結果は title, url, snippet を含む辞書
    """
    return await web_search_with_retry(query, max_results, max_retries=3)


async def web_search_with_retry(query: str, max_results: int = 5, max_retries: int = 3) -> List[Dict[str, Any]]:
    """
    リトライ機能付きのWeb検索実装
    
    Args:
        query: 検索クエリ
        max_results: 最大検索結果数
        max_retries: 最大リトライ回数
        
    Returns:
        検索結果のリスト
    """
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


# 後方互換性のための関数エイリアス
async def web_search_function(query: str, max_results: int = 5) -> List[Dict]:
    """
    後方互換性のための関数エイリアス
    既存コードとの互換性を維持するため、@toolデコレータなしの関数も提供
    """
    return await web_search_with_retry(query, max_results)


# LangChain統合用ツールリスト
AVAILABLE_TOOLS = [web_search_tool]


def get_search_tools() -> List:
    """検索ツールのリストを取得"""
    return AVAILABLE_TOOLS


def get_tool_by_name(name: str):
    """名前でツールを取得"""
    tool_map = {
        "web_search_tool": web_search_tool,
        "web_search": web_search_tool  # エイリアス
    }
    return tool_map.get(name) 