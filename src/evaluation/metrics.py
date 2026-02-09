"""
評価指標モジュール

Time-to-Warn、Precision@K、False Positive分析などの評価指標を実装する。
"""

import numpy as np
from typing import Dict, List, Tuple, Optional
from sklearn.metrics import (
    roc_auc_score, precision_recall_curve, 
    precision_score, recall_score, f1_score,
    confusion_matrix
)
import pandas as pd
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)


class EvaluationMetrics:
    """評価指標を計算するクラス"""
    
    def __init__(self):
        pass
    
    def compute_all_metrics(self,
                           y_true: np.ndarray,
                           y_pred: np.ndarray,
                           y_scores: np.ndarray,
                           publication_times: Optional[np.ndarray] = None,
                           detection_times: Optional[np.ndarray] = None) -> Dict:
        """
        すべての評価指標を計算
        
        Args:
            y_true: 真のラベル（1: 悪性, 0: 良性）
            y_pred: 予測ラベル（1: 悪性, 0: 良性）
            y_scores: 異常スコア（高いほど悪性）
            publication_times: 公開時刻の配列（datetime）
            detection_times: 検知時刻の配列（datetime）
            
        Returns:
            評価指標の辞書
        """
        metrics = {}
        
        # 基本指標
        metrics.update(self.compute_basic_metrics(y_true, y_pred, y_scores))
        
        # Precision@K
        metrics.update(self.compute_precision_at_k(y_true, y_scores, k_values=[10, 50, 100]))
        
        # Time-to-Warn（公開時刻と検知時刻が提供される場合）
        if publication_times is not None and detection_times is not None:
            metrics.update(self.compute_time_to_warn(
                y_true, y_pred, publication_times, detection_times
            ))
        
        # False Positive分析
        metrics.update(self.analyze_false_positives(y_true, y_pred, y_scores))
        
        return metrics
    
    def compute_basic_metrics(self,
                              y_true: np.ndarray,
                              y_pred: np.ndarray,
                              y_scores: np.ndarray) -> Dict:
        """基本指標を計算"""
        # AUC-ROC
        try:
            auc_roc = roc_auc_score(y_true, y_scores)
        except:
            auc_roc = 0.0
        
        # Precision, Recall, F1
        precision = precision_score(y_true, y_pred, zero_division=0)
        recall = recall_score(y_true, y_pred, zero_division=0)
        f1 = f1_score(y_true, y_pred, zero_division=0)
        
        # Confusion Matrix
        tn, fp, fn, tp = confusion_matrix(y_true, y_pred).ravel()
        
        return {
            'auc_roc': auc_roc,
            'precision': precision,
            'recall': recall,
            'f1_score': f1,
            'true_positives': int(tp),
            'true_negatives': int(tn),
            'false_positives': int(fp),
            'false_negatives': int(fn),
            'false_positive_rate': fp / (fp + tn) if (fp + tn) > 0 else 0.0,
            'false_negative_rate': fn / (fn + tp) if (fn + tp) > 0 else 0.0,
        }
    
    def compute_precision_at_k(self,
                               y_true: np.ndarray,
                               y_scores: np.ndarray,
                               k_values: List[int] = [10, 50, 100]) -> Dict:
        """
        Precision@Kを計算
        
        Args:
            y_true: 真のラベル
            y_scores: 異常スコア
            k_values: Kの値のリスト
            
        Returns:
            Precision@Kの辞書
        """
        # スコアでソート（高い順）
        sorted_indices = np.argsort(y_scores)[::-1]
        sorted_labels = y_true[sorted_indices]
        
        metrics = {}
        for k in k_values:
            if k > len(sorted_labels):
                k = len(sorted_labels)
            
            top_k_labels = sorted_labels[:k]
            precision_at_k = np.sum(top_k_labels) / k if k > 0 else 0.0
            metrics[f'precision_at_{k}'] = precision_at_k
        
        return metrics
    
    def compute_time_to_warn(self,
                             y_true: np.ndarray,
                             y_pred: np.ndarray,
                             publication_times: np.ndarray,
                             detection_times: np.ndarray,
                             time_windows: List[int] = [60, 360, 1440]) -> Dict:
        """
        Time-to-Warn指標を計算
        
        Args:
            y_true: 真のラベル
            y_pred: 予測ラベル
            publication_times: 公開時刻（datetime配列）
            detection_times: 検知時刻（datetime配列）
            time_windows: 時間ウィンドウ（分単位、例: [60, 360, 1440] = 1時間、6時間、24時間）
            
        Returns:
            Time-to-Warn指標の辞書
        """
        metrics = {}
        
        # 悪性パッケージのみを対象
        malicious_mask = y_true == 1
        detected_mask = y_pred == 1
        
        if not np.any(malicious_mask):
            return {f'recall_at_{tw}_minutes': 0.0 for tw in time_windows}
        
        # 検知された悪性パッケージ
        detected_malicious_mask = malicious_mask & detected_mask
        
        # 各時間ウィンドウでの検知率
        for tw_minutes in time_windows:
            tw_delta = timedelta(minutes=tw_minutes)
            
            detected_within_window = 0
            total_malicious = np.sum(malicious_mask)
            
            for i in range(len(y_true)):
                if malicious_mask[i] and detected_malicious_mask[i]:
                    time_diff = detection_times[i] - publication_times[i]
                    if time_diff <= tw_delta:
                        detected_within_window += 1
            
            recall_at_time = detected_within_window / total_malicious if total_malicious > 0 else 0.0
            metrics[f'recall_at_{tw_minutes}_minutes'] = recall_at_time
        
        # 平均検知時間（検知された悪性パッケージのみ）
        if np.any(detected_malicious_mask):
            time_diffs = []
            for i in range(len(y_true)):
                if detected_malicious_mask[i]:
                    time_diff = (detection_times[i] - publication_times[i]).total_seconds() / 60  # 分単位
                    time_diffs.append(time_diff)
            
            metrics['avg_time_to_warn_minutes'] = np.mean(time_diffs)
            metrics['median_time_to_warn_minutes'] = np.median(time_diffs)
        else:
            metrics['avg_time_to_warn_minutes'] = np.inf
            metrics['median_time_to_warn_minutes'] = np.inf
        
        return metrics
    
    def analyze_false_positives(self,
                                y_true: np.ndarray,
                                y_pred: np.ndarray,
                                y_scores: np.ndarray) -> Dict:
        """
        False Positiveを分析
        
        Args:
            y_true: 真のラベル
            y_pred: 予測ラベル
            y_scores: 異常スコア
            
        Returns:
            False Positive分析の辞書
        """
        fp_mask = (y_true == 0) & (y_pred == 1)
        tp_mask = (y_true == 1) & (y_pred == 1)
        
        analysis = {
            'false_positive_count': int(np.sum(fp_mask)),
            'true_positive_count': int(np.sum(tp_mask)),
        }
        
        if np.any(fp_mask):
            analysis['fp_mean_score'] = float(np.mean(y_scores[fp_mask]))
            analysis['fp_std_score'] = float(np.std(y_scores[fp_mask]))
            analysis['fp_max_score'] = float(np.max(y_scores[fp_mask]))
            analysis['fp_min_score'] = float(np.min(y_scores[fp_mask]))
        else:
            analysis['fp_mean_score'] = 0.0
            analysis['fp_std_score'] = 0.0
            analysis['fp_max_score'] = 0.0
            analysis['fp_min_score'] = 0.0
        
        if np.any(tp_mask):
            analysis['tp_mean_score'] = float(np.mean(y_scores[tp_mask]))
            analysis['tp_std_score'] = float(np.std(y_scores[tp_mask]))
        else:
            analysis['tp_mean_score'] = 0.0
            analysis['tp_std_score'] = 0.0
        
        # スコアの分離度
        if np.any(fp_mask) and np.any(tp_mask):
            score_separation = analysis['tp_mean_score'] - analysis['fp_mean_score']
            analysis['score_separation'] = float(score_separation)
        else:
            analysis['score_separation'] = 0.0
        
        return analysis
    
    def compute_temporal_performance(self,
                                    y_true: np.ndarray,
                                    y_pred: np.ndarray,
                                    y_scores: np.ndarray,
                                    time_periods: np.ndarray) -> pd.DataFrame:
        """
        時系列での性能を計算（概念ドリフト評価用）
        
        Args:
            y_true: 真のラベル
            y_pred: 予測ラベル
            y_scores: 異常スコア
            time_periods: 時系列ラベル（例: 年、四半期）
            
        Returns:
            時系列ごとの性能データフレーム
        """
        unique_periods = np.unique(time_periods)
        results = []
        
        for period in unique_periods:
            mask = time_periods == period
            period_y_true = y_true[mask]
            period_y_pred = y_pred[mask]
            period_y_scores = y_scores[mask]
            
            if len(period_y_true) == 0:
                continue
            
            period_metrics = self.compute_basic_metrics(
                period_y_true, period_y_pred, period_y_scores
            )
            period_metrics['period'] = period
            period_metrics['sample_count'] = len(period_y_true)
            results.append(period_metrics)
        
        return pd.DataFrame(results)


if __name__ == "__main__":
    # テスト実行
    metrics = EvaluationMetrics()
    
    # ダミーデータ
    np.random.seed(42)
    n_samples = 1000
    y_true = np.random.binomial(1, 0.1, n_samples)  # 10%が悪性
    y_scores = np.random.rand(n_samples)
    y_scores[y_true == 1] += 0.3  # 悪性のスコアを高く
    y_pred = (y_scores > 0.5).astype(int)
    
    # 基本指標
    basic_metrics = metrics.compute_basic_metrics(y_true, y_pred, y_scores)
    print("Basic metrics:", basic_metrics)
    
    # Precision@K
    precision_at_k = metrics.compute_precision_at_k(y_true, y_scores)
    print("Precision@K:", precision_at_k)
    
    # False Positive分析
    fp_analysis = metrics.analyze_false_positives(y_true, y_pred, y_scores)
    print("False Positive analysis:", fp_analysis)
