"""
Chart Helper Functions for Night Watch
Separated to avoid circular imports between night_watch_board.py and simple_user_dashboard.py
"""

import json
from glob import glob
import os
from datetime import datetime, timezone, timedelta

try:
    import altair as alt
    import pandas as pd
    ALTAIR_AVAILABLE = True
except ImportError:
    ALTAIR_AVAILABLE = False


def get_token_history_14days(token_id: str, exchange: str, symbol: str, current_data: dict = None) -> dict:
    """
    Get 14-day history for a token from scan_history files + current snapshot
    Returns dict with grades, volumes, spreads, depths (2%, 5%, 10%) arrays
    
    Args:
        token_id: Token ID (exchange_symbol_usdt format)
        exchange: Exchange name
        symbol: Symbol (e.g., "BTC/USDT")
        current_data: Current snapshot data to append (optional)
    """
    history_dir = 'scan_history'
    if not os.path.exists(history_dir):
        return {'dates': [], 'grades': [], 'volumes': [], 'spreads': [], 'depths': [], 'depths_5': [], 'depths_10': []}
    
    # Get last 13 days of scan files (not 14, to make room for current)
    now = datetime.now(timezone.utc)
    history_data = {'dates': [], 'grades': [], 'volumes': [], 'spreads': [], 'depths': [], 'depths_5': [], 'depths_10': []}
    
    # Collect data from scan history files (13 days ago to yesterday)
    for days_ago in range(13, 0, -1):  # 13 days ago to 1 day ago
        target_date = now - timedelta(days=days_ago)
        date_str = target_date.strftime('%Y%m%d')
        
        # Check files for this date (all hours)
        date_files = glob(os.path.join(history_dir, f"{date_str}_*.json"))
        
        if date_files:
            # Use 3 scans per day (00h, 08h, 16h UTC)
            date_files.sort()
            
            # Filter for 00h, 08h, 16h files
            target_hours = ["00", "08", "16"]
            filtered_files = [f for f in date_files if any(f.endswith(f"_{h}.json") for h in target_hours)]
            
            for scan_file in filtered_files:
                try:
                    with open(scan_file, 'r', encoding='utf-8') as f:
                        scan_data = json.load(f)
                    
                    # Extract hour from filename (YYYYMMDD_HH.json)
                    filename = os.path.basename(scan_file)
                    hour_str = filename.split('_')[1].split('.')[0]  # Get HH
                    
                    # Find this token in the scan data
                    tokens = scan_data.get('tokens', [])
                    for token in tokens:
                        if token.get('exchange') == exchange and token.get('symbol') == symbol:
                            history_data['dates'].append(f"{target_date.strftime('%m/%d')} {hour_str}h")
                            history_data['grades'].append(token.get('grade', 'N/A'))
                            history_data['volumes'].append(token.get('quote_volume', 0))
                            history_data['spreads'].append(token.get('spread_pct', 0))
                            history_data['depths'].append(token.get('depth_2pct', 0))
                            history_data['depths_5'].append(token.get('depth_5pct', 0))
                            history_data['depths_10'].append(token.get('depth_10pct', 0))
                            break
                except Exception as e:
                    print(f"[WARN] Failed to read history file {scan_file}: {e}")
                    continue
    if current_data:
        history_data['dates'].append('Now')
        history_data['grades'].append(current_data.get('grade', 'N/A'))
        history_data['volumes'].append(current_data.get('avg_volume_24h', 0))
        history_data['spreads'].append(current_data.get('avg_spread_pct', 0))
        history_data['depths'].append(current_data.get('avg_depth_2pct', 0))
        history_data['depths_5'].append(current_data.get('avg_depth_5pct', 0))
        history_data['depths_10'].append(current_data.get('avg_depth_10pct', 0))
    
    return history_data


def generate_mini_chart_html(history_data: dict, chart_type: str = 'combined', inline: bool = False) -> str:
    """
    Generate HTML/CSS for mini trend charts
    chart_type: 'combined' (all 3 metrics) or 'separate' (3 individual charts)
    inline: if True, generates small inline chart for placement next to exchange badge
    """
    if not history_data or not history_data.get('dates'):
        return ""
    
    dates = history_data['dates']
    volumes = history_data.get('volumes', [])
    spreads = history_data['spreads']
    depths = history_data['depths']
    
    if len(dates) == 0:
        return ""
    
    # If only 1 data point, duplicate it to show a horizontal line
    if len(dates) == 1:
        dates = dates + dates
        volumes = volumes + volumes if volumes else [0, 0]
        spreads = spreads + spreads
        depths = depths + depths
    
    # Normalize values for chart display (0-85 scale to leave margin at top/bottom)
    def normalize(values, max_val=None):
        if not values or all(v <= 0 for v in values):
            return [0] * len(values)
        if max_val is None:
            max_val = max(values) if values else 1
        if max_val == 0:
            return [0] * len(values)
        # Scale to 85% to leave 15% margin (7.5% top + 7.5% bottom)
        return [min(85, max(0, (v / max_val) * 85)) for v in values]
    
    # Normalize each metric (filter out None values)
    valid_volumes = [v for v in volumes if v is not None and v > 0]
    valid_spreads = [s for s in spreads if s is not None and s > 0]
    valid_depths = [d for d in depths if d is not None and d > 0]

    norm_volumes = normalize([v if v is not None and v > 0 else 0 for v in volumes],
                            max_val=max(valid_volumes) if valid_volumes else 10000)
    norm_spreads = normalize([s if s is not None and s > 0 else 0 for s in spreads],
                            max_val=max(valid_spreads) if valid_spreads else 5)
    norm_depths = normalize([d if d is not None and d > 0 else 0 for d in depths],
                           max_val=max(valid_depths) if valid_depths else 2000)
    
    # Chart dimensions
    if inline:
        chart_width = 94  # 30% increase (72 * 1.3)
        chart_height = 28
    else:
        chart_width = 140
        chart_height = 50
    
    point_width = chart_width / max(len(dates) - 1, 1) if len(dates) > 1 else chart_width
    
    # Build SVG paths for each metric (with padding at top/bottom)
    def build_path(normalized_values):
        if not normalized_values:
            return ""
        points = []
        padding = 3  # 3px padding at top and bottom
        usable_height = chart_height - (2 * padding)
        for i, val in enumerate(normalized_values):
            x = i * point_width if len(normalized_values) > 1 else chart_width / 2
            y = padding + (usable_height - (val / 85 * usable_height))  # Scale from 85 to usable_height
            points.append(f"{x},{y}")
        return " ".join(points)
    
    volume_path = build_path(norm_volumes)
    spread_path = build_path(norm_spreads)
    depth_path = build_path(norm_depths)
    
    # For inline version, simpler design without thresholds
    if inline:
        chart_html = f"""<span class='mini-chart-inline' style='display:inline-block; width:{chart_width}px; height:{chart_height}px; vertical-align:middle; margin-left:3px; opacity:0.8;'>
<svg width="{chart_width}" height="{chart_height}" style='display:block;'>
<polyline points="{volume_path}" fill="none" stroke="#8b5cf6" stroke-width="3" opacity="0.9"/>
<polyline points="{spread_path}" fill="none" stroke="#f59e0b" stroke-width="2.4" opacity="0.85"/>
<polyline points="{depth_path}" fill="none" stroke="#3b82f6" stroke-width="2.4" opacity="0.85"/>
</svg>
</span>"""
    else:
        # Calculate threshold positions (0-85 scale to match normalized values)
        # For volume, use a percentage of max volume as threshold (no fixed threshold)
        # For spread, 2% threshold (거래소 기본 요구사항)
        # For depth, 500 USDT threshold
        spread_threshold_pct = 85 - ((2.0 / (max(spreads) if spreads and max(spreads) > 0 else 5)) * 85)  # 2% threshold (inverted)
        depth_threshold_pct = (500 / (max(depths) if depths and max(depths) > 0 else 2000)) * 85  # 500 USDT threshold

        # Generate threshold lines (only spread and depth, volume has no fixed threshold)
        padding = 3
        usable_height = chart_height - (2 * padding)
        spread_threshold_y = padding + (usable_height - (spread_threshold_pct / 85 * usable_height))
        depth_threshold_y = padding + (usable_height - (depth_threshold_pct / 85 * usable_height))
        
        chart_html = f"""<div class='mini-chart-container' style='position:absolute; right:70px; bottom:8px; width:{chart_width}px; height:{chart_height}px; opacity:0.5; z-index:1; pointer-events:none;'>
<svg width="{chart_width}" height="{chart_height}" style='display:block;'>
<line x1="0" y1="{spread_threshold_y}" x2="{chart_width}" y2="{spread_threshold_y}" stroke="#f59e0b" stroke-width="0.5" stroke-dasharray="2,2" opacity="0.5" class="threshold-spread"/>
<line x1="0" y1="{depth_threshold_y}" x2="{chart_width}" y2="{depth_threshold_y}" stroke="#3b82f6" stroke-width="0.5" stroke-dasharray="2,2" opacity="0.5" class="threshold-depth"/>
<polyline points="{volume_path}" fill="none" stroke="#8b5cf6" stroke-width="2" opacity="0.7" class="line-volume"/>
<polyline points="{spread_path}" fill="none" stroke="#f59e0b" stroke-width="2" opacity="0.7" class="line-spread"/>
<polyline points="{depth_path}" fill="none" stroke="#3b82f6" stroke-width="2" opacity="0.7" class="line-depth"/>
</svg>
</div>"""
    
    return chart_html


def create_spread_volume_chart(history_data: dict):
    """
    Create spread chart with volume background overlay using Altair
    Returns Altair chart object or None if Altair not available
    """
    if not ALTAIR_AVAILABLE:
        return None
    
    if not history_data or not history_data.get('dates'):
        return None
    
    # Prepare data
    df = pd.DataFrame({
        'Date': history_data['dates'],
        'Spread (%)': history_data['spreads'],
        'Volume ($)': history_data['volumes']
    })
    
    # Volume background (bar chart)
    volume_chart = alt.Chart(df).mark_bar(opacity=0.3, color='#8b5cf6').encode(
        x=alt.X('Date:N', title='Date', axis=alt.Axis(labelAngle=-45)),
        y=alt.Y('Volume ($):Q', title='Volume (USD)', axis=alt.Axis(format='~s')),
        tooltip=['Date:N', alt.Tooltip('Volume ($):Q', format=',.0f')]
    )
    
    # Spread line (overlay)
    spread_chart = alt.Chart(df).mark_line(color='#f59e0b', strokeWidth=3).encode(
        x=alt.X('Date:N'),
        y=alt.Y('Spread (%):Q', title='Spread (%)', scale=alt.Scale(zero=False)),
        tooltip=['Date:N', alt.Tooltip('Spread (%):Q', format='.2f')]
    ).properties(
        width=600,
        height=300
    )
    
    # Spread threshold line (1%)
    threshold_df = pd.DataFrame({'y': [1.0]})
    threshold_line = alt.Chart(threshold_df).mark_rule(color='red', strokeDash=[5, 5]).encode(
        y='y:Q'
    )
    
    # Combine charts (dual axis)
    chart = alt.layer(
        volume_chart,
        spread_chart + threshold_line
    ).resolve_scale(
        y='independent'
    ).properties(
        title='14-Day Spread & Volume Trend'
    )
    
    return chart


def create_grade_chart(history_data: dict):
    """
    Create grade trend chart using Altair
    Returns Altair chart object or None if Altair not available
    """
    if not ALTAIR_AVAILABLE:
        return None
    
    if not history_data or not history_data.get('dates'):
        return None
    
    # Grade to numeric mapping (5-point system)
    grade_map = {
        'A': 5.0,
        'A-': 4.67,
        'B+': 4.33,
        'B': 4.0,
        'B-': 3.67,
        'C+': 3.33,
        'C': 3.0,
        'C-': 2.67,
        'D+': 2.33,
        'D': 2.0,
        'F': 1.0
    }

    # Prepare data - filter out N/A grades
    valid_data = [(d, g) for d, g in zip(history_data['dates'], history_data['grades']) if g in grade_map]
    if not valid_data:
        return None

    dates, grades = zip(*valid_data)
    df = pd.DataFrame({
        'Date': dates,
        'Grade': grades,
        'Grade_Numeric': [grade_map[g] for g in grades]
    })
    
    # Grade color scale (5-point system)
    grade_colors = {
        'F': '#8B0000',
        'D': '#DC143C',
        'D+': '#FF4500',
        'C-': '#FF6347',
        'C': '#FF8C00',
        'C+': '#FFA500',
        'B-': '#FFB347',
        'B': '#FFD700',
        'B+': '#ADFF2F',
        'A-': '#7FFF00',
        'A': '#32CD32'
    }
    
    # Create chart
    chart = alt.Chart(df).mark_line(point=True, strokeWidth=3).encode(
        x=alt.X('Date:N', title='Date', axis=alt.Axis(labelAngle=-45)),
        y=alt.Y('Grade_Numeric:Q', title='Grade',
                scale=alt.Scale(domain=[1.0, 5.0]),
                axis=alt.Axis(
                    values=[1.0, 2.0, 2.33, 2.67, 3.0, 3.33, 3.67, 4.0, 4.33, 4.67, 5.0],
                    labelExpr="datum.value == 5.0 ? 'A' : datum.value == 4.67 ? 'A-' : datum.value == 4.33 ? 'B+' : datum.value == 4.0 ? 'B' : datum.value == 3.67 ? 'B-' : datum.value == 3.33 ? 'C+' : datum.value == 3.0 ? 'C' : datum.value == 2.67 ? 'C-' : datum.value == 2.33 ? 'D+' : datum.value == 2.0 ? 'D' : 'F'"
                )),
        color=alt.Color('Grade:N', scale=alt.Scale(domain=list(grade_colors.keys()), range=list(grade_colors.values())), legend=None),
        tooltip=['Date:N', 'Grade:N']
    ).properties(
        width=600,
        height=300,
        title='14-Day Grade Trend'
    )

    # Critical Zone line (F grade = 1.0)
    critical_line = alt.Chart(pd.DataFrame({'y': [1.0]})).mark_rule(
        color='red', strokeWidth=2
    ).encode(y='y:Q')

    # White Walkers Zone line (D grade = 2.0 - Main Board entry threshold)
    mainboard_line = alt.Chart(pd.DataFrame({'y': [2.0]})).mark_rule(
        color='orange', strokeDash=[5, 5], strokeWidth=2
    ).encode(y='y:Q')

    return chart + critical_line + mainboard_line


def create_depth_area_chart(history_data: dict):
    """
    Create depth area chart with 2%, 5%, 10% lines using Altair
    Returns Altair chart object or None if Altair not available
    """
    if not ALTAIR_AVAILABLE:
        return None
    
    if not history_data or not history_data.get('dates'):
        return None
    
    # Prepare data
    df = pd.DataFrame({
        'Date': history_data['dates'],
        'Depth 2%': history_data['depths'],
        'Depth 5%': history_data.get('depths_5', [0] * len(history_data['dates'])),
        'Depth 10%': history_data.get('depths_10', [0] * len(history_data['dates']))
    })
    
    # Melt data for multi-line chart
    df_melted = df.melt('Date', var_name='Depth Range', value_name='Depth (USD)')
    
    # Create chart
    chart = alt.Chart(df_melted).mark_line(point=True, strokeWidth=2).encode(
        x=alt.X('Date:N', title='Date', axis=alt.Axis(labelAngle=-45)),
        y=alt.Y('Depth (USD):Q', title='Depth (USD)', axis=alt.Axis(format='~s')),
        color=alt.Color('Depth Range:N', 
                       scale=alt.Scale(domain=['Depth 2%', 'Depth 5%', 'Depth 10%'],
                                     range=['#3b82f6', '#10b981', '#8b5cf6'])),
        tooltip=['Date:N', 'Depth Range:N', alt.Tooltip('Depth (USD):Q', format=',.0f')]
    ).properties(
        width=600,
        height=300,
        title='14-Day Depth Trend (2%, 5%, 10%)'
    )
    
    # Add 500 USD threshold line for 2% depth
    threshold_df = pd.DataFrame({'y': [500]})
    threshold_line = alt.Chart(threshold_df).mark_rule(color='red', strokeDash=[5, 5]).encode(
        y='y:Q'
    )
    
    return chart + threshold_line

