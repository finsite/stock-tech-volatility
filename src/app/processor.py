"""Processor module for volatility analysis.

This module provides functions to calculate various volatility indicators
used in stock market analysis. These include Bollinger Bands, ATR, historical
volatility, standard deviation, Keltner Channels, Chaikin Volatility,
Donchian Channels, and Price %B.
"""

from typing import Any  # Import Any for type annotations

import numpy as np  # Import numpy for numerical operations
import pandas as pd  # Import pandas for data manipulation

from app.logger import setup_logger  # Import logger setup function

# Set up a logger for this module
logger = setup_logger(__name__)


def calculate_bollinger_bands(
    prices: list[float],
    window: int = 20,
    num_std: int = 2
) -> dict[str, float]:
    """Calculate Bollinger Bands for given stock prices.

    Bollinger Bands are a volatility indicator. They consist of a moving average
    and two standard deviations plotted around it. The upper band is the moving
    average plus the standard deviation, and the lower band is the moving average
    minus the standard deviation.

    Parameters:
        prices (list[float]): A list of stock prices.
        window (int): The number of days to use for the moving average and standard
                      deviation. Defaults to 20.
        num_std (int): The number of standard deviations to use for the bands.
                      Defaults to 2.

    Returns:
        dict[str, float]: A dictionary with the following keys:
            - sma (float): The moving average of the prices.
            - upper_band (float): The upper Bollinger Band.
            - lower_band (float): The lower Bollinger Band.
            - percent_b (float): The percent the current price is above the lower Bollinger
                                 Band.
    """
    if len(prices) < window:
        raise ValueError("Not enough price data for Bollinger Bands calculation.")
    series = pd.Series(prices[-window:])
    sma = series.mean()
    std = series.std()
    return {
        "sma": round(sma, 4),
        "upper_band": round(sma + num_std * std, 4),
        "lower_band": round(sma - num_std * std, 4),
        "percent_b": round((series.iloc[-1] - (sma - num_std * std)) / (2 * num_std * std), 4),
    }


def calculate_atr(
    highs: list[float], lows: list[float], closes: list[float], window: int = 14
) -> float:
    """Calculate the Average True Range (ATR) for given stock prices.

    ATR is a measure of volatility. It is the moving average of the true range
    over a given period.

    Parameters:
        highs (list of float): A list of daily highs.
        lows (list of float): A list of daily lows.
        closes (list of float): A list of daily closes.
        window (int): The number of days to use for the moving average. Defaults to 14.

    Returns:
        float: The ATR for the given period.
    """
    if len(closes) < window + 1:
        raise ValueError("Not enough data for ATR calculation.")
    # Calculate the true range for each day
    tr = [
        # The true range is the greatest of:
        # 1. The difference between the high and low of the day
        # 2. The absolute difference between the high and the previous close
        # 3. The absolute difference between the low and the previous close
        max(highs[i] - lows[i], abs(highs[i] - closes[i - 1]), abs(lows[i] - closes[i - 1]))
        for i in range(1, window + 1)
    ]
    # Calculate the average true range over the given period
    return round(np.mean(tr), 4)


def calculate_std(
    prices: list[float],  # A list of prices to calculate the standard deviation for.
    window: int = 20  # The number of prices to use for the calculation. Defaults to 20.
) -> float:  # The standard deviation of the given prices.
    """
    Calculate the standard deviation of a given list of prices.

    Parameters:
        prices (list of float): A list of prices to calculate the standard deviation for.
        window (int): The number of prices to use for the calculation. Defaults to 20.

    Returns:
        float: The standard deviation of the given prices.

    Raises:
        ValueError: If there is not enough data for the calculation.
    """
    if len(prices) < window:
        raise ValueError("Not enough data for standard deviation.")
    return round(np.std(prices[-window:]), 4)


def calculate_historical_volatility(
    prices: List[float],  # A list of prices to calculate the historical volatility for.
    window: int = 20  # The number of prices to use for the calculation. Defaults to 20.
) -> float:  # The historical volatility of the given prices.
    """
    Calculate the historical volatility of a stock using the given prices.

    Parameters:
        prices (List[float]): A list of prices to calculate the historical volatility for.
        window (int): The number of prices to use for the calculation. Defaults to 20.

    Returns:
        float: The historical volatility of the given prices.

    Raises:
        ValueError: If there is not enough data for the calculation.
    """
    if len(prices) < window + 1:
        raise ValueError("Not enough data for historical volatility.")
    # Calculate the logarithmic returns
    log_returns = np.diff(np.log(prices[-(window + 1) :]))
    # Calculate the standard deviation of the logarithmic returns
    # and annualize it
    return round(np.std(log_returns) * np.sqrt(252), 4)


def calculate_keltner_channels(
    highs: List[float],  # A list of daily highs.
    lows: List[float],  # A list of daily lows.
    closes: List[float],  # A list of daily closes.
    window: int = 20,  # The number of days to use for the moving average and ATR. Defaults to 20.
    factor: float = 2.0,  # The factor to multiply the ATR by. Defaults to 2.0.
) -> Dict[str, float]:  # A dictionary with the following keys:
    """
    Calculate Keltner Channels for given stock prices.

    Keltner Channels are a volatility indicator. They consist of a center line
    (usually the Exponential Moving Average (EMA)) and two channels plotted
    around it. The upper channel is the EMA plus the Average True Range (ATR)
    multiplied by a factor, and the lower channel is the EMA minus the ATR
    multiplied by the same factor.

    Parameters:
        highs (List[float]): A list of daily highs.
        lows (List[float]): A list of daily lows.
        closes (List[float]): A list of daily closes.
        window (int): The number of days to use for the moving average and ATR.
                      Defaults to 20.
        factor (float): The factor to multiply the ATR by. Defaults to 2.0.

    Returns:
        Dict[str, float]: A dictionary with the following keys:
            - ema (float): The Exponential Moving Average of the closes.
            - upper_channel (float): The upper Keltner Channel.
            - lower_channel (float): The lower Keltner Channel.
    """
    if len(closes) < window or len(highs) < window or len(lows) < window:
        raise ValueError("Not enough data for Keltner Channels.")
    closes_series = pd.Series(closes[-window:])
    ema = closes_series.ewm(span=window).mean().iloc[-1]
    atr = calculate_atr(highs, lows, closes, window)
    return {
        "ema": round(ema, 4),
        "upper_channel": round(ema + factor * atr, 4),
        "lower_channel": round(ema - factor * atr, 4),
    }


def calculate_chaikin_volatility(
    highs: list[float], lows: list[float], window: int = 10
) -> float:
    """
    Calculate the Chaikin Volatility indicator for given stock prices.

    The Chaikin Volatility indicator is a measure of volatility introduced by
    Marc Chaikin. It is calculated by taking the difference between two moving
    averages of the range between the high and low prices over a given window
    of time. The result is then multiplied by 100 to make it a percentage.

    Parameters:
        highs (list[float]): A list of daily highs.
        lows (list[float]): A list of daily lows.
        window (int): The number of days to use for the moving averages.
                      Defaults to 10.

    Returns:
        float: The Chaikin Volatility indicator.
    """
    if len(highs) < window * 2 or len(lows) < window * 2:
        raise ValueError("Not enough data for Chaikin Volatility.")
    # Calculate the range between high and low prices
    hl_range = pd.Series([h - l for h, l in zip(highs, lows)])
    # Calculate the short and long exponential moving averages
    ema_short = hl_range.ewm(span=window).mean()
    # Calculate the Chaikin Volatility indicator
    chaikin_vol = ((ema_short - ema_short.shift(window)) / ema_short.shift(window)) * 100
    return round(chaikin_vol.iloc[-1], 4)


def calculate_donchian_channels(
    highs: list[float], lows: list[float], window: int = 20
) -> dict[str, float]:
    """
    Calculate the Donchian Channels for given stock prices.

    The Donchian Channels are a measure of volatility introduced by Richard
    Donchian. They are calculated by taking the highest high and lowest low
    prices over a given window of time.

    Parameters:
        highs (list[float]): A list of daily highs.
        lows (list[float]): A list of daily lows.
        window (int): The number of days to use for the calculation.
                      Defaults to 20.

    Returns:
        dict[str, float]: A dictionary containing the upper and lower
                          channels.
    """
    if len(highs) < window or len(lows) < window:
        raise ValueError("Not enough data for Donchian Channels.")
    return {
        "upper_channel": round(max(highs[-window:]), 4),  # type: float
        "lower_channel": round(min(lows[-window:]), 4),  # type: float
    }  # type: dict[str, float]


def analyze_volatility(
    symbol: str,  # Stock symbol.
    data: dict[str, Any]  # Must include 'close_prices', 'highs', and 'lows'.
) -> dict[str, Any]:  # Analysis results.
    """Applies volatility analysis to incoming stock data.

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

        result: dict[str, Any] = {
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
