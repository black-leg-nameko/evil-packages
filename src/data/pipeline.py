"""
データ収集と前処理のパイプライン

NPMパッケージデータを収集し、特徴抽出までを実行する。
"""

import json
import pandas as pd
import numpy as np
from typing import List, Dict, Optional
from datetime import datetime
import logging
from pathlib import Path

from .collectors.npm_collector import NPMCollector
from .collectors.osv_collector import OSVCollector
from ..features.nlp_features import NLPFeatureExtractor
from ..features.metadata_features import MetadataFeatureExtractor
from ..features.static_features import StaticFeatureExtractor

logger = logging.getLogger(__name__)


class DataPipeline:
    """データ収集と前処理のパイプライン"""
    
    def __init__(self, 
                 output_dir: str = "data/processed",
                 popular_packages: Optional[List[str]] = None):
        """
        Args:
            output_dir: 出力ディレクトリ
            popular_packages: 人気パッケージ名のリスト（typosquatting検出用）
        """
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        self.npm_collector = NPMCollector()
        self.osv_collector = OSVCollector()
        self.nlp_extractor = NLPFeatureExtractor()
        self.metadata_extractor = MetadataFeatureExtractor()
        self.static_extractor = StaticFeatureExtractor(popular_packages)
    
    def process_package(self, package_name: str, label: Optional[int] = None) -> Dict:
        """
        単一パッケージを処理
        
        Args:
            package_name: パッケージ名
            label: ラベル（1: 悪性, 0: 良性, None: 不明）
            
        Returns:
            処理済みデータの辞書
        """
        logger.info(f"Processing package: {package_name}")
        
        # NPMからメタデータを取得
        package_info = self.npm_collector.get_package_info(package_name)
        if not package_info:
            logger.warning(f"Failed to fetch package info for {package_name}")
            return None
        
        metadata = self.npm_collector.extract_metadata(package_info)
        
        # OSVから脆弱性情報を取得
        osv_vulns = self.osv_collector.query_by_package(package_name, ecosystem="npm")
        osv_features = self.osv_collector.extract_vulnerability_features(osv_vulns)
        
        # 特徴抽出
        description = metadata.get('description', '')
        readme = metadata.get('readme', '')
        
        # 自然言語特徴
        nlp_features = self.nlp_extractor.extract_all_features(description, readme)
        
        # メタデータ特徴
        metadata_features = self.metadata_extractor.extract_all_features(
            metadata, osv_features=osv_features
        )
        
        # 静的特徴
        static_features = self.static_extractor.extract_all_features(
            package_name,
            repository_url=metadata.get('repository'),
            file_structure=None  # ファイル構造は別途取得が必要
        )
        
        # 統合
        result = {
            'package_name': package_name,
            'label': label,
            'metadata': metadata,
            'nlp_features': nlp_features,
            'metadata_features': metadata_features,
            'static_features': static_features,
            'osv_features': osv_features,
            'processed_at': datetime.now().isoformat(),
        }
        
        return result
    
    def process_package_list(self, 
                           package_names: List[str],
                           labels: Optional[List[int]] = None,
                           batch_size: int = 100,
                           save_interval: int = 50) -> List[Dict]:
        """
        パッケージリストを一括処理
        
        Args:
            package_names: パッケージ名のリスト
            labels: ラベルのリスト（オプション）
            batch_size: バッチサイズ
            save_interval: 保存間隔
            
        Returns:
            処理済みデータのリスト
        """
        if labels is None:
            labels = [None] * len(package_names)
        
        results = []
        
        for i, (package_name, label) in enumerate(zip(package_names, labels)):
            try:
                result = self.process_package(package_name, label)
                if result:
                    results.append(result)
                
                # 定期的に保存
                if (i + 1) % save_interval == 0:
                    self._save_results(results, f"batch_{i+1}.json")
                    logger.info(f"Processed {i+1}/{len(package_names)} packages")
            
            except Exception as e:
                logger.error(f"Error processing {package_name}: {e}")
                continue
        
        # 最終保存
        self._save_results(results, "final_results.json")
        
        return results
    
    def create_feature_matrix(self, processed_data: List[Dict]) -> tuple:
        """
        処理済みデータから特徴量行列を作成
        
        Args:
            processed_data: 処理済みデータのリスト
            
        Returns:
            (X_nlp, X_metadata, X_static, y, package_names) のタプル
        """
        nlp_features_list = []
        metadata_features_list = []
        static_features_list = []
        labels = []
        package_names = []
        
        for data in processed_data:
            if not data:
                continue
            
            # 特徴量をフラット化
            nlp_features = self._flatten_features(data['nlp_features'])
            metadata_features = self._flatten_features(data['metadata_features'])
            static_features = self._flatten_features(data['static_features'])
            
            nlp_features_list.append(nlp_features)
            metadata_features_list.append(metadata_features)
            static_features_list.append(static_features)
            
            labels.append(data.get('label'))
            package_names.append(data['package_name'])
        
        # 配列に変換
        X_nlp = np.array(nlp_features_list)
        X_metadata = np.array(metadata_features_list)
        X_static = np.array(static_features_list)
        y = np.array(labels)
        
        return X_nlp, X_metadata, X_static, y, package_names
    
    def _flatten_features(self, features: Dict) -> List[float]:
        """特徴量辞書をフラットなリストに変換"""
        flattened = []
        
        for key, value in features.items():
            if isinstance(value, (int, float)):
                flattened.append(float(value))
            elif isinstance(value, bool):
                flattened.append(1.0 if value else 0.0)
            elif isinstance(value, list):
                flattened.extend([float(v) for v in value])
            elif isinstance(value, np.ndarray):
                flattened.extend(value.tolist())
            elif value is None:
                flattened.append(0.0)
            else:
                # その他の型は0に変換
                flattened.append(0.0)
        
        return flattened
    
    def _save_results(self, results: List[Dict], filename: str):
        """結果をJSONファイルに保存"""
        filepath = self.output_dir / filename
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(results, f, indent=2, ensure_ascii=False, default=str)
        logger.info(f"Saved results to {filepath}")
    
    def create_time_split(self,
                         processed_data: List[Dict],
                         train_end: str = "2023-12-31",
                         val_end: str = "2024-06-30") -> Dict:
        """
        時系列分割を作成
        
        Args:
            processed_data: 処理済みデータのリスト
            train_end: 学習データの終了日（YYYY-MM-DD）
            val_end: 検証データの終了日（YYYY-MM-DD）
            
        Returns:
            分割されたデータの辞書
        """
        train_data = []
        val_data = []
        test_data = []
        
        train_end_dt = datetime.strptime(train_end, "%Y-%m-%d")
        val_end_dt = datetime.strptime(val_end, "%Y-%m-%d")
        
        for data in processed_data:
            if not data:
                continue
            
            created_str = data['metadata'].get('created', '')
            if not created_str:
                continue
            
            try:
                created_dt = datetime.fromisoformat(created_str.replace('Z', '+00:00'))
            except:
                continue
            
            if created_dt <= train_end_dt:
                train_data.append(data)
            elif created_dt <= val_end_dt:
                val_data.append(data)
            else:
                test_data.append(data)
        
        return {
            'train': train_data,
            'val': val_data,
            'test': test_data
        }


if __name__ == "__main__":
    # テスト実行
    pipeline = DataPipeline()
    
    # テストパッケージ
    test_packages = ["lodash", "express", "react"]
    results = pipeline.process_package_list(test_packages)
    
    print(f"Processed {len(results)} packages")
    
    # 特徴量行列を作成
    X_nlp, X_metadata, X_static, y, names = pipeline.create_feature_matrix(results)
    print(f"NLP features shape: {X_nlp.shape}")
    print(f"Metadata features shape: {X_metadata.shape}")
    print(f"Static features shape: {X_static.shape}")
