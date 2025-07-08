"""
LangGraph エージェント間で共有される状態定義
すべてのエージェントが使用する統一 AgentState クラス
"""

from typing import Dict, List, Any, Optional, TypedDict
from datetime import datetime


class AgentState(TypedDict):
    """
    すべてのLangGraphエージェントで共通して使用する状態管理クラス
    
    Fields:
        user_query: ユーザーからの質問
        messages: 会話履歴（LLM API形式）
        intent_analysis: 意図分析結果
        search_plan: 検索計画
        search_results: Web検索結果
        final_answer: 最終回答
        thinking_log: 思考プロセスのログ
        error: エラー情報（あれば）
        session_id: セッションID（デバッグ用）
        timestamp: 開始時刻
    """
    user_query: str
    messages: List[Dict[str, str]]
    intent_analysis: Dict[str, Any]
    search_plan: Dict[str, Any]
    search_results: List[Dict[str, Any]]
    final_answer: str
    thinking_log: List[Dict[str, Any]]
    error: Optional[str]
    session_id: Optional[str]
    timestamp: Optional[str]


def create_initial_state(user_query: str, messages: Optional[List[Dict[str, str]]] = None) -> AgentState:
    """
    初期状態を作成する便利関数
    
    Args:
        user_query: ユーザーからの質問
        messages: 会話履歴（省略可）
    
    Returns:
        初期化されたAgentState
    """
    return AgentState(
        user_query=user_query,
        messages=messages or [],
        intent_analysis={},
        search_plan={},
        search_results=[],
        final_answer="",
        thinking_log=[],
        error=None,
        session_id=f"session_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
        timestamp=datetime.now().isoformat()
    )


def validate_state(state: AgentState) -> bool:
    """
    AgentState の有効性を検証
    
    Args:
        state: 検証対象のAgentState
    
    Returns:
        有効な場合True、無効な場合False
    """
    required_fields = [
        'user_query', 'messages', 'intent_analysis', 
        'search_plan', 'search_results', 'final_answer', 
        'thinking_log'
    ]
    
    for field in required_fields:
        if field not in state:
            return False
    
    # 型チェック
    if not isinstance(state['user_query'], str):
        return False
    if not isinstance(state['messages'], list):
        return False
    if not isinstance(state['thinking_log'], list):
        return False
    
    return True


def get_state_summary(state: AgentState) -> Dict[str, Any]:
    """
    AgentState の要約情報を取得
    
    Args:
        state: 要約対象のAgentState
    
    Returns:
        状態の要約情報
    """
    return {
        "session_id": state.get('session_id'),
        "user_query": state['user_query'],
        "has_intent_analysis": bool(state['intent_analysis']),
        "has_search_plan": bool(state['search_plan']),
        "search_results_count": len(state['search_results']),
        "has_final_answer": bool(state['final_answer']),
        "thinking_steps": len(state['thinking_log']),
        "has_error": state.get('error') is not None,
        "timestamp": state.get('timestamp')
    } 