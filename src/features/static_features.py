"""
弱い静的特徴抽出モジュール

パッケージ名の類似度（typosquatting検出）、ファイル構造の異常度、リポジトリURLの存在/有効性を抽出する。
"""

import re
import numpy as np
from typing import Dict, List, Optional, Set
from difflib import SequenceMatcher
import requests
import logging

logger = logging.getLogger(__name__)


class StaticFeatureExtractor:
    """弱い静的特徴を抽出するクラス"""
    
    def __init__(self, popular_package_names: Optional[List[str]] = None):
        """
        Args:
            popular_package_names: 人気パッケージ名のリスト（typosquatting検出用）
        """
        self.popular_packages = set(popular_package_names or [])
    
    def extract_all_features(self, 
                           package_name: str,
                           repository_url: Optional[str] = None,
                           file_structure: Optional[List[str]] = None) -> Dict:
        """
        すべての静的特徴を抽出
        
        Args:
            package_name: パッケージ名
            repository_url: リポジトリURL
            file_structure: ファイル構造のリスト
            
        Returns:
            特徴量の辞書
        """
        features = {}
        
        # パッケージ名特徴
        features.update(self.extract_name_features(package_name))
        
        # リポジトリURL特徴
        if repository_url:
            features.update(self.extract_repository_features(repository_url))
        else:
            features.update(self._empty_repository_features())
        
        # ファイル構造特徴
        if file_structure:
            features.update(self.extract_file_structure_features(file_structure))
        else:
            features.update(self._empty_file_structure_features())
        
        return features
    
    def extract_name_features(self, package_name: str) -> Dict:
        """
        パッケージ名特徴を抽出
        
        - typosquatting検出（人気パッケージとの類似度）
        - 名前の異常度
        """
        features = {
            'name_length': len(package_name),
            'name_word_count': len(package_name.split('-')),
            'has_hyphens': '-' in package_name,
            'has_underscores': '_' in package_name,
            'has_numbers': bool(re.search(r'\d', package_name)),
            'has_mixed_case': bool(re.search(r'[a-z].*[A-Z]|[A-Z].*[a-z]', package_name)),
            'starts_with_at': package_name.startswith('@'),
            'is_scoped': package_name.startswith('@'),
        }
        
        # typosquatting検出
        if self.popular_packages:
            similarity_scores = []
            for popular_name in self.popular_packages:
                similarity = self._string_similarity(package_name, popular_name)
                similarity_scores.append(similarity)
            
            if similarity_scores:
                features['max_similarity_to_popular'] = max(similarity_scores)
                features['avg_similarity_to_popular'] = np.mean(similarity_scores)
                features['potential_typosquatting'] = max(similarity_scores) > 0.8 and package_name not in self.popular_packages
        else:
            features['max_similarity_to_popular'] = 0.0
            features['avg_similarity_to_popular'] = 0.0
            features['potential_typosquatting'] = False
        
        # 名前の異常パターン
        features.update(self._detect_suspicious_patterns(package_name))
        
        return features
    
    def extract_repository_features(self, repository_url: str) -> Dict:
        """
        リポジトリURL特徴を抽出
        
        - URLの存在/有効性
        - ホスティングサービスの種類
        - URLの異常度
        """
        features = {
            'has_repository': True,
            'repository_url_length': len(repository_url),
            'is_github': 'github.com' in repository_url.lower(),
            'is_gitlab': 'gitlab.com' in repository_url.lower(),
            'is_bitbucket': 'bitbucket.org' in repository_url.lower(),
            'is_git': repository_url.startswith('git+') or repository_url.endswith('.git'),
        }
        
        # URLの検証（実際には非同期で行うべき）
        try:
            # 簡易的な検証（実際のHTTPリクエストは重いので注意）
            # ここでは形式チェックのみ
            features['repository_url_valid_format'] = self._is_valid_url_format(repository_url)
        except:
            features['repository_url_valid_format'] = False
        
        # 異常パターン検出
        features['suspicious_repository_pattern'] = self._detect_suspicious_repo_patterns(repository_url)
        
        return features
    
    def extract_file_structure_features(self, file_structure: List[str]) -> Dict:
        """
        ファイル構造特徴を抽出
        
        - ファイル数の異常度
        - 重要なファイルの存在
        - ファイル名の異常パターン
        """
        file_names = [f.split('/')[-1] for f in file_structure]  # ファイル名のみ
        
        features = {
            'file_count': len(file_structure),
            'has_package_json': 'package.json' in file_names,
            'has_readme': any('readme' in f.lower() for f in file_names),
            'has_license': any('license' in f.lower() for f in file_names),
            'has_test_files': any('test' in f.lower() for f in file_names),
            'has_config_files': any(f.endswith(('.json', '.yaml', '.yml', '.config')) for f in file_names),
        }
        
        # 異常パターン
        features['suspicious_file_patterns'] = self._detect_suspicious_file_patterns(file_structure)
        features['minified_files'] = sum(1 for f in file_structure if f.endswith('.min.js'))
        features['obfuscated_files'] = sum(1 for f in file_structure if 'obfuscated' in f.lower() or 'min' in f.lower())
        
        return features
    
    def _string_similarity(self, s1: str, s2: str) -> float:
        """2つの文字列の類似度を計算（SequenceMatcher使用）"""
        return SequenceMatcher(None, s1.lower(), s2.lower()).ratio()
    
    def _detect_suspicious_patterns(self, package_name: str) -> Dict:
        """パッケージ名の異常パターンを検出"""
        patterns = {
            'has_random_strings': bool(re.search(r'[a-z]{10,}', package_name)),  # 長いランダム文字列
            'has_repeated_chars': bool(re.search(r'(.)\1{3,}', package_name)),  # 同じ文字の繰り返し
            'has_special_chars': bool(re.search(r'[^a-zA-Z0-9\-_@]', package_name)),
            'is_too_short': len(package_name) < 3,
            'is_too_long': len(package_name) > 50,
        }
        return patterns
    
    def _is_valid_url_format(self, url: str) -> bool:
        """URL形式が有効かどうかをチェック"""
        url_pattern = re.compile(
            r'^https?://'  # http:// or https://
            r'(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+[A-Z]{2,6}\.?|'  # domain...
            r'localhost|'  # localhost...
            r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})'  # ...or ip
            r'(?::\d+)?'  # optional port
            r'(?:/?|[/?]\S+)$', re.IGNORECASE)
        return bool(url_pattern.match(url))
    
    def _detect_suspicious_repo_patterns(self, url: str) -> bool:
        """リポジトリURLの異常パターンを検出"""
        suspicious_patterns = [
            r'bit\.ly',  # 短縮URL
            r'tinyurl\.com',
            r'goo\.gl',
            r'[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}',  # IPアドレス直接
        ]
        
        for pattern in suspicious_patterns:
            if re.search(pattern, url, re.IGNORECASE):
                return True
        return False
    
    def _detect_suspicious_file_patterns(self, file_structure: List[str]) -> int:
        """ファイル構造の異常パターンを検出"""
        suspicious_count = 0
        
        suspicious_patterns = [
            r'eval',
            r'obfuscat',
            r'encrypt',
            r'hidden',
            r'\.bin$',
            r'\.exe$',
        ]
        
        for file_path in file_structure:
            for pattern in suspicious_patterns:
                if re.search(pattern, file_path, re.IGNORECASE):
                    suspicious_count += 1
                    break
        
        return suspicious_count
    
    def _empty_repository_features(self) -> Dict:
        """空のリポジトリ特徴を返す"""
        return {
            'has_repository': False,
            'repository_url_length': 0,
            'is_github': False,
            'is_gitlab': False,
            'is_bitbucket': False,
            'is_git': False,
            'repository_url_valid_format': False,
            'suspicious_repository_pattern': False,
        }
    
    def _empty_file_structure_features(self) -> Dict:
        """空のファイル構造特徴を返す"""
        return {
            'file_count': 0,
            'has_package_json': False,
            'has_readme': False,
            'has_license': False,
            'has_test_files': False,
            'has_config_files': False,
            'suspicious_file_patterns': 0,
            'minified_files': 0,
            'obfuscated_files': 0,
        }


if __name__ == "__main__":
    # テスト実行
    popular_packages = ['lodash', 'express', 'react', 'vue', 'angular']
    extractor = StaticFeatureExtractor(popular_packages)
    
    # typosquattingテスト
    test_name = "lodashh"  # lodashのtyposquatting
    features = extractor.extract_name_features(test_name)
    print("Name features:", features)
    print("Potential typosquatting:", features['potential_typosquatting'])
