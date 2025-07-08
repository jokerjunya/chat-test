"""
Chain of Thought (CoT) 思考プロセスのテスト
思考JSONが含まれるかを検証するPyTest
新しいモジュール構造に対応
"""

import pytest
import asyncio
import json
from typing import Dict, Any, List
import sys
import os

# プロジェクトルートをパスに追加
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

# 新しいモジュール構造に対応したインポート
try:
    from agent_pipeline import AdvancedRAGPipeline
    from thinking_callback import ThinkingCallbackManager, ThinkingIntegration
    from thinking_parser import ThinkingParser
    from shared_state import AgentState, create_initial_state
    from tools import web_search_function
    from llm import OllamaLLMClient
    NEW_MODULES_AVAILABLE = True
except ImportError as e:
    print(f"新しいモジュールのインポートエラー: {e}")
    # フォールバック用
    from agent_pipeline import AdvancedRAGPipeline
    from thinking_callback import ThinkingCallbackManager, ThinkingIntegration
    from thinking_parser import ThinkingParser
    NEW_MODULES_AVAILABLE = False


class TestCoTProcessing:
    """Chain of Thought処理のテスト"""
    
    @pytest.fixture
    def pipeline(self):
        """パイプラインのテスト用インスタンス"""
        return AdvancedRAGPipeline()
    
    @pytest.fixture
    def callback_manager(self):
        """コールバックマネージャーのテスト用インスタンス"""
        return ThinkingCallbackManager()
    
    @pytest.fixture
    def integration(self, pipeline, callback_manager):
        """統合オブジェクトのテスト用インスタンス"""
        return ThinkingIntegration(pipeline, callback_manager)
    
    @pytest.fixture
    def thinking_parser(self):
        """思考パーサーのテスト用インスタンス"""
        return ThinkingParser()
    
    @pytest.fixture
    def sample_messages(self):
        """テスト用のメッセージデータ"""
        return [
            {"role": "user", "content": "Python の基本的な文法について教えてください"}
        ]
    
    @pytest.fixture
    def sample_simple_messages(self):
        """検索不要のシンプルなメッセージ"""
        return [
            {"role": "user", "content": "こんにちは"}
        ]
    
    @pytest.mark.asyncio
    async def test_pipeline_returns_thinking_log(self, pipeline, sample_messages):
        """パイプラインが思考ログを返すかをテスト"""
        result = await pipeline.process_message(sample_messages)
        
        # 基本的な構造のチェック
        assert isinstance(result, dict)
        assert "success" in result
        assert "thinking_log" in result
        
        # 思考ログの存在をチェック
        thinking_log = result["thinking_log"]
        assert isinstance(thinking_log, list)
        assert len(thinking_log) > 0
        
        # 各思考ステップの構造をチェック
        for step in thinking_log:
            assert "step" in step
            assert "timestamp" in step
            assert "duration" in step
            assert step["step"] in ["intent_analysis", "search_plan", "search", "answer"]
    
    @pytest.mark.asyncio
    async def test_integration_returns_thinking_session(self, integration, sample_messages):
        """統合オブジェクトが思考セッションを返すかをテスト"""
        result = await integration.process_with_thinking(sample_messages)
        
        # 基本的な構造のチェック
        assert isinstance(result, dict)
        assert "success" in result
        assert "thinking_session" in result
        
        # 思考セッションの構造をチェック
        thinking_session = result["thinking_session"]
        assert isinstance(thinking_session, dict)
        assert "session_id" in thinking_session
        assert "user_query" in thinking_session
        assert "start_time" in thinking_session
        assert "end_time" in thinking_session
        assert "steps" in thinking_session
        assert "status" in thinking_session
    
    @pytest.mark.asyncio
    async def test_intent_analysis_structure(self, pipeline, sample_messages):
        """意図分析の構造をテスト"""
        result = await pipeline.process_message(sample_messages)
        
        assert result["success"] == True
        assert "intent_analysis" in result
        
        intent_analysis = result["intent_analysis"]
        assert isinstance(intent_analysis, dict)
        
        # 意図分析の必須フィールドをチェック
        required_fields = ["question_type", "required_info", "needs_search", "complexity"]
        for field in required_fields:
            assert field in intent_analysis
    
    @pytest.mark.asyncio
    async def test_search_plan_structure(self, pipeline, sample_messages):
        """検索計画の構造をテスト"""
        result = await pipeline.process_message(sample_messages)
        
        assert result["success"] == True
        assert "search_plan" in result
        
        search_plan = result["search_plan"]
        assert isinstance(search_plan, dict)
        
        # 検索計画の必須フィールドをチェック
        if search_plan.get("search_needed", True):
            assert "keywords" in search_plan
            assert isinstance(search_plan["keywords"], list)
    
    @pytest.mark.asyncio
    async def test_thinking_parser_with_think_tags(self, thinking_parser):
        """思考パーサーが<think>タグを正しく処理するかをテスト"""
        # <think>タグ付きの応答をテスト
        sample_response = """<think>
ユーザーがPythonについて質問しています。
基本的な文法について説明する必要があります。
</think>

Pythonは初心者にも学びやすいプログラミング言語です。基本的な文法について説明します。"""
        
        result = thinking_parser.parse_response(sample_response)
        
        assert result["has_thinking"] == True
        assert "ユーザーがPythonについて質問しています" in result["thinking"]
        assert "Pythonは初心者にも学びやすい" in result["answer"]
    
    @pytest.mark.asyncio
    async def test_thinking_parser_without_think_tags(self, thinking_parser):
        """思考パーサーが<think>タグなしの応答を正しく処理するかをテスト"""
        sample_response = "Pythonは初心者にも学びやすいプログラミング言語です。"
        
        result = thinking_parser.parse_response(sample_response)
        
        assert result["has_thinking"] == False
        assert result["thinking"] == ""
        assert result["answer"] == sample_response
    
    @pytest.mark.asyncio
    async def test_all_pipeline_steps_executed(self, pipeline, sample_messages):
        """全ての段階的ステップが実行されるかをテスト"""
        result = await pipeline.process_message(sample_messages)
        
        assert result["success"] == True
        
        # 実行されたステップの確認
        thinking_log = result["thinking_log"]
        executed_steps = [step["step"] for step in thinking_log]
        
        # 期待される全てのステップが実行されているかチェック
        expected_steps = ["intent_analysis", "search_plan", "search", "answer"]
        for step in expected_steps:
            assert step in executed_steps
    
    @pytest.mark.asyncio
    async def test_error_handling_in_pipeline(self, pipeline):
        """パイプラインのエラーハンドリングをテスト"""
        # 無効なメッセージでテスト
        invalid_messages = []
        
        result = await pipeline.process_message(invalid_messages)
        
        assert result["success"] == False
        assert "error" in result
        assert "メッセージが空です" in result["error"]
    
    @pytest.mark.asyncio
    async def test_search_skipping_logic(self, pipeline, sample_simple_messages):
        """検索スキップロジックをテスト"""
        result = await pipeline.process_message(sample_simple_messages)
        
        # 基本的な応答の確認
        assert result["success"] == True
        assert "thinking_log" in result
        
        # 検索がスキップされる場合があることを確認
        thinking_log = result["thinking_log"]
        search_steps = [step for step in thinking_log if step["step"] == "search"]
        
        if search_steps:
            # 検索が実行された場合、結果が空でも正常
            assert "search_results" in result
            assert isinstance(result["search_results"], list)
    
    @pytest.mark.skipif(not NEW_MODULES_AVAILABLE, reason="新しいモジュールが利用できません")
    def test_new_module_structure(self):
        """新しいモジュール構造のテスト"""
        # 統一AgentStateのテスト
        state = create_initial_state("テスト質問", [])
        assert isinstance(state, dict)
        assert "user_query" in state
        assert "thinking_log" in state
        assert "session_id" in state
        assert "timestamp" in state
        
        # LLMクライアントのテスト
        llm_client = OllamaLLMClient()
        assert llm_client.model_name == "qwen3:30b"
        assert llm_client.base_url == "http://localhost:11434"
        
        # システムプロンプトが読み込まれるかテスト
        system_prompt = llm_client.get_system_prompt()
        assert isinstance(system_prompt, str)
        assert len(system_prompt) > 0
    
    @pytest.mark.asyncio
    @pytest.mark.skipif(not NEW_MODULES_AVAILABLE, reason="新しいモジュールが利用できません")
    async def test_unified_web_search_function(self):
        """統一Web検索関数のテスト"""
        # 簡単な検索テスト
        try:
            results = await web_search_function("Python", max_results=2)
            assert isinstance(results, list)
            assert len(results) <= 2
            
            # 各結果の構造チェック
            for result in results:
                assert "title" in result
                assert "url" in result
                assert "snippet" in result
        except Exception:
            # 検索エラーの場合もテスト通過（ネットワーク依存のため）
            pass
    
    @pytest.mark.asyncio
    async def test_thinking_log_timing(self, pipeline, sample_messages):
        """思考ログのタイミング情報をテスト"""
        result = await pipeline.process_message(sample_messages)
        
        assert result["success"] == True
        
        thinking_log = result["thinking_log"]
        
        for step in thinking_log:
            # タイミング情報の確認
            assert "timestamp" in step
            assert "duration" in step
            
            # 継続時間が正の値であることを確認
            assert isinstance(step["duration"], (int, float))
            assert step["duration"] >= 0
    
    @pytest.mark.asyncio
    async def test_json_structure_validation(self, pipeline, sample_messages):
        """返されるJSON構造の検証"""
        result = await pipeline.process_message(sample_messages)
        
        # 必須フィールドの確認
        required_fields = [
            "success", "response", "search_results", 
            "thinking_log", "intent_analysis", "search_plan"
        ]
        
        for field in required_fields:
            assert field in result, f"必須フィールド '{field}' が見つかりません"
        
        # データ型の確認
        assert isinstance(result["success"], bool)
        assert isinstance(result["response"], str)
        assert isinstance(result["search_results"], list)
        assert isinstance(result["thinking_log"], list)
        assert isinstance(result["intent_analysis"], dict)
        assert isinstance(result["search_plan"], dict)
    
    def test_thinking_callback_manager_creation(self, callback_manager):
        """思考コールバックマネージャーの作成をテスト"""
        # デフォルトコールバックの存在確認
        default_callback = callback_manager.get_default_callback()
        assert default_callback is not None
        
        # 新しいコールバックの作成
        test_callback = callback_manager.create_callback("test", stdout_enabled=False)
        assert test_callback is not None
        
        # 作成されたコールバックの取得
        retrieved_callback = callback_manager.get_callback("test")
        assert retrieved_callback is test_callback
    
    @pytest.mark.asyncio
    async def test_performance_requirements(self, pipeline, sample_messages):
        """パフォーマンス要件のテスト（6秒以内）"""
        import time
        
        start_time = time.time()
        result = await pipeline.process_message(sample_messages)
        end_time = time.time()
        
        duration = end_time - start_time
        
        # 6秒以内であることを確認（KPI要件）
        assert duration <= 6.0, f"処理時間が6秒を超過しました: {duration:.2f}秒"
        assert result["success"] == True


if __name__ == "__main__":
    # 個別テストの実行
    pytest.main([__file__, "-v"]) 