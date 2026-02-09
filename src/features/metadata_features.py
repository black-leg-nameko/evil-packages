"""
メタデータ特徴抽出モジュール

依存関係、公開パターン、作者履歴からメタデータ特徴を抽出する。
"""

import numpy as np
from typing import Dict, List, Optional
from datetime import datetime, timedelta
from collections import Counter
import logging

logger = logging.getLogger(__name__)


class MetadataFeatureExtractor:
    """メタデータ特徴を抽出するクラス"""
    
    def __init__(self, osv_features: Optional[Dict] = None):
        """
        Args:
            osv_features: OSVから取得した脆弱性特徴（オプション）
        """
        self.osv_features = osv_features or {}
    
    def extract_all_features(self, 
                           package_metadata: Dict,
                           author_history: Optional[List[Dict]] = None,
                           osv_features: Optional[Dict] = None) -> Dict:
        """
        すべてのメタデータ特徴を抽出
        
        Args:
            package_metadata: パッケージのメタデータ
            author_history: 作者の過去パッケージ履歴
            osv_features: OSV脆弱性特徴
            
        Returns:
            特徴量の辞書
        """
        features = {}
        
        # 依存関係特徴
        features.update(self.extract_dependency_features(package_metadata, osv_features))
        
        # 公開パターン特徴
        features.update(self.extract_publication_features(package_metadata))
        
        # 作者履歴特徴
        if author_history:
            features.update(self.extract_author_features(package_metadata, author_history))
        else:
            features.update(self.extract_author_features_basic(package_metadata))
        
        return features
    
    def extract_dependency_features(self, 
                                   package_metadata: Dict,
                                   osv_features: Optional[Dict] = None) -> Dict:
        """
        依存関係特徴を抽出
        
        - 依存の深さと複雑度
        - OSVベースの脆弱性伝播リスク
        - 新規/既存依存の比率
        """
        deps = package_metadata.get('dependencies', {})
        dev_deps = package_metadata.get('devDependencies', {})
        peer_deps = package_metadata.get('peerDependencies', {})
        
        all_deps = {**deps, **dev_deps, **peer_deps}
        
        features = {
            # 依存関係の基本統計
            'dependency_count': len(deps),
            'dev_dependency_count': len(dev_deps),
            'peer_dependency_count': len(peer_deps),
            'total_dependency_count': len(all_deps),
            
            # 依存関係の複雑度
            'has_dependencies': len(deps) > 0,
            'has_dev_dependencies': len(dev_deps) > 0,
            'dependency_depth': self._estimate_dependency_depth(all_deps),  # 簡易推定
            
            # OSV脆弱性特徴（提供される場合）
            'has_vulnerable_dependency': osv_features.get('has_vulnerability', False) if osv_features else False,
            'vulnerability_count': osv_features.get('vulnerability_count', 0) if osv_features else 0,
            'max_severity_score': osv_features.get('max_severity_score', 0) if osv_features else 0,
            'avg_severity_score': osv_features.get('avg_severity_score', 0) if osv_features else 0,
        }
        
        # 依存関係のバージョン範囲分析
        if all_deps:
            version_patterns = self._analyze_version_patterns(list(all_deps.values()))
            features.update(version_patterns)
        
        return features
    
    def extract_publication_features(self, package_metadata: Dict) -> Dict:
        """
        公開パターン特徴を抽出
        
        - 公開頻度（初回公開から更新までの時間）
        - バージョン履歴の異常度
        """
        versions = package_metadata.get('versions', [])
        time_info = package_metadata.get('time', {})
        created = package_metadata.get('created', '')
        modified = package_metadata.get('modified', '')
        
        features = {
            # バージョン情報
            'version_count': len(versions),
            'has_multiple_versions': len(versions) > 1,
            
            # 時間情報
            'created_timestamp': self._parse_timestamp(created),
            'modified_timestamp': self._parse_timestamp(modified),
        }
        
        # 公開から更新までの時間
        if created and modified:
            created_dt = self._parse_timestamp(created)
            modified_dt = self._parse_timestamp(modified)
            if created_dt and modified_dt:
                time_diff = (modified_dt - created_dt).total_seconds()
                features['time_to_first_update'] = time_diff / 3600  # 時間単位
                features['update_frequency'] = len(versions) / max(time_diff / 86400, 1)  # バージョン/日
        
        # バージョン履歴の異常度
        if len(versions) > 1:
            version_sequence = self._analyze_version_sequence(versions, time_info)
            features.update(version_sequence)
        
        return features
    
    def extract_author_features(self, 
                               package_metadata: Dict,
                               author_history: List[Dict]) -> Dict:
        """
        作者履歴特徴を抽出（履歴が提供される場合）
        
        - 過去パッケージの信頼度
        - 同時公開パッケージ数
        - アカウント作成からの経過時間
        """
        author_name = self._extract_author_name(package_metadata)
        
        features = {
            'author_package_count': len(author_history),
            'author_has_history': len(author_history) > 0,
        }
        
        if author_history:
            # 過去パッケージの統計
            features['author_avg_downloads'] = np.mean([
                pkg.get('downloads', 0) for pkg in author_history
            ])
            features['author_total_downloads'] = sum([
                pkg.get('downloads', 0) for pkg in author_history
            ])
            
            # 同時公開パッケージ数（最近30日以内）
            recent_packages = [
                pkg for pkg in author_history
                if self._is_recent(pkg.get('created', ''), days=30)
            ]
            features['author_recent_packages'] = len(recent_packages)
        
        return features
    
    def extract_author_features_basic(self, package_metadata: Dict) -> Dict:
        """
        作者特徴を抽出（履歴なし、基本情報のみ）
        
        - アカウント作成からの経過時間（推定）
        """
        author = self._extract_author_name(package_metadata)
        created = package_metadata.get('created', '')
        
        features = {
            'has_author': bool(author),
            'author_name_length': len(author) if author else 0,
        }
        
        # 作成日からの経過時間
        if created:
            created_dt = self._parse_timestamp(created)
            if created_dt:
                now = datetime.now()
                days_since_creation = (now - created_dt).days
                features['days_since_creation'] = days_since_creation
                features['is_new_account'] = days_since_creation < 30
        
        return features
    
    def _estimate_dependency_depth(self, dependencies: Dict) -> int:
        """依存関係の深さを簡易推定（実際には再帰的に探索する必要がある）"""
        # 簡易版: 直接依存のみをカウント
        return 1 if dependencies else 0
    
    def _analyze_version_patterns(self, version_specs: List[str]) -> Dict:
        """バージョン指定パターンを分析"""
        patterns = {
            'exact_version_count': 0,
            'range_version_count': 0,
            'caret_version_count': 0,
            'tilde_version_count': 0,
        }
        
        for spec in version_specs:
            if spec.startswith('^'):
                patterns['caret_version_count'] += 1
            elif spec.startswith('~'):
                patterns['tilde_version_count'] += 1
            elif '-' in spec or '||' in spec:
                patterns['range_version_count'] += 1
            else:
                patterns['exact_version_count'] += 1
        
        return patterns
    
    def _analyze_version_sequence(self, versions: List[str], time_info: Dict) -> Dict:
        """バージョン履歴の異常度を分析"""
        if len(versions) < 2:
            return {}
        
        # バージョン番号の増加パターン
        version_numbers = []
        for v in versions:
            try:
                # セマンティックバージョニングのメジャー番号を抽出
                parts = v.lstrip('v').split('.')
                major = int(parts[0]) if parts[0].isdigit() else 0
                version_numbers.append(major)
            except:
                version_numbers.append(0)
        
        features = {
            'version_sequence_length': len(versions),
            'version_jump_detected': self._detect_version_jumps(version_numbers),
        }
        
        # 更新頻度の異常度
        if time_info:
            update_times = []
            for v in versions:
                if v in time_info:
                    ts = self._parse_timestamp(time_info[v])
                    if ts:
                        update_times.append(ts)
            
            if len(update_times) > 1:
                update_intervals = [
                    (update_times[i+1] - update_times[i]).total_seconds() / 3600
                    for i in range(len(update_times) - 1)
                ]
                features['avg_update_interval_hours'] = np.mean(update_intervals) if update_intervals else 0
                features['update_interval_std'] = np.std(update_intervals) if update_intervals else 0
        
        return features
    
    def _detect_version_jumps(self, version_numbers: List[int]) -> bool:
        """バージョン番号の大きな飛びを検出"""
        if len(version_numbers) < 2:
            return False
        
        for i in range(1, len(version_numbers)):
            if version_numbers[i] - version_numbers[i-1] > 5:  # 5以上の飛び
                return True
        return False
    
    def _parse_timestamp(self, timestamp_str: str) -> Optional[datetime]:
        """タイムスタンプ文字列をパース"""
        if not timestamp_str:
            return None
        
        try:
            # ISO 8601形式を想定
            return datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
        except:
            try:
                # その他の形式
                return datetime.strptime(timestamp_str, '%Y-%m-%dT%H:%M:%S.%fZ')
            except:
                return None
    
    def _is_recent(self, timestamp_str: str, days: int = 30) -> bool:
        """タイムスタンプが最近かどうかを判定"""
        dt = self._parse_timestamp(timestamp_str)
        if not dt:
            return False
        
        now = datetime.now()
        return (now - dt).days < days
    
    def _extract_author_name(self, package_metadata: Dict) -> str:
        """作者名を抽出"""
        author = package_metadata.get('author', {})
        if isinstance(author, dict):
            return author.get('name', '')
        elif isinstance(author, str):
            return author
        return ''


if __name__ == "__main__":
    # テスト実行
    extractor = MetadataFeatureExtractor()
    
    test_metadata = {
        'name': 'test-package',
        'dependencies': {'lodash': '^4.17.21', 'express': '~4.18.0'},
        'devDependencies': {'jest': '27.0.0'},
        'versions': ['1.0.0', '1.0.1', '1.1.0'],
        'created': '2024-01-01T00:00:00Z',
        'modified': '2024-01-15T00:00:00Z',
        'time': {
            '1.0.0': '2024-01-01T00:00:00Z',
            '1.0.1': '2024-01-10T00:00:00Z',
            '1.1.0': '2024-01-15T00:00:00Z',
        },
        'author': {'name': 'test-author'}
    }
    
    features = extractor.extract_all_features(test_metadata)
    print("Metadata features:", features)
