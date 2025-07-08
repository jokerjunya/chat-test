"""
思考分離パーサー
<think>タグを含む応答を解析し、思考部分と実際の回答を分離
"""

import re
from typing import Dict, Any, Optional


class ThinkingParser:
    """思考部分を分離するパーサー"""
    
    def __init__(self):
        # <think>で始まる思考部分の正規表現パターン
        self.think_pattern = re.compile(r'<think>(.*?)</think>', re.DOTALL)
        # 終了タグが見つからない場合（途中で切れている場合）
        self.think_unclosed_pattern = re.compile(r'<think>(.*?)(?=\n\n|\Z)', re.DOTALL)
        # 実際の応答パターン（開始や終了の改行を含む）
        self.think_flexible_pattern = re.compile(r'<think>(.*?)(?:</think>|$)', re.DOTALL)
        # 不完全なタグパターン（</think>のみで開始される場合）
        self.think_malformed_pattern = re.compile(r'^(.*?)</think>', re.DOTALL)
        # 思考らしい内容の検出
        self.think_content_pattern = re.compile(r'^.*?</think>\s*\n\s*(.*)$', re.DOTALL)
        
    def parse_response(self, response: str) -> Dict[str, Any]:
        """
        応答を分析して思考部分と実際の回答を分離
        
        Args:
            response: LLMからの応答文字列
            
        Returns:
            Dictionary containing:
            - has_thinking: bool - 思考部分があるかどうか
            - thinking: str - 思考部分のテキスト
            - answer: str - 実際の回答部分
            - original: str - 元の応答
        """
        result = {
            "has_thinking": False,
            "thinking": "",
            "answer": response,
            "original": response
        }
        
        # 特殊ケース: </think>で始まる不完全なタグの処理
        if response.startswith('</think>'):
            # </think>タグを全て削除し、残りを回答として扱う
            import re
            cleaned_response = re.sub(r'</think>\s*', '', response).strip()
            result["answer"] = cleaned_response if cleaned_response else "応答が生成されました。"
            return result
        
        # まず正規の<think>...</think>パターンで検索
        match = self.think_pattern.search(response)
        thinking_text = ""
        answer_text = response
        
        if not match:
            # 次に柔軟なパターンで検索（終了タグがない場合も含む）
            match = self.think_flexible_pattern.search(response)
        
        if not match:
            # 最後に改行で区切られた未終了パターンで検索
            match = self.think_unclosed_pattern.search(response)
        
        if not match:
            # 不完全なタグパターンで検索（</think>で始まる場合）
            malformed_match = self.think_malformed_pattern.search(response)
            if malformed_match:
                # </think>より前の部分を思考として扱う
                thinking_text = malformed_match.group(1).strip()
                if thinking_text:  # 思考内容が実際にある場合のみ
                    # </think>以降を回答として扱う
                    content_match = self.think_content_pattern.search(response)
                    if content_match:
                        answer_text = content_match.group(1).strip()
                        result["has_thinking"] = True
                        result["thinking"] = thinking_text
                        result["answer"] = answer_text if answer_text else "応答が生成されました。"
                        return result
        
        if match:
            result["has_thinking"] = True
            result["thinking"] = match.group(1).strip()
            
            # 思考部分を除去して実際の回答を取得
            answer_text = response[:match.start()] + response[match.end():]
            result["answer"] = answer_text.strip()
            
            # 空の回答の場合は最低限のメッセージを設定
            if not result["answer"]:
                result["answer"] = "応答が生成されました。"
        
        return result
    
    def format_for_frontend(self, parsed_response: Dict[str, Any]) -> Dict[str, Any]:
        """
        フロントエンド用にフォーマットされた応答を作成
        
        Args:
            parsed_response: parse_response()の出力
            
        Returns:
            フロントエンド用の構造化された応答
        """
        return {
            "message": parsed_response["answer"],
            "thinking": parsed_response["thinking"] if parsed_response["has_thinking"] else None,
            "has_thinking": parsed_response["has_thinking"],
            "original_response": parsed_response["original"]
        }


def parse_thinking_response(response: str) -> Dict[str, Any]:
    """
    便利な関数：思考応答を分析
    """
    parser = ThinkingParser()
    return parser.parse_response(response)


# 使用例とテスト
if __name__ == "__main__":
    # テストケース
    test_response = """<think>
ユーザーが「こんにちは」と言っています。これは一般的な挨拶なので、
適切な日本語で応答する必要があります。
</think>

こんにちは！どのようにお手伝いできますか？"""
    
    parser = ThinkingParser()
    result = parser.parse_response(test_response)
    
    print("Test Result:")
    print(f"Has thinking: {result['has_thinking']}")
    print(f"Thinking: {result['thinking']}")
    print(f"Answer: {result['answer']}")
    print(f"Formatted: {parser.format_for_frontend(result)}") 