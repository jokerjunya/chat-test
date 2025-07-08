"""
思考プロセスのコールバック機能
中間思考JSONをstdoutとAPIに渡すためのコールバック処理
"""

import json
import sys
from typing import Dict, Any, List, Optional, Callable
from datetime import datetime
import asyncio
from pathlib import Path


class ThinkingCallback:
    """思考プロセスのコールバック管理クラス"""
    
    def __init__(self, 
                 stdout_enabled: bool = True,
                 file_logging: bool = False,
                 log_file: str = "thinking_logs.json"):
        self.stdout_enabled = stdout_enabled
        self.file_logging = file_logging
        self.log_file = log_file
        self.callbacks: List[Callable] = []
        self.current_session = None
        
    def add_callback(self, callback: Callable):
        """コールバック関数を追加"""
        self.callbacks.append(callback)
    
    def remove_callback(self, callback: Callable):
        """コールバック関数を削除"""
        if callback in self.callbacks:
            self.callbacks.remove(callback)
    
    def start_session(self, session_id: str, user_query: str):
        """思考セッションを開始"""
        self.current_session = {
            "session_id": session_id,
            "user_query": user_query,
            "start_time": datetime.now().isoformat(),
            "steps": [],
            "status": "started"
        }
        
        self._log_to_stdout("SESSION_START", {
            "session_id": session_id,
            "user_query": user_query,
            "timestamp": self.current_session["start_time"]
        })
    
    def log_step(self, step_name: str, step_data: Dict[str, Any]):
        """思考ステップをログに記録"""
        if not self.current_session:
            return
        
        step_entry = {
            "step": step_name,
            "timestamp": datetime.now().isoformat(),
            "data": step_data
        }
        
        self.current_session["steps"].append(step_entry)
        
        # stdoutに出力
        self._log_to_stdout(f"STEP_{step_name.upper()}", step_data)
        
        # 登録されたコールバックを呼び出し
        for callback in self.callbacks:
            try:
                callback(step_name, step_data)
            except Exception as e:
                self._log_to_stdout("CALLBACK_ERROR", {
                    "error": str(e),
                    "step": step_name
                })
    
    def end_session(self, final_response: str, success: bool = True):
        """思考セッションを終了"""
        if not self.current_session:
            return
        
        self.current_session["end_time"] = datetime.now().isoformat()
        self.current_session["final_response"] = final_response
        self.current_session["status"] = "completed" if success else "failed"
        
        # 最終ログを出力
        self._log_to_stdout("SESSION_END", {
            "session_id": self.current_session["session_id"],
            "duration": self._calculate_duration(),
            "steps_count": len(self.current_session["steps"]),
            "success": success
        })
        
        # ファイルログ出力
        if self.file_logging:
            self._log_to_file()
        
        # セッションをリセット
        session_data = self.current_session.copy()
        self.current_session = None
        
        return session_data
    
    def get_current_session(self) -> Optional[Dict[str, Any]]:
        """現在のセッション情報を取得"""
        return self.current_session
    
    def _log_to_stdout(self, event_type: str, data: Dict[str, Any]):
        """stdoutに構造化ログを出力"""
        if not self.stdout_enabled:
            return
        
        log_entry = {
            "timestamp": datetime.now().isoformat(),
            "event_type": event_type,
            "data": data
        }
        
        try:
            print(f"[THINKING_LOG] {json.dumps(log_entry, ensure_ascii=False, indent=2)}", 
                  file=sys.stdout, flush=True)
        except Exception as e:
            print(f"[THINKING_LOG_ERROR] {str(e)}", file=sys.stderr, flush=True)
    
    def _log_to_file(self):
        """ファイルにログを出力"""
        if not self.current_session:
            return
        
        try:
            log_path = Path(self.log_file)
            
            # 既存のログを読み込み
            logs = []
            if log_path.exists():
                with open(log_path, 'r', encoding='utf-8') as f:
                    logs = json.load(f)
            
            # 新しいログを追加
            logs.append(self.current_session)
            
            # ファイルに保存
            with open(log_path, 'w', encoding='utf-8') as f:
                json.dump(logs, f, ensure_ascii=False, indent=2)
                
        except Exception as e:
            self._log_to_stdout("FILE_LOG_ERROR", {"error": str(e)})
    
    def _calculate_duration(self) -> float:
        """セッションの実行時間を計算"""
        if not self.current_session:
            return 0.0
        
        try:
            start_time = datetime.fromisoformat(self.current_session["start_time"])
            end_time = datetime.fromisoformat(self.current_session["end_time"])
            return (end_time - start_time).total_seconds()
        except:
            return 0.0


class ThinkingCallbackManager:
    """思考コールバックの管理クラス"""
    
    def __init__(self):
        self.callbacks: Dict[str, ThinkingCallback] = {}
        self.default_callback = ThinkingCallback()
    
    def create_callback(self, name: str, **kwargs) -> ThinkingCallback:
        """新しいコールバックを作成"""
        callback = ThinkingCallback(**kwargs)
        self.callbacks[name] = callback
        return callback
    
    def get_callback(self, name: str) -> Optional[ThinkingCallback]:
        """コールバックを取得"""
        return self.callbacks.get(name)
    
    def remove_callback(self, name: str):
        """コールバックを削除"""
        if name in self.callbacks:
            del self.callbacks[name]
    
    def get_default_callback(self) -> ThinkingCallback:
        """デフォルトコールバックを取得"""
        return self.default_callback


def create_api_callback(response_queue: asyncio.Queue) -> Callable:
    """API応答用のコールバック関数を作成"""
    def callback(step_name: str, step_data: Dict[str, Any]):
        try:
            # 非同期キューに思考データを追加
            response_queue.put_nowait({
                "type": "thinking_step",
                "step": step_name,
                "data": step_data,
                "timestamp": datetime.now().isoformat()
            })
        except asyncio.QueueFull:
            # キューが満杯の場合はスキップ
            pass
    
    return callback


def create_websocket_callback(websocket) -> Callable:
    """WebSocket用のコールバック関数を作成"""
    def callback(step_name: str, step_data: Dict[str, Any]):
        try:
            message = {
                "type": "thinking_step",
                "step": step_name,
                "data": step_data,
                "timestamp": datetime.now().isoformat()
            }
            
            # WebSocketでメッセージを送信（非同期）
            asyncio.create_task(websocket.send_text(json.dumps(message, ensure_ascii=False)))
        except Exception as e:
            # エラーは無視（WebSocket接続が切れている可能性）
            pass
    
    return callback


class ThinkingIntegration:
    """既存のパイプラインとの統合クラス"""
    
    def __init__(self, pipeline, callback_manager: ThinkingCallbackManager):
        self.pipeline = pipeline
        self.callback_manager = callback_manager
    
    async def process_with_thinking(self, 
                                  messages: List[Dict[str, Any]], 
                                  session_id: str = None,
                                  callback_name: str = "default") -> Dict[str, Any]:
        """思考コールバック付きでメッセージを処理"""
        if session_id is None:
            session_id = f"session_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        # コールバックを取得
        callback = self.callback_manager.get_callback(callback_name)
        if not callback:
            callback = self.callback_manager.get_default_callback()
        
        # 質問を取得
        user_query = messages[-1].get("content", "") if messages else ""
        
        # セッション開始
        callback.start_session(session_id, user_query)
        
        try:
            # パイプラインの実行と監視
            result = await self._process_with_monitoring(messages, callback)
            
            # セッション終了
            session_data = callback.end_session(
                result.get("response", ""), 
                result.get("success", False)
            )
            
            # 結果に思考ログを追加
            result["thinking_session"] = session_data
            
            return result
            
        except Exception as e:
            # エラー発生時
            callback.end_session(f"エラー: {str(e)}", False)
            raise
    
    async def _process_with_monitoring(self, messages: List[Dict[str, Any]], callback: ThinkingCallback) -> Dict[str, Any]:
        """パイプラインの実行を監視"""
        # 元のパイプラインの process_message を呼び出し
        result = await self.pipeline.process_message(messages)
        
        # thinking_log があれば、各ステップをコールバックに送信
        if "thinking_log" in result:
            for log_entry in result["thinking_log"]:
                step_name = log_entry.get("step", "unknown")
                step_data = {
                    "timestamp": log_entry.get("timestamp"),
                    "duration": log_entry.get("duration"),
                    "input": log_entry.get("input"),
                    "output": log_entry.get("output"),
                    "error": log_entry.get("error")
                }
                callback.log_step(step_name, step_data)
        
        return result


# グローバルインスタンス
thinking_callback_manager = ThinkingCallbackManager() 