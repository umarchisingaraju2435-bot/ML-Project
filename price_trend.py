import numpy as np

def moving_average(prices: list[float], window: int = 3) -> list[float]:
    result = []
    for i in range(len(prices)):
        start = max(0, i - window + 1)
        result.append(round(np.mean(prices[start:i+1]), 2))
    return result

def analyze_price_trend(competitor_data: list[dict]) -> dict:
    """
    competitor_data: [{'name': str, 'prices': [float], 'dates': [str]}]
    """
    analysis = []
    for comp in competitor_data:
        prices = comp['prices']
        if len(prices) < 2:
            continue
        ma = moving_average(prices)
        change = round(prices[-1] - prices[0], 2)
        pct_change = round((change / prices[0]) * 100, 1) if prices[0] != 0 else 0
        trend = 'Rising' if change > 0 else ('Falling' if change < 0 else 'Stable')
        analysis.append({
            'name': comp['name'],
            'current_price': prices[-1],
            'initial_price': prices[0],
            'change': change,
            'pct_change': pct_change,
            'trend': trend,
            'moving_avg': ma,
            'dates': comp.get('dates', [])
        })
    return analysis
