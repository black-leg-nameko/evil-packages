#!/bin/bash
# 環境セットアップスクリプト

echo "Setting up research environment..."

# Python仮想環境の作成
python3 -m venv venv
source venv/bin/activate

# 依存関係のインストール
pip install --upgrade pip
pip install -r requirements.txt

# NLTKデータのダウンロード
python3 -c "import nltk; nltk.download('punkt'); nltk.download('stopwords')"

# ディレクトリの作成
mkdir -p data/raw
mkdir -p data/processed
mkdir -p data/splits
mkdir -p results/models
mkdir -p results/figures
mkdir -p results/reports
mkdir -p notebooks

echo "Environment setup complete!"
echo "To activate the virtual environment, run: source venv/bin/activate"
