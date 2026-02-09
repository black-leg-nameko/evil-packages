"""
自然言語特徴抽出モジュール

README、説明文、更新履歴から自然言語特徴を抽出する。
"""

import re
import numpy as np
from typing import Dict, List, Optional
from collections import Counter
import nltk
from nltk.tokenize import word_tokenize, sent_tokenize
from nltk.corpus import stopwords
from sentence_transformers import SentenceTransformer
import logging

logger = logging.getLogger(__name__)

# NLTKデータのダウンロード（初回のみ）
try:
    nltk.data.find('tokenizers/punkt')
except LookupError:
    nltk.download('punkt', quiet=True)

try:
    nltk.data.find('corpora/stopwords')
except LookupError:
    nltk.download('stopwords', quiet=True)


class NLPFeatureExtractor:
    """自然言語特徴を抽出するクラス"""
    
    def __init__(self, model_name: str = "all-MiniLM-L6-v2"):
        """
        Args:
            model_name: SentenceTransformerモデル名
        """
        self.model = SentenceTransformer(model_name)
        self.stop_words = set(stopwords.words('english'))
    
    def extract_all_features(self, text: str, readme: Optional[str] = None) -> Dict:
        """
        すべての自然言語特徴を抽出
        
        Args:
            text: 説明文やREADMEテキスト
            readme: READMEファイルの内容（別途提供される場合）
            
        Returns:
            特徴量の辞書
        """
        features = {}
        
        # スタイル特徴
        features.update(self.extract_style_features(text))
        
        # セマンティック特徴
        features.update(self.extract_semantic_features(text))
        
        # README特徴（別途提供される場合）
        if readme:
            features.update(self.extract_readme_features(readme))
        
        return features
    
    def extract_style_features(self, text: str) -> Dict:
        """
        スタイル特徴を抽出
        
        - 語彙多様性
        - 文長
        - 記号使用
        - 大文字小文字の比率
        """
        if not text:
            return self._empty_style_features()
        
        # トークン化
        sentences = sent_tokenize(text)
        words = word_tokenize(text.lower())
        words_no_stop = [w for w in words if w.isalpha() and w not in self.stop_words]
        
        features = {
            # 基本統計
            'char_count': len(text),
            'word_count': len(words),
            'sentence_count': len(sentences),
            'avg_sentence_length': np.mean([len(s.split()) for s in sentences]) if sentences else 0,
            'avg_word_length': np.mean([len(w) for w in words if w.isalpha()]) if words else 0,
            
            # 語彙多様性
            'unique_word_ratio': len(set(words)) / len(words) if words else 0,
            'vocabulary_richness': len(set(words_no_stop)) / len(words_no_stop) if words_no_stop else 0,
            
            # 記号・特殊文字
            'punctuation_ratio': sum(1 for c in text if c in '.,!?;:') / len(text) if text else 0,
            'digit_ratio': sum(1 for c in text if c.isdigit()) / len(text) if text else 0,
            'uppercase_ratio': sum(1 for c in text if c.isupper()) / len(text) if text else 0,
            'special_char_ratio': sum(1 for c in text if not c.isalnum() and c != ' ') / len(text) if text else 0,
            
            # URL・メールアドレス
            'url_count': len(re.findall(r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+', text)),
            'email_count': len(re.findall(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b', text)),
            
            # 言語的特徴
            'exclamation_count': text.count('!'),
            'question_count': text.count('?'),
            'ellipsis_count': text.count('...'),
        }
        
        return features
    
    def extract_semantic_features(self, text: str) -> Dict:
        """
        セマンティック特徴を抽出
        
        - BERT埋め込み（SentenceTransformer）
        - トピックモデル的な特徴（簡易版）
        """
        if not text:
            return {
                'embedding_mean': np.zeros(384),  # all-MiniLM-L6-v2の次元数
                'embedding_std': np.zeros(384),
            }
        
        # 文ごとに埋め込みを取得
        sentences = sent_tokenize(text)
        if not sentences:
            sentences = [text]
        
        embeddings = self.model.encode(sentences)
        
        features = {
            'embedding_mean': np.mean(embeddings, axis=0).tolist(),
            'embedding_std': np.std(embeddings, axis=0).tolist(),
            'embedding_max': np.max(embeddings, axis=0).tolist(),
            'embedding_min': np.min(embeddings, axis=0).tolist(),
        }
        
        return features
    
    def extract_readme_features(self, readme: str) -> Dict:
        """
        README特有の特徴を抽出
        
        - セクション構造
        - コードブロックの有無
        - 画像・リンクの数
        """
        if not readme:
            return self._empty_readme_features()
        
        features = {
            # セクション構造
            'heading_count': len(re.findall(r'^#+\s', readme, re.MULTILINE)),
            'code_block_count': len(re.findall(r'```', readme)),
            'inline_code_count': len(re.findall(r'`[^`]+`', readme)),
            
            # リンク・画像
            'link_count': len(re.findall(r'\[([^\]]+)\]\(([^\)]+)\)', readme)),
            'image_count': len(re.findall(r'!\[([^\]]*)\]\(([^\)]+)\)', readme)),
            
            # リスト
            'bullet_list_count': len(re.findall(r'^\s*[-*+]\s', readme, re.MULTILINE)),
            'numbered_list_count': len(re.findall(r'^\s*\d+\.\s', readme, re.MULTILINE)),
            
            # その他
            'table_count': len(re.findall(r'\|', readme)) // 3,  # 簡易的なテーブル検出
        }
        
        return features
    
    def compute_similarity(self, text1: str, text2: str) -> float:
        """
        2つのテキスト間の類似度を計算（コサイン類似度）
        
        Args:
            text1: テキスト1
            text2: テキスト2
            
        Returns:
            コサイン類似度（0-1）
        """
        if not text1 or not text2:
            return 0.0
        
        emb1 = self.model.encode(text1)
        emb2 = self.model.encode(text2)
        
        # コサイン類似度
        similarity = np.dot(emb1, emb2) / (np.linalg.norm(emb1) * np.linalg.norm(emb2))
        return float(similarity)
    
    def _empty_style_features(self) -> Dict:
        """空のスタイル特徴を返す"""
        return {
            'char_count': 0,
            'word_count': 0,
            'sentence_count': 0,
            'avg_sentence_length': 0,
            'avg_word_length': 0,
            'unique_word_ratio': 0,
            'vocabulary_richness': 0,
            'punctuation_ratio': 0,
            'digit_ratio': 0,
            'uppercase_ratio': 0,
            'special_char_ratio': 0,
            'url_count': 0,
            'email_count': 0,
            'exclamation_count': 0,
            'question_count': 0,
            'ellipsis_count': 0,
        }
    
    def _empty_readme_features(self) -> Dict:
        """空のREADME特徴を返す"""
        return {
            'heading_count': 0,
            'code_block_count': 0,
            'inline_code_count': 0,
            'link_count': 0,
            'image_count': 0,
            'bullet_list_count': 0,
            'numbered_list_count': 0,
            'table_count': 0,
        }


if __name__ == "__main__":
    # テスト実行
    extractor = NLPFeatureExtractor()
    
    test_text = """
    This is a simple test package for demonstration purposes.
    It provides basic functionality for testing and development.
    Please refer to the documentation for more information.
    """
    
    features = extractor.extract_all_features(test_text)
    print("Style features:", {k: v for k, v in features.items() if 'embedding' not in k})
    print("Semantic features shape:", len(features.get('embedding_mean', [])))
