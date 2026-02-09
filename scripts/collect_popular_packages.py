#!/usr/bin/env python3
"""
人気パッケージリストを収集するスクリプト

NPM検索APIを使用して人気パッケージを収集し、typosquatting検出用のリストを作成する。
"""

import sys
from pathlib import Path

# プロジェクトルートをパスに追加
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.data.collectors.npm_collector import NPMCollector
import json

def collect_popular_packages(output_file: str = "data/raw/popular_packages.json"):
    """人気パッケージを収集"""
    collector = NPMCollector()
    
    # 検索クエリ（人気パッケージのキーワード）
    search_queries = [
        "react", "vue", "angular", "express", "lodash", "axios",
        "webpack", "babel", "typescript", "jest", "mocha", "chai",
        "moment", "jquery", "bootstrap", "tailwind", "next", "nuxt",
        "graphql", "apollo", "redux", "mobx", "socket.io", "ws",
        "mongoose", "sequelize", "prisma", "knex", "typeorm"
    ]
    
    popular_packages = set()
    
    print("Collecting popular packages...")
    for i, query in enumerate(search_queries):
        print(f"Searching for '{query}' ({i+1}/{len(search_queries)})...")
        results = collector.search_packages(query, size=20)
        
        for result in results:
            package_name = result.get('package', {}).get('name')
            if package_name:
                popular_packages.add(package_name)
    
    popular_packages = sorted(list(popular_packages))
    
    print(f"\nCollected {len(popular_packages)} unique popular packages")
    
    # 保存
    output_path = project_root / output_file
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    with open(output_path, 'w') as f:
        json.dump(popular_packages, f, indent=2)
    
    print(f"Saved to {output_path}")
    
    return popular_packages

if __name__ == "__main__":
    collect_popular_packages()
