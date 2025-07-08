"""
思考分離パーサーの改良テスト
"""

from thinking_parser import ThinkingParser
import re

# 実際のAPI応答をテスト
test_response = """</think>

</think>

申し訳ありません、現在の天気情報は提供できません。検索結果には天気に関する情報は含まれていません。最新の天気情報が必要な場合は、天気アプリや天気予報のウェブサイトをご確認ください。

一般的に、正確な天気情報を得るためには：
1. 気象庁のウェブサイト
2. Yahoo!天気やウェザーニュースなどの天気アプリ
3. テレビやラジオの天気予報
をご利用いただくことをおすすめします。"""

print("=== 改良版パーサーテスト ===")

# 特殊ケース用の改良パターン
def improved_parse(response):
    """改良版パーサー"""
    
    # </think>で始まる場合の特殊処理
    if response.startswith('</think>'):
        # </think>タグを全て削除し、残りを回答として扱う
        cleaned_response = re.sub(r'</think>\s*', '', response).strip()
        
        # 思考内容はなしとして扱う（モデルが不完全に生成した場合）
        return {
            "has_thinking": False,  # 完全でない思考は無効とする
            "thinking": "",
            "answer": cleaned_response,
            "original": response
        }
    
    # 通常のパーサー処理
    parser = ThinkingParser()
    return parser.parse_response(response)

result = improved_parse(test_response)

print("=== 改良版結果 ===")
print(f"思考有無: {result['has_thinking']}")
print(f"思考内容: '{result['thinking']}'")
print(f"回答内容: '{result['answer'][:150]}...'")

# 実際に適用してみる
print("\n=== 適用後の表示 ===")
if result['has_thinking']:
    print("🤔 思考プロセス:")
    print(result['thinking'])
    print()
print("💬 回答:")
print(result['answer']) 