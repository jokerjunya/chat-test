#!/usr/bin/env python3
"""
FastAPI チャットアプリケーションのテストスクリプト
"""
import asyncio
import json
import httpx
import websockets
from typing import Dict, List

# テスト設定
API_BASE_URL = "http://localhost:8000"
WS_URL = "ws://localhost:8000/api/chat/ws"

async def test_health_check():
    """ヘルスチェックエンドポイントをテスト"""
    print("🔍 ヘルスチェックをテスト中...")
    
    async with httpx.AsyncClient() as client:
        response = await client.get(f"{API_BASE_URL}/health")
        
        if response.status_code == 200:
            print("✅ ヘルスチェック: 正常")
            print(f"   レスポンス: {response.json()}")
        else:
            print(f"❌ ヘルスチェック: 失敗 (ステータス: {response.status_code})")

async def test_chat_rest_api():
    """REST API チャットエンドポイントをテスト"""
    print("\n🔍 REST API チャットをテスト中...")
    
    test_messages = [
        {"role": "user", "content": "こんにちは"},
        {"role": "user", "content": "今日の天気はどうですか？"},
        {"role": "user", "content": "Python について教えてください"}
    ]
    
    async with httpx.AsyncClient() as client:
        for i, message in enumerate(test_messages, 1):
            print(f"\n📝 テストメッセージ {i}: {message['content']}")
            
            try:
                response = await client.post(
                    f"{API_BASE_URL}/api/chat",
                    json={"messages": [message]},
                    timeout=30.0
                )
                
                if response.status_code == 200:
                    result = response.json()
                    print(f"✅ レスポンス: {result['message'][:100]}...")
                    print(f"   タイムスタンプ: {result['timestamp']}")
                else:
                    print(f"❌ エラー: {response.status_code} - {response.text}")
                    
            except httpx.TimeoutException:
                print("⏰ タイムアウト: レスポンスが30秒以内に返されませんでした")
            except Exception as e:
                print(f"❌ エラー: {str(e)}")

async def test_websocket():
    """WebSocket エンドポイントをテスト"""
    print("\n🔍 WebSocket チャットをテスト中...")
    
    try:
        async with websockets.connect(WS_URL) as websocket:
            print("✅ WebSocket接続: 成功")
            
            # テストメッセージを送信
            test_message = {
                "messages": [
                    {"role": "user", "content": "WebSocketで接続中です！"}
                ]
            }
            
            await websocket.send(json.dumps(test_message))
            print("📤 メッセージ送信: 完了")
            
            # 処理中メッセージを受信
            processing_msg = await websocket.recv()
            print(f"📥 処理中メッセージ: {processing_msg}")
            
            # 応答を受信
            response = await websocket.recv()
            print(f"📥 応答: {response[:100]}...")
            
    except websockets.exceptions.ConnectionClosed:
        print("❌ WebSocket接続が閉じられました")
    except Exception as e:
        print(f"❌ WebSocketエラー: {str(e)}")

async def run_all_tests():
    """すべてのテストを実行"""
    print("🚀 チャットアプリケーションのテストを開始します\n")
    
    await test_health_check()
    await test_chat_rest_api()
    await test_websocket()
    
    print("\n🎉 テスト完了！")

if __name__ == "__main__":
    asyncio.run(run_all_tests()) 