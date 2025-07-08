"""
KPI測定システム
レイテンシ、BLEU、DDGリクエスト数を測定・記録
"""

import time
import json
import asyncio
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict
import asyncio
import threading
from collections import defaultdict
import statistics

@dataclass
class KPIMetrics:
    """KPI測定結果"""
    timestamp: datetime
    latency_ms: float
    token_count: int
    search_requests: int
    bleu_score: Optional[float] = None
    error_occurred: bool = False
    error_message: Optional[str] = None

class KPIMonitor:
    """KPI監視システム"""
    
    def __init__(self):
        self.metrics: List[KPIMetrics] = []
        self.daily_search_count = defaultdict(int)
        self.lock = threading.Lock()
        
    def start_measurement(self) -> float:
        """測定開始"""
        return time.time()
    
    def record_measurement(
        self, 
        start_time: float, 
        token_count: int, 
        search_requests: int = 0,
        bleu_score: Optional[float] = None,
        error_occurred: bool = False,
        error_message: Optional[str] = None
    ) -> KPIMetrics:
        """測定結果を記録"""
        
        latency_ms = (time.time() - start_time) * 1000
        
        metric = KPIMetrics(
            timestamp=datetime.now(),
            latency_ms=latency_ms,
            token_count=token_count,
            search_requests=search_requests,
            bleu_score=bleu_score,
            error_occurred=error_occurred,
            error_message=error_message
        )
        
        with self.lock:
            self.metrics.append(metric)
            
            # 今日の日付でDDGリクエスト数を更新
            today = datetime.now().date()
            self.daily_search_count[today] += search_requests
            
        return metric
    
    def get_recent_metrics(self, hours: int = 24) -> List[KPIMetrics]:
        """最近の測定結果を取得"""
        cutoff_time = datetime.now() - timedelta(hours=hours)
        
        with self.lock:
            return [m for m in self.metrics if m.timestamp >= cutoff_time]
    
    def get_daily_stats(self) -> Dict[str, Any]:
        """日次統計を取得"""
        today = datetime.now().date()
        recent_metrics = self.get_recent_metrics(24)
        
        if not recent_metrics:
            return {
                "date": today.isoformat(),
                "total_requests": 0,
                "avg_latency_ms": 0,
                "avg_tokens": 0,
                "search_requests": 0,
                "error_rate": 0,
                "avg_bleu_score": None
            }
        
        # 統計計算
        valid_metrics = [m for m in recent_metrics if not m.error_occurred]
        
        avg_latency = statistics.mean([m.latency_ms for m in valid_metrics]) if valid_metrics else 0
        avg_tokens = statistics.mean([m.token_count for m in valid_metrics]) if valid_metrics else 0
        
        bleu_scores = [m.bleu_score for m in valid_metrics if m.bleu_score is not None]
        avg_bleu = statistics.mean(bleu_scores) if bleu_scores else None
        
        error_rate = len([m for m in recent_metrics if m.error_occurred]) / len(recent_metrics)
        
        return {
            "date": today.isoformat(),
            "total_requests": len(recent_metrics),
            "avg_latency_ms": round(avg_latency, 2),
            "avg_tokens": round(avg_tokens, 1),
            "search_requests": self.daily_search_count[today],
            "error_rate": round(error_rate, 3),
            "avg_bleu_score": round(avg_bleu, 3) if avg_bleu else None
        }
    
    def get_performance_report(self) -> Dict[str, Any]:
        """パフォーマンスレポートを生成"""
        recent_metrics = self.get_recent_metrics(24)
        daily_stats = self.get_daily_stats()
        
        if not recent_metrics:
            return {
                "summary": daily_stats,
                "status": "No data available",
                "recommendations": []
            }
        
        # パフォーマンス評価
        avg_latency = daily_stats["avg_latency_ms"]
        search_requests = daily_stats["search_requests"]
        error_rate = daily_stats["error_rate"]
        
        # 仕様書の目標値と比較
        status = "良好"
        recommendations = []
        
        # レイテンシ目標: 128 tok ≤ 6s (6000ms)
        if avg_latency > 6000:
            status = "改善要"
            recommendations.append("レイテンシが目標値(6秒)を超えています。モデルまたはハードウェアの最適化が必要です。")
        
        # DDGリクエスト数目標: ≤ 250/日
        if search_requests > 250:
            status = "制限警告"
            recommendations.append("DDGリクエスト数が日次制限(250件)を超えています。")
        
        # エラー率チェック
        if error_rate > 0.05:  # 5%以上
            status = "エラー多発"
            recommendations.append("エラー率が高すぎます。システムの安定性を確認してください。")
        
        return {
            "summary": daily_stats,
            "status": status,
            "recommendations": recommendations,
            "targets": {
                "latency_ms": 6000,
                "daily_searches": 250,
                "bleu_score": 0.85
            }
        }
    
    def export_metrics(self, filename: Optional[str] = None) -> str:
        """測定結果をJSONファイルに出力"""
        if filename is None:
            filename = f"kpi_metrics_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        
        with self.lock:
            data = {
                "export_time": datetime.now().isoformat(),
                "metrics": [asdict(m) for m in self.metrics],
                "daily_search_counts": {str(k): v for k, v in self.daily_search_count.items()}
            }
        
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2, default=str)
        
        return filename

# BLEU スコア計算関数
def calculate_bleu_score(reference: str, hypothesis: str) -> float:
    """
    簡易BLEU スコア計算
    実際のプロダクションでは、sacrebleu等の専用ライブラリを使用推奨
    """
    try:
        # 文字レベルのn-gramでBLEU計算（簡易版）
        import re
        
        # 前処理
        ref_tokens = list(reference.lower().strip())
        hyp_tokens = list(hypothesis.lower().strip())
        
        if not ref_tokens or not hyp_tokens:
            return 0.0
        
        # 1-gramの一致率を計算
        ref_1gram = set(ref_tokens)
        hyp_1gram = set(hyp_tokens)
        
        if not hyp_1gram:
            return 0.0
        
        precision = len(ref_1gram.intersection(hyp_1gram)) / len(hyp_1gram)
        
        # 長さペナルティ
        length_penalty = min(1.0, len(hyp_tokens) / len(ref_tokens))
        
        # 簡易BLEU スコア
        bleu = precision * length_penalty
        
        return max(0.0, min(1.0, bleu))
        
    except Exception:
        return 0.0

# グローバルKPIモニターインスタンス
kpi_monitor = KPIMonitor() 