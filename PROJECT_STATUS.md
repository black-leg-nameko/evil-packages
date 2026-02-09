# プロジェクトステータス

## 完了したタスク ✅

### 1. 既存研究の徹底調査
- [x] 研究分類マトリクスの作成 (`research/literature_review/research_classification.md`)
- [x] 論文分析テンプレートの作成 (`research/literature_review/paper_analysis_template.md`)
- [x] 主要研究（Cerebro, MalGuard, ConfuGuard等）の課題抽出

### 2. データセット構築
- [x] NPMデータ収集モジュール (`src/data/collectors/npm_collector.py`)
- [x] OSVデータ収集モジュール (`src/data/collectors/osv_collector.py`)
- [x] データパイプライン (`src/data/pipeline.py`)
- [x] 時系列分割機能の実装

### 3. 特徴設計
- [x] 自然言語特徴抽出 (`src/features/nlp_features.py`)
  - スタイル特徴（語彙多様性、文長、記号使用）
  - セマンティック特徴（BERT埋め込み）
  - README特徴
- [x] メタデータ特徴抽出 (`src/features/metadata_features.py`)
  - 依存関係特徴
  - 公開パターン特徴
  - 作者履歴特徴
- [x] 静的特徴抽出 (`src/features/static_features.py`)
  - パッケージ名類似度（typosquatting検出）
  - リポジトリURL特徴
  - ファイル構造特徴

### 4. モデル設計
- [x] 異常検知モデル (`src/models/anomaly_detector.py`)
  - Isolation Forest実装
  - AutoEncoder実装
  - マルチモーダル融合モデル

### 5. 評価プロトコル
- [x] 評価指標モジュール (`src/evaluation/metrics.py`)
  - Time-to-Warn指標
  - Precision@K指標
  - False Positive分析
  - 時系列評価

### 6. 実装と実験
- [x] Colabノートブックの作成
  - [x] データ収集 (`notebooks/01_data_collection.ipynb`)
  - [ ] 特徴抽出 (`notebooks/02_feature_extraction.ipynb`) - 作成済みだが確認必要
  - [ ] モデル学習 (`notebooks/03_model_training.ipynb`) - 作成済みだが確認必要
  - [x] 評価 (`notebooks/04_evaluation.ipynb`)

### 7. 論文執筆
- [x] 論文テンプレート (`research/paper/paper_template.md`)
- [x] 参考文献リスト (`research/paper/bibliography.md`)

## 追加で作成したファイル

- [x] README.md - プロジェクト概要
- [x] requirements.txt - Python依存関係
- [x] .gitignore - Git除外設定
- [x] CONTRIBUTING.md - 貢献ガイド
- [x] scripts/setup_environment.sh - 環境セットアップスクリプト
- [x] scripts/collect_popular_packages.py - 人気パッケージ収集スクリプト
- [x] research/notes/research_notes.md - 研究ノート

## 次のステップ

### 即座に実行可能
1. **環境セットアップ**
   ```bash
   ./scripts/setup_environment.sh
   source venv/bin/activate
   ```

2. **データ収集の開始**
   - Colabで `notebooks/01_data_collection.ipynb` を実行
   - 悪性パッケージリストの準備（既存研究から取得）

3. **実験の実行**
   - 特徴抽出 → モデル学習 → 評価の順で実行

### データ収集が必要
- **悪性パッケージデータ**: 既存研究（Cerebro, MalGuard）のデータセットから取得
- **OSVデータ**: API経由で自動収集可能
- **良性パッケージデータ**: NPM API経由で自動収集可能

### 論文執筆
- Introduction: サプライチェーン攻撃の現状と早期検知の重要性
- Related Work: 既存研究の分類と課題（`research_classification.md`を参照）
- Methodology: 実装済みの特徴設計とモデル設計を説明
- Evaluation: 実験結果を記述（実験実行後）
- Discussion: 限界と今後の課題

## プロジェクト構造

```
evil_package/
├── README.md                    # プロジェクト概要
├── requirements.txt             # Python依存関係
├── CONTRIBUTING.md              # 貢献ガイド
├── PROJECT_STATUS.md           # このファイル
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
│   ├── paper/                   # 論文
│   └── notes/                   # 研究ノート
├── results/                     # 実験結果
│   ├── models/                  # 学習済みモデル
│   ├── figures/                 # 図表
│   └── reports/                 # 評価レポート
└── scripts/                     # スクリプト
    ├── setup_environment.sh
    └── collect_popular_packages.py
```

## 技術スタック

- **Python 3.8+**
- **主要ライブラリ**:
  - transformers (BERT埋め込み)
  - scikit-learn (異常検知、評価指標)
  - torch (AutoEncoder)
  - pandas, numpy (データ処理)
  - requests (API呼び出し)

## 注意事項

1. **APIレート制限**: NPM APIとOSV APIにはレート制限があるため、適切な遅延を設定
2. **データの再現性**: データ収集日時を記録し、再現可能にする
3. **Colab環境**: 無料枠での実行を想定（GPU不要）
4. **悪性パッケージデータ**: 既存研究のデータセットを利用するか、手動でリスト化が必要

## 完了基準

- [x] コード実装完了
- [x] 評価プロトコル実装完了
- [x] 論文テンプレート作成完了
- [ ] 実験実行完了（データ収集後）
- [ ] 論文執筆完了（実験結果後）
