# NPM/PyPI悪性パッケージ早期検知研究

## 研究概要

ソフトウェア供給網（NPM/PyPI）における悪性パッケージを、自然言語（README/説明文/更新履歴）とメタデータ（依存関係、公開頻度、作者履歴）を融合したNLP手法で早期検知する研究。

## 貢献

**「新規公開直後に、自然言語 + メタデータ + 弱い静的特徴で、異常検知ベースに"早期警戒スコア"を出す」**

- 目的変数：Time-to-Warn（公開から何分/何時間で検知できるか）
- 差別化：既存のコード解析中心から、公開直後に取得可能な情報のみで判断
- 評価：時系列分割（概念ドリフトを正面から扱う）

## プロジェクト構造

```
evil_package/
├── README.md                    # このファイル
├── requirements.txt             # Python依存関係
├── data/                        # データセット
│   ├── raw/                     # 生データ
│   ├── processed/               # 前処理済みデータ
│   └── splits/                  # 時系列分割データ
├── notebooks/                   # Colabノートブック
│   ├── 01_data_collection.ipynb
│   ├── 02_feature_extraction.ipynb
│   ├── 03_model_training.ipynb
│   └── 04_evaluation.ipynb
├── src/                         # ソースコード
│   ├── data/                    # データ収集・前処理
│   ├── features/                # 特徴抽出
│   ├── models/                  # モデル実装
│   ├── evaluation/              # 評価指標
│   └── utils/                   # ユーティリティ
├── research/                    # 研究資料
│   ├── literature_review/       # 既存研究調査
│   ├── papers/                  # 論文PDF
│   └── notes/                   # 研究ノート
└── results/                     # 実験結果
    ├── models/                  # 学習済みモデル
    ├── figures/                 # 図表
    └── reports/                 # 評価レポート
```

## 既存研究の主要課題

1. **概念ドリフト**: 古いデータで学習したモデルが新しい悪性に効かなくなる
2. **多ファイル分散・難読化**: 攻撃者が複数ファイルに分散したり、リソースファイルに隠す
3. **「悪性っぽいコード」≠「悪性」問題**: 同じAPIコールでも正当用途がある
4. **早期検知**: 公開直後に判断したい（行動ログ待ちは遅い）
5. **データ問題**: 悪性ラベルが少ない/偏る/確定しにくい


## 参考文献

- Cerebro: Malicious behavior sequence detection using BERT
- MalGuard: Real-time detection in PyPI ecosystem
- ConfuGuard: Metadata-based package confusion attack detection
- OSCAR: Dynamic analysis with sandbox execution
- IntelliRadar: LLM-based intelligence extraction
