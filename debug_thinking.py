"""
思考分離パーサーのデバッグスクリプト
"""

from thinking_parser import ThinkingParser

# 実際のAPI応答をテスト
test_response = """</think>

</think>

申し訳ありません、現在の天気情報は提供できません。検索結果には天気に関する情報は含まれていません。最新の天気情報が必要な場合は、天気アプリや天気予報のウェブサイトをご確認ください。

一般的に、正確な天気情報を得るためには：
1. 気象庁のウェブサイト
2. Yahoo!天気やウェザーニュースなどの天気アプリ
3. テレビやラジオの天気予報
をご利用いただくことをおすすめします。"""

print("=== デバッグテスト ===")
print(f"入力: {test_response[:100]}...")
print()

parser = ThinkingParser()
result = parser.parse_response(test_response)

print("=== パーサー結果 ===")
print(f"思考有無: {result['has_thinking']}")
print(f"思考内容: '{result['thinking']}'")
print(f"回答内容: '{result['answer'][:100]}...'")
print()

print("=== パターンマッチング調査 ===")
import re

# 各種パターンでテスト
patterns = [
    (r'<think>(.*?)</think>', "正規パターン"),
    (r'<think>(.*?)(?:</think>|$)', "柔軟パターン"),
    (r'<think>(.*?)(?=\n\n|\Z)', "改行区切りパターン"),
    (r'</think>', "終了タグのみ"),
    (r'<think>', "開始タグのみ")
]

for pattern, name in patterns:
    match = re.search(pattern, test_response, re.DOTALL)
    print(f"{name}: {'✅ 発見' if match else '❌ 未発見'}")
    if match:
        print(f"  マッチ内容: '{match.group(0)[:50]}...'")

print("\n=== 文字列詳細分析 ===")
print(f"レスポンス先頭20文字: {repr(test_response[:20])}")
print(f"</think>の位置: {test_response.find('</think>')}")
print(f"<think>の位置: {test_response.find('<think>')}") 