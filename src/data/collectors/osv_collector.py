"""
OSV (Open Source Vulnerabilities) データベースから脆弱性情報を収集するモジュール
"""

import requests
import json
import time
from typing import Dict, List, Optional
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


class OSVCollector:
    """OSV APIから脆弱性情報を収集するクラス"""
    
    BASE_URL = "https://api.osv.dev/v1"
    
    def __init__(self, rate_limit_delay: float = 0.1):
        """
        Args:
            rate_limit_delay: APIレート制限を避けるための遅延（秒）
        """
        self.rate_limit_delay = rate_limit_delay
        self.session = requests.Session()
        self.session.headers.update({
            'Content-Type': 'application/json',
            'User-Agent': 'Malicious-Package-Research/1.0'
        })
    
    def query_by_package(self, 
                        name: str, 
                        ecosystem: str = "npm",
                        version: Optional[str] = None) -> List[Dict]:
        """
        パッケージ名で脆弱性を検索
        
        Args:
            name: パッケージ名
            ecosystem: エコシステム（npm, PyPI等）
            version: 特定バージョン（省略時は全バージョン）
            
        Returns:
            脆弱性情報のリスト
        """
        try:
            url = f"{self.BASE_URL}/query"
            payload = {
                "package": {
                    "name": name,
                    "ecosystem": ecosystem
                }
            }
            if version:
                payload["version"] = version
            
            response = self.session.post(url, json=payload, timeout=10)
            response.raise_for_status()
            time.sleep(self.rate_limit_delay)
            data = response.json()
            return data.get('vulns', [])
        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to query OSV for {name}: {e}")
            return []
    
    def get_vulnerability(self, vuln_id: str) -> Optional[Dict]:
        """
        脆弱性IDから詳細情報を取得
        
        Args:
            vuln_id: 脆弱性ID（例: GHSA-xxxx-xxxx-xxxx）
            
        Returns:
            脆弱性詳細情報の辞書
        """
        try:
            url = f"{self.BASE_URL}/v1/{vuln_id}"
            response = self.session.get(url, timeout=10)
            response.raise_for_status()
            time.sleep(self.rate_limit_delay)
            return response.json()
        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to fetch vulnerability {vuln_id}: {e}")
            return None
    
    def batch_query(self, queries: List[Dict]) -> List[Dict]:
        """
        複数パッケージの一括検索
        
        Args:
            queries: クエリのリスト（各クエリはquery_by_packageの引数に対応）
            
        Returns:
            結果のリスト
        """
        try:
            url = f"{self.BASE_URL}/querybatch"
            payload = {"queries": queries}
            response = self.session.post(url, json=payload, timeout=30)
            response.raise_for_status()
            time.sleep(self.rate_limit_delay)
            data = response.json()
            return data.get('results', [])
        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to batch query OSV: {e}")
            return []
    
    def extract_vulnerability_features(self, vulns: List[Dict]) -> Dict:
        """
        脆弱性情報から特徴量を抽出
        
        Args:
            vulns: 脆弱性情報のリスト
            
        Returns:
            抽出された特徴量の辞書
        """
        if not vulns:
            return {
                'has_vulnerability': False,
                'vulnerability_count': 0,
                'severity_scores': [],
                'cve_ids': [],
                'affected_versions': []
            }
        
        features = {
            'has_vulnerability': True,
            'vulnerability_count': len(vulns),
            'severity_scores': [],
            'cve_ids': [],
            'affected_versions': [],
            'severity_types': []
        }
        
        for vuln in vulns:
            # CVE ID
            if 'id' in vuln:
                features['cve_ids'].append(vuln['id'])
            
            # 深刻度スコア
            if 'database_specific' in vuln:
                db_spec = vuln['database_specific']
                if 'severity' in db_spec:
                    severity = db_spec['severity']
                    if isinstance(severity, str):
                        features['severity_types'].append(severity)
                    elif isinstance(severity, dict):
                        if 'score' in severity:
                            features['severity_scores'].append(severity['score'])
            
            # 影響を受けるバージョン
            if 'affected' in vuln:
                for affected in vuln['affected']:
                    if 'versions' in affected:
                        features['affected_versions'].extend(affected['versions'])
        
        # 統計情報
        features['max_severity_score'] = max(features['severity_scores']) if features['severity_scores'] else 0
        features['avg_severity_score'] = (
            sum(features['severity_scores']) / len(features['severity_scores'])
            if features['severity_scores'] else 0
        )
        features['unique_cve_count'] = len(set(features['cve_ids']))
        
        return features


if __name__ == "__main__":
    # テスト実行
    collector = OSVCollector()
    
    # テストパッケージ
    test_package = "lodash"
    vulns = collector.query_by_package(test_package, ecosystem="npm")
    print(f"Found {len(vulns)} vulnerabilities for {test_package}")
    
    if vulns:
        features = collector.extract_vulnerability_features(vulns)
        print(json.dumps(features, indent=2, ensure_ascii=False))
