def generate_strategy(sentiment_score: float, price_trends: list[dict], your_price: float) -> list[dict]:
    """
    Agentic rule-based decision engine combining ML outputs.
    Returns prioritized action recommendations.
    """
    actions = []

    # Rule 1: Negative sentiment + competitor price drop = urgent action
    falling_competitors = [p for p in price_trends if p['trend'] == 'Falling']
    if sentiment_score < -0.2 and falling_competitors:
        actions.append({
            'priority': 'CRITICAL',
            'icon': '🚨',
            'action': 'Immediate Price & Quality Review',
            'reason': f"Negative reviews (score: {sentiment_score}) + {len(falling_competitors)} competitor(s) dropping prices.",
            'suggestion': 'Reduce price by 5-10% AND address top complaints in reviews.'
        })

    # Rule 2: Negative sentiment only
    elif sentiment_score < -0.2:
        actions.append({
            'priority': 'HIGH',
            'icon': '⚠️',
            'action': 'Address Product Quality Issues',
            'reason': f"Sentiment score is {sentiment_score} — customers are unhappy.",
            'suggestion': 'Analyze negative reviews for recurring complaints and fix them.'
        })

    # Rule 3: Competitor price rising = opportunity
    rising_competitors = [p for p in price_trends if p['trend'] == 'Rising']
    if rising_competitors and sentiment_score >= 0:
        actions.append({
            'priority': 'OPPORTUNITY',
            'icon': '💰',
            'action': 'Consider Price Increase',
            'reason': f"{len(rising_competitors)} competitor(s) raising prices with your positive reviews.",
            'suggestion': f"You can increase price by 3-7%. Current: ${your_price}"
        })

    # Rule 4: Positive sentiment + stable market
    if sentiment_score > 0.3 and not falling_competitors:
        actions.append({
            'priority': 'GROWTH',
            'icon': '🚀',
            'action': 'Scale Marketing',
            'reason': 'Strong positive sentiment and stable competitive landscape.',
            'suggestion': 'Invest in ads and promotions to capture more market share.'
        })

    # Rule 5: Competitor significantly cheaper
    cheaper = [p for p in price_trends if p['current_price'] < your_price * 0.85]
    if cheaper:
        actions.append({
            'priority': 'HIGH',
            'icon': '📉',
            'action': 'Competitive Pricing Alert',
            'reason': f"{len(cheaper)} competitor(s) priced 15%+ below you.",
            'suggestion': 'Review your pricing strategy or highlight unique value proposition.'
        })

    if not actions:
        actions.append({
            'priority': 'STABLE',
            'icon': '✅',
            'action': 'Market Position is Stable',
            'reason': 'No critical signals detected.',
            'suggestion': 'Continue monitoring. Consider expanding product range.'
        })

    return actions
