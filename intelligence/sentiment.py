"""
Sentiment Analyzer - Analyze sentiment from news and text
"""
from textblob import TextBlob
from typing import List, Dict
import re


class SentimentAnalyzer:
    """Analyze sentiment of financial news and text"""

    # Financial sentiment keywords (weighted)
    BULLISH_WORDS = {
        'surge': 2, 'soar': 2, 'jump': 1.5, 'rally': 2, 'gain': 1,
        'rise': 1, 'climb': 1, 'bullish': 2, 'breakout': 2, 'moon': 1.5,
        'buy': 1.5, 'upgrade': 1.5, 'beat': 1, 'strong': 1, 'growth': 1,
        'profit': 1, 'record': 1.5, 'high': 0.5, 'positive': 1,
        'outperform': 1.5, 'boom': 2, 'rocket': 2, 'pump': 1.5
    }

    BEARISH_WORDS = {
        'crash': 2, 'plunge': 2, 'drop': 1.5, 'fall': 1, 'decline': 1,
        'sink': 1.5, 'bearish': 2, 'dump': 2, 'sell': 1.5, 'downgrade': 1.5,
        'miss': 1, 'weak': 1, 'loss': 1, 'low': 0.5, 'negative': 1,
        'underperform': 1.5, 'bust': 2, 'collapse': 2, 'fear': 1.5,
        'concern': 1, 'risk': 0.5, 'warning': 1.5, 'trouble': 1.5
    }

    def analyze_text(self, text: str) -> Dict:
        """Analyze sentiment of a single text"""
        if not text:
            return {'score': 0, 'label': 'neutral', 'confidence': 0}

        text_lower = text.lower()

        # TextBlob sentiment
        blob = TextBlob(text)
        tb_sentiment = blob.sentiment.polarity  # -1 to 1

        # Custom financial sentiment
        bullish_score = sum(
            weight for word, weight in self.BULLISH_WORDS.items()
            if word in text_lower
        )
        bearish_score = sum(
            weight for word, weight in self.BEARISH_WORDS.items()
            if word in text_lower
        )

        # Combine scores
        financial_score = (bullish_score - bearish_score) / max(bullish_score + bearish_score, 1)

        # Weighted average (financial sentiment weighted more)
        combined_score = (tb_sentiment * 0.3) + (financial_score * 0.7)

        # Normalize to -100 to 100
        score = int(combined_score * 100)
        score = max(-100, min(100, score))

        # Determine label
        if score > 20:
            label = 'bullish'
        elif score > 5:
            label = 'slightly_bullish'
        elif score < -20:
            label = 'bearish'
        elif score < -5:
            label = 'slightly_bearish'
        else:
            label = 'neutral'

        confidence = abs(score)

        return {
            'score': score,
            'label': label,
            'confidence': confidence,
            'bullish_signals': bullish_score,
            'bearish_signals': bearish_score
        }

    def analyze_news_batch(self, news_items: List[Dict]) -> Dict:
        """Analyze sentiment across multiple news items"""
        if not news_items:
            return {
                'overall_score': 0,
                'overall_label': 'neutral',
                'bullish_count': 0,
                'bearish_count': 0,
                'neutral_count': 0,
                'articles_analyzed': 0
            }

        scores = []
        bullish_count = 0
        bearish_count = 0
        neutral_count = 0

        for item in news_items:
            text = item.get('title', '') + " " + item.get('summary', '')
            sentiment = self.analyze_text(text)

            scores.append(sentiment['score'])
            item['sentiment'] = sentiment

            if sentiment['label'] in ['bullish', 'slightly_bullish']:
                bullish_count += 1
            elif sentiment['label'] in ['bearish', 'slightly_bearish']:
                bearish_count += 1
            else:
                neutral_count += 1

        overall_score = sum(scores) / len(scores) if scores else 0

        if overall_score > 15:
            overall_label = 'bullish'
        elif overall_score > 5:
            overall_label = 'slightly_bullish'
        elif overall_score < -15:
            overall_label = 'bearish'
        elif overall_score < -5:
            overall_label = 'slightly_bearish'
        else:
            overall_label = 'neutral'

        return {
            'overall_score': int(overall_score),
            'overall_label': overall_label,
            'bullish_count': bullish_count,
            'bearish_count': bearish_count,
            'neutral_count': neutral_count,
            'articles_analyzed': len(news_items)
        }

    def get_sentiment_signal(self, sentiment_data: Dict) -> Dict:
        """Convert sentiment analysis to trading signal"""
        score = sentiment_data.get('overall_score', 0)
        bullish = sentiment_data.get('bullish_count', 0)
        bearish = sentiment_data.get('bearish_count', 0)
        total = sentiment_data.get('articles_analyzed', 0)

        if total == 0:
            return {
                'signal': 'NEUTRAL',
                'strength': 0,
                'reason': 'Ingen nyheder at analysere'
            }

        bullish_ratio = bullish / total if total > 0 else 0

        if score > 25 and bullish_ratio > 0.6:
            return {
                'signal': 'BUY',
                'strength': min(abs(score), 100),
                'reason': f'Stærkt positiv sentiment ({bullish}/{total} bullish artikler)'
            }
        elif score < -25 and bullish_ratio < 0.4:
            return {
                'signal': 'SELL',
                'strength': min(abs(score), 100),
                'reason': f'Stærkt negativ sentiment ({bearish}/{total} bearish artikler)'
            }
        elif score > 10:
            return {
                'signal': 'SLIGHTLY_BULLISH',
                'strength': min(abs(score), 100),
                'reason': f'Let positiv sentiment'
            }
        elif score < -10:
            return {
                'signal': 'SLIGHTLY_BEARISH',
                'strength': min(abs(score), 100),
                'reason': f'Let negativ sentiment'
            }
        else:
            return {
                'signal': 'NEUTRAL',
                'strength': 50 - abs(score),
                'reason': 'Blandet sentiment i nyheder'
            }
