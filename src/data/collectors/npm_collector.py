"""
NPMパッケージデータ収集モジュール

NPMレジストリからパッケージのメタデータ、README、依存関係などを収集する。
"""

import requests
import json
import time
from typing import Dict, List, Optional
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


class NPMCollector:
    """NPMレジストリからパッケージ情報を収集するクラス"""
    
    BASE_URL = "https://registry.npmjs.org"
    
    def __init__(self, rate_limit_delay: float = 0.1):
        """
        Args:
            rate_limit_delay: APIレート制限を避けるための遅延（秒）
        """
        self.rate_limit_delay = rate_limit_delay
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Malicious-Package-Research/1.0'
        })
    
    def get_package_info(self, package_name: str) -> Optional[Dict]:
        """
        パッケージの基本情報を取得
        
        Args:
            package_name: パッケージ名
            
        Returns:
            パッケージ情報の辞書、取得失敗時はNone
        """
        try:
            url = f"{self.BASE_URL}/{package_name}"
            response = self.session.get(url, timeout=10)
            response.raise_for_status()
            time.sleep(self.rate_limit_delay)
            return response.json()
        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to fetch package {package_name}: {e}")
            return None
    
    def get_package_version(self, package_name: str, version: str = "latest") -> Optional[Dict]:
        """
        特定バージョンのパッケージ情報を取得
        
        Args:
            package_name: パッケージ名
            version: バージョン（デフォルト: latest）
            
        Returns:
            バージョン情報の辞書、取得失敗時はNone
        """
        try:
            url = f"{self.BASE_URL}/{package_name}/{version}"
            response = self.session.get(url, timeout=10)
            response.raise_for_status()
            time.sleep(self.rate_limit_delay)
            return response.json()
        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to fetch version {package_name}@{version}: {e}")
            return None
    
    def extract_metadata(self, package_info: Dict) -> Dict:
        """
        パッケージ情報からメタデータを抽出
        
        Args:
            package_info: NPM APIから取得したパッケージ情報
            
        Returns:
            抽出されたメタデータの辞書
        """
        metadata = {
            'name': package_info.get('name'),
            'description': package_info.get('description', ''),
            'author': self._extract_author(package_info),
            'maintainers': package_info.get('maintainers', []),
            'repository': self._extract_repository(package_info),
            'homepage': package_info.get('homepage', ''),
            'license': self._extract_license(package_info),
            'keywords': package_info.get('keywords', []),
            'versions': list(package_info.get('versions', {}).keys()),
            'time': package_info.get('time', {}),
            'created': package_info.get('time', {}).get('created', ''),
            'modified': package_info.get('time', {}).get('modified', ''),
        }
        
        # 最新バージョンの情報を追加
        latest_version = package_info.get('dist-tags', {}).get('latest')
        if latest_version and latest_version in package_info.get('versions', {}):
            latest_info = package_info['versions'][latest_version]
            metadata.update({
                'latest_version': latest_version,
                'dependencies': latest_info.get('dependencies', {}),
                'devDependencies': latest_info.get('devDependencies', {}),
                'peerDependencies': latest_info.get('peerDependencies', {}),
                'readme': latest_info.get('readme', ''),
                'readme_filename': latest_info.get('readmeFilename', ''),
            })
        
        return metadata
    
    def _extract_author(self, package_info: Dict) -> Dict:
        """著者情報を抽出"""
        author = package_info.get('author')
        if isinstance(author, dict):
            return author
        elif isinstance(author, str):
            return {'name': author}
        return {}
    
    def _extract_repository(self, package_info: Dict) -> Optional[str]:
        """リポジトリURLを抽出"""
        repo = package_info.get('repository')
        if isinstance(repo, dict):
            return repo.get('url', '')
        elif isinstance(repo, str):
            return repo
        return None
    
    def _extract_license(self, package_info: Dict) -> str:
        """ライセンス情報を抽出"""
        license_info = package_info.get('license')
        if isinstance(license_info, dict):
            return license_info.get('type', '')
        elif isinstance(license_info, str):
            return license_info
        return ''
    
    def get_download_stats(self, package_name: str, period: str = "last-month") -> Optional[Dict]:
        """
        ダウンロード統計を取得（npm-stat API使用）
        
        Args:
            package_name: パッケージ名
            period: 期間（last-day, last-week, last-month, last-year）
            
        Returns:
            ダウンロード統計の辞書
        """
        try:
            # 注意: npm-stat APIは非公式で、レート制限がある可能性
            url = f"https://api.npmjs.org/downloads/point/{period}/{package_name}"
            response = self.session.get(url, timeout=10)
            response.raise_for_status()
            time.sleep(self.rate_limit_delay)
            return response.json()
        except requests.exceptions.RequestException as e:
            logger.warning(f"Failed to fetch download stats for {package_name}: {e}")
            return None
    
    def search_packages(self, query: str, size: int = 20) -> List[Dict]:
        """
        パッケージを検索
        
        Args:
            query: 検索クエリ
            size: 取得件数
            
        Returns:
            検索結果のリスト
        """
        try:
            url = f"{self.BASE_URL}/-/v1/search"
            params = {
                'text': query,
                'size': size
            }
            response = self.session.get(url, params=params, timeout=10)
            response.raise_for_status()
            time.sleep(self.rate_limit_delay)
            data = response.json()
            return data.get('objects', [])
        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to search packages: {e}")
            return []


if __name__ == "__main__":
    # テスト実行
    collector = NPMCollector()
    
    # テストパッケージ
    test_package = "lodash"
    info = collector.get_package_info(test_package)
    if info:
        metadata = collector.extract_metadata(info)
        print(json.dumps(metadata, indent=2, ensure_ascii=False))
