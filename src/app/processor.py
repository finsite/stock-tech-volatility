"""
Processor module for volatility analysis.

Calculates Bollinger Bands, ATR, and extended volatility indicators such as
historical volatility, standard deviation, Keltner Channels, Chaikin Volatility,
Donchian Channels, and Price %B.
"""

from typing import Any
import numpy as np
import pandas as pd

from app.logger import setup_logger

logger = setup_logger(__name__)


def calculate_bollinger_bands(prices: list[float], window: int = 20, num_std: int = 2) -> dict[str, float]:
    if len(prices) < window:
        raise ValueError("Not enough price data for Bollinger Bands calculation.")
    series = pd.Series(prices[-window:])
    sma = series.mean()
    std = series.std()
    return {
        "sma": round(sma, 4),
        "upper_band": round(sma + num_std * std, 4),
        "lower_band": round(sma - num_std * std, 4),
        "percent_b": round((series.iloc[-1] - (sma - num_std * std)) / (2 * num_std * std), 4)
    }


def calculate_atr(highs: list[float], lows: list[float], closes: list[float], window: int = 14) -> float:
    if len(closes) < window + 1:
        raise ValueError("Not enough data for ATR calculation.")
    tr = [max(highs[i] - lows[i], abs(highs[i] - closes[i-1]), abs(lows[i] - closes[i-1]))
          for i in range(1, window + 1)]
    return round(np.mean(tr), 4)


def calculate_std(prices: list[float], window: int = 20) -> float:
    if len(prices) < window:
        raise ValueError("Not enough data for standard deviation.")
    return round(np.std(prices[-window:]), 4)


def calculate_historical_volatility(prices: list[float], window: int = 20) -> float:
    if len(prices) < window + 1:
        raise ValueError("Not enough data for historical volatility.")
    log_returns = np.diff(np.log(prices[-(window + 1):]))
    return round(np.std(log_returns) * np.sqrt(252), 4)  # Annualized volatility


def calculate_keltner_channels(highs: list[float], lows: list[float], closes: list[float], window: int = 20, factor: float = 2.0) -> dict[str, float]:
    if len(closes) < window or len(highs) < window or len(lows) < window:
        raise ValueError("Not enough data for Keltner Channels.")
    closes_series = pd.Series(closes[-window:])
    ema = closes_series.ewm(span=window).mean().iloc[-1]
    atr = calculate_atr(highs, lows, closes, window)
    return {
        "ema": round(ema, 4),
        "upper_channel": round(ema + factor * atr, 4),
        "lower_channel": round(ema - factor * atr, 4)
    }


def calculate_chaikin_volatility(highs: list[float], lows: list[float], window: int = 10) -> float:
    if len(highs) < window * 2 or len(lows) < window * 2:
        raise ValueError("Not enough data for Chaikin Volatility.")
    hl_range = pd.Series([h - l for h, l in zip(highs, lows)])
    ema_short = hl_range.ewm(span=window).mean()
    chaikin_vol = ((ema_short - ema_short.shift(window)) / ema_short.shift(window)) * 100
    return round(chaikin_vol.iloc[-1], 4)


def calculate_donchian_channels(highs: list[float], lows: list[float], window: int = 20) -> dict[str, float]:
    if len(highs) < window or len(lows) < window:
        raise ValueError("Not enough data for Donchian Channels.")
    return {
        "upper_channel": round(max(highs[-window:]), 4),
        "lower_channel": round(min(lows[-window:]), 4)
    }


def analyze_volatility(symbol: str, data: dict[str, Any]) -> dict[str, Any]:
    """
    Applies volatility analysis to incoming stock data.

    Args:
        symbol (str): Stock symbol.
        data (dict[str, Any]): Must include 'close_prices', 'highs', and 'lows'.

    Returns:
        dict[str, Any]: Analysis results.
    """
    try:
        logger.info("Analyzing volatility for %s", symbol)

        prices = data["close_prices"]
        highs = data["highs"]
        lows = data["lows"]
        closes = prices  # closes == prices for our model

        result = {
            "symbol": symbol,
            "analysis_type": "volatility",
            "bollinger_bands": calculate_bollinger_bands(prices),
            "atr": calculate_atr(highs, lows, closes),
            "stddev": calculate_std(prices),
            "historical_volatility": calculate_historical_volatility(prices),
            "keltner_channels": calculate_keltner_channels(highs, lows, closes),
            "chaikin_volatility": calculate_chaikin_volatility(highs, lows),
            "donchian_channels": calculate_donchian_channels(highs, lows),
        }

        logger.info("Volatility analysis complete for %s", symbol)
        return result

    except Exception as e:
        logger.exception("Failed to analyze volatility for %s: %s", symbol, str(e))
        raise
