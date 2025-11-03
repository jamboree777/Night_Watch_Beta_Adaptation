"""
Chart Generation Functions for Token Analysis Reports
Provides Altair and Plotly chart creation for various metrics
"""

import altair as alt
import pandas as pd
import plotly.graph_objects as go
from typing import Dict, Optional


def create_grade_chart(df: pd.DataFrame, current_grade: str = 'N/A') -> alt.Chart:
    """
    Create 30-day grade history chart with moving averages and background zones

    Args:
        df: DataFrame with columns ['timestamp', 'grade', 'grade_numeric']
        current_grade: Current letter grade to highlight

    Returns:
        Altair layered chart
    """
    if df.empty:
        # Return empty chart with message
        return alt.Chart(pd.DataFrame({'x': [0], 'y': [0], 'text': ['No data available']})).mark_text(
            size=14, color='gray'
        ).encode(
            x='x:Q',
            y='y:Q',
            text='text:N'
        ).properties(width=700, height=300)

    # Calculate moving averages
    # 7 days @ 2hr intervals = 84 points
    # 14 days @ 2hr intervals = 168 points
    df['ma_7d'] = df['grade_numeric'].rolling(window=84, min_periods=1).mean()
    df['ma_14d'] = df['grade_numeric'].rolling(window=168, min_periods=1).mean()

    # Define grade zones for background
    grade_zones = pd.DataFrame({
        'grade_zone': ['F', 'D', 'C', 'B', 'A'],
        'y_min': [0, 1, 2, 3, 4],
        'y_max': [1, 2, 3, 4, 5],
        'color': ['#ff4444', '#ff8800', '#ffcc00', '#88cc00', '#00cc66']
    })

    # Base chart setup
    base = alt.Chart(df).encode(
        x=alt.X('timestamp:T', title='Date', axis=alt.Axis(format='%m/%d'))
    ).properties(
        width=700,
        height=300,
        title='30-Day Grade History'
    )

    # Background zones (grade levels)
    zones = alt.Chart(grade_zones).mark_rect(opacity=0.15).encode(
        y=alt.Y('y_min:Q', scale=alt.Scale(domain=[0, 5])),
        y2='y_max:Q',
        color=alt.Color('color:N', scale=None),
        tooltip=['grade_zone:N']
    )

    # Main grade line
    grade_line = base.mark_line(
        color='#3b82f6',
        strokeWidth=2.5
    ).encode(
        y=alt.Y('grade_numeric:Q', title='Grade', scale=alt.Scale(domain=[0, 5])),
        tooltip=[
            alt.Tooltip('timestamp:T', title='Time', format='%Y-%m-%d %H:%M'),
            alt.Tooltip('grade:N', title='Grade'),
            alt.Tooltip('grade_numeric:Q', title='Numeric', format='.2f')
        ]
    )

    # 7-day moving average
    ma_7d_line = base.mark_line(
        strokeDash=[5, 5],
        color='#06b6d4',
        strokeWidth=1.5
    ).encode(
        y=alt.Y('ma_7d:Q', title=''),
        tooltip=[
            alt.Tooltip('timestamp:T', title='Time', format='%Y-%m-%d'),
            alt.Tooltip('ma_7d:Q', title='7-Day Avg', format='.2f')
        ]
    )

    # 14-day moving average
    ma_14d_line = base.mark_line(
        strokeDash=[8, 4],
        color='#10b981',
        strokeWidth=1.5
    ).encode(
        y=alt.Y('ma_14d:Q', title=''),
        tooltip=[
            alt.Tooltip('timestamp:T', title='Time', format='%Y-%m-%d'),
            alt.Tooltip('ma_14d:Q', title='14-Day Avg', format='.2f')
        ]
    )

    # Current point highlight (last point)
    if not df.empty:
        last_point = df.iloc[-1:].copy()
        current_point = alt.Chart(last_point).mark_circle(
            size=120,
            color='#ef4444',
            opacity=0.8
        ).encode(
            x='timestamp:T',
            y='grade_numeric:Q',
            tooltip=[
                alt.Tooltip('timestamp:T', title='Current Time', format='%Y-%m-%d %H:%M'),
                alt.Tooltip('grade:N', title='Current Grade')
            ]
        )
    else:
        current_point = alt.Chart(pd.DataFrame()).mark_point()

    # Combine all layers
    chart = zones + grade_line + ma_7d_line + ma_14d_line + current_point

    return chart.configure_view(
        strokeWidth=0
    ).configure_axis(
        grid=True,
        gridColor='#e5e7eb',
        gridOpacity=0.5
    )


def create_spread_volume_chart(df: pd.DataFrame, spread_threshold: float = 2.0,
                                volume_threshold: float = 10000.0) -> go.Figure:
    """
    Create dual-axis chart: Volume (background bars) + Spread (foreground line)

    Args:
        df: DataFrame with columns ['timestamp', 'spread_pct', 'volume_24h']
        spread_threshold: Spread threshold for horizontal line
        volume_threshold: Volume threshold for horizontal line

    Returns:
        Plotly Figure with dual y-axes
    """
    if df.empty:
        fig = go.Figure()
        fig.add_annotation(
            text="No data available",
            xref="paper", yref="paper",
            x=0.5, y=0.5, showarrow=False,
            font=dict(size=14, color="gray")
        )
        fig.update_layout(height=350, title="Volume & Spread History")
        return fig

    fig = go.Figure()

    # Volume bars (background, secondary y-axis)
    fig.add_trace(go.Bar(
        x=df['timestamp'],
        y=df['volume_24h'],
        name='24h Volume',
        yaxis='y2',
        opacity=0.3,
        marker_color='#94a3b8',
        hovertemplate='<b>Volume</b><br>%{y:,.0f} USD<br>%{x}<extra></extra>'
    ))

    # Spread line (foreground, primary y-axis)
    fig.add_trace(go.Scatter(
        x=df['timestamp'],
        y=df['spread_pct'],
        name='Spread %',
        mode='lines',
        line=dict(color='#ef4444', width=2),
        hovertemplate='<b>Spread</b><br>%{y:.3f}%<br>%{x}<extra></extra>'
    ))

    # Spread threshold line (primary y-axis, left side)
    fig.add_hline(
        y=spread_threshold,
        line_dash="dash",
        line_color="#f97316",
        annotation_text=f"Spread Target: {spread_threshold}%",
        annotation_position="left",
        yref='y'
    )

    # Volume threshold line (secondary y-axis, right side)
    if not df.empty and df['volume_24h'].max() > 0:
        fig.add_hline(
            y=volume_threshold,
            line_dash="dot",
            line_color="#3b82f6",
            annotation_text=f"Volume Target: ${volume_threshold:,.0f}",
            annotation_position="right",
            yref='y2'
        )

    # Layout with dual y-axes
    fig.update_layout(
        title='Volume & Spread - 30 Day History',
        xaxis=dict(title='Date'),
        yaxis=dict(
            title='Spread (%)',
            side='left',
            showgrid=True,
            gridcolor='rgba(229,231,235,0.5)',
            rangemode='tozero'  # Ensure y-axis starts at 0
        ),
        yaxis2=dict(
            title='Volume (USD)',
            side='right',
            overlaying='y',
            showgrid=False,
            rangemode='tozero'  # Ensure y-axis starts at 0
        ),
        hovermode='x unified',
        height=350,
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1
        )
    )

    return fig


def create_depth_area_chart(df: pd.DataFrame, depth_threshold: float = 500.0) -> alt.Chart:
    """
    Create stacked area chart for depth levels (2%, 5%, 10%)

    Args:
        df: DataFrame with columns ['timestamp', 'depth_2pct', 'depth_5pct', 'depth_10pct']
        depth_threshold: 2% depth threshold for horizontal line

    Returns:
        Altair layered chart
    """
    if df.empty:
        return alt.Chart(pd.DataFrame({'x': [0], 'y': [0], 'text': ['No data available']})).mark_text(
            size=14, color='gray'
        ).encode(
            x='x:Q',
            y='y:Q',
            text='text:N'
        ).properties(width=700, height=300)

    # Melt dataframe for stacking
    df_melted = df.melt(
        id_vars=['timestamp'],
        value_vars=['depth_10pct', 'depth_5pct', 'depth_2pct'],
        var_name='depth_level',
        value_name='depth_usd'
    )

    # Rename for better legend labels
    df_melted['depth_level'] = df_melted['depth_level'].map({
        'depth_2pct': '2% Depth',
        'depth_5pct': '5% Depth',
        'depth_10pct': '10% Depth'
    })

    # Create area chart with contrasting colors for better visibility
    area = alt.Chart(df_melted).mark_area(opacity=0.7).encode(
        x=alt.X('timestamp:T', title='Date', axis=alt.Axis(format='%m/%d')),
        y=alt.Y('depth_usd:Q', title='Depth (USD)', stack=None),
        color=alt.Color(
            'depth_level:N',
            title='Depth Level',
            scale=alt.Scale(
                domain=['10% Depth', '5% Depth', '2% Depth'],
                range=['#10b981', '#f59e0b', '#3b82f6']  # Green-Orange-Blue for contrast
            )
        ),
        tooltip=[
            alt.Tooltip('timestamp:T', title='Time', format='%Y-%m-%d %H:%M'),
            alt.Tooltip('depth_level:N', title='Level'),
            alt.Tooltip('depth_usd:Q', title='Depth', format='$,.0f')
        ]
    ).properties(
        width=700,
        height=300,
        title='Depth Levels - 30 Day History'
    )

    # Threshold line
    threshold_df = pd.DataFrame({
        'y': [depth_threshold],
        'label': [f'2% Target: ${depth_threshold:,.0f}']
    })

    threshold = alt.Chart(threshold_df).mark_rule(
        strokeDash=[5, 5],
        color='#ef4444',
        strokeWidth=2
    ).encode(
        y='y:Q',
        tooltip=['label:N']
    )

    return (area + threshold).configure_view(
        strokeWidth=0
    ).configure_axis(
        grid=True,
        gridColor='#e5e7eb',
        gridOpacity=0.5
    )


def create_summary_box_html(grade: str, scores: Dict, exchange: str, symbol: str) -> str:
    """
    Create HTML for top summary box with 5 scores

    Args:
        grade: Letter grade (A+, A, B+, etc.)
        scores: Dictionary with depth_score, spread_score, volume_score, deposit_score
                Each is a tuple of (score, violation_rate)
        exchange: Exchange name
        symbol: Token symbol

    Returns:
        HTML string for summary box
    """
    # Extract score values
    depth_score, depth_violation = scores.get('depth_score', (0, 0))
    spread_score, spread_violation = scores.get('spread_score', (0, 0))
    volume_score, volume_violation = scores.get('volume_score', (0, 0))
    deposit_score, deposit_violation = scores.get('deposit_score', (0, 0))

    # Determine grade color
    grade_colors = {
        'A': '#00cc66', 'A+': '#00cc66', 'A-': '#00cc66',
        'B': '#88cc00', 'B+': '#88cc00', 'B-': '#88cc00',
        'C': '#ffcc00', 'C+': '#ffcc00', 'C-': '#ffcc00',
        'D': '#ff8800', 'D+': '#ff8800', 'D-': '#ff8800',
        'F': '#ff4444'
    }
    grade_color = grade_colors.get(grade, '#999')

    # Score color function
    def score_color(score: int) -> str:
        if score >= 90:
            return '#00cc66'
        elif score >= 70:
            return '#88cc00'
        elif score >= 50:
            return '#ffcc00'
        else:
            return '#ff4444'

    # Format deposit display
    if deposit_score > 0:
        deposit_display = str(deposit_score)
        deposit_color = score_color(deposit_score)
        deposit_subtitle = f'Violations: {deposit_violation:.1f}%'
    else:
        deposit_display = 'N/A'
        deposit_color = '#64748b'
        deposit_subtitle = 'No Data'

    html = f"""
    <div style='background: linear-gradient(135deg, #1e293b 0%, #334155 100%);
                padding: 20px; border-radius: 12px; margin-bottom: 20px;
                box-shadow: 0 4px 6px rgba(0,0,0,0.1);'>
        <h3 style='color: white; margin-top: 0; margin-bottom: 15px; font-size: 18px;'>
            📊 {exchange.upper()} {symbol} - Overall Assessment
        </h3>
        <div style='display: grid; grid-template-columns: repeat(5, 1fr); gap: 15px;'>

            <!-- Letter Grade -->
            <div style='background: rgba(255,255,255,0.1); padding: 15px; border-radius: 8px; text-align: center;'>
                <div style='font-size: 11px; color: #94a3b8; margin-bottom: 5px; font-weight: 600;'>GRADE</div>
                <div style='font-size: 36px; font-weight: bold; color: {grade_color}; line-height: 1;'>{grade}</div>
                <div style='font-size: 10px; color: #cbd5e1; margin-top: 5px;'>Letter Rating</div>
            </div>

            <!-- Depth Score -->
            <div style='background: rgba(255,255,255,0.1); padding: 15px; border-radius: 8px; text-align: center;'>
                <div style='font-size: 11px; color: #94a3b8; margin-bottom: 5px; font-weight: 600;'>DEPTH</div>
                <div style='font-size: 32px; font-weight: bold; color: {score_color(depth_score)}; line-height: 1;'>{depth_score}</div>
                <div style='font-size: 10px; color: #cbd5e1; margin-top: 5px;'>Violations: {depth_violation}%</div>
            </div>

            <!-- Spread Score -->
            <div style='background: rgba(255,255,255,0.1); padding: 15px; border-radius: 8px; text-align: center;'>
                <div style='font-size: 11px; color: #94a3b8; margin-bottom: 5px; font-weight: 600;'>SPREAD</div>
                <div style='font-size: 32px; font-weight: bold; color: {score_color(spread_score)}; line-height: 1;'>{spread_score}</div>
                <div style='font-size: 10px; color: #cbd5e1; margin-top: 5px;'>Violations: {spread_violation}%</div>
            </div>

            <!-- Volume Score -->
            <div style='background: rgba(255,255,255,0.1); padding: 15px; border-radius: 8px; text-align: center;'>
                <div style='font-size: 11px; color: #94a3b8; margin-bottom: 5px; font-weight: 600;'>VOLUME</div>
                <div style='font-size: 32px; font-weight: bold; color: {score_color(volume_score)}; line-height: 1;'>{volume_score}</div>
                <div style='font-size: 10px; color: #cbd5e1; margin-top: 5px;'>Violations: {volume_violation}%</div>
            </div>

            <!-- Deposit Market Cap Score (Phase 3 - ACTIVE) -->
            <div style='background: rgba(255,255,255,0.1); padding: 15px; border-radius: 8px; text-align: center;'>
                <div style='font-size: 11px; color: #94a3b8; margin-bottom: 5px; font-weight: 600;'>DEPOSIT</div>
                <div style='font-size: 32px; font-weight: bold; color: {deposit_color}; line-height: 1;'>{deposit_display}</div>
                <div style='font-size: 10px; color: #cbd5e1; margin-top: 5px;'>{deposit_subtitle}</div>
            </div>

        </div>
    </div>
    """

    return html


def create_basic_info_html(token_data: Dict, exchange: str, symbol: str) -> str:
    """
    Create HTML for basic token information section

    Args:
        token_data: Token data from tokens_unified.json
        exchange: Exchange name
        symbol: Token symbol

    Returns:
        HTML string for basic info section
    """
    current_snapshot = token_data.get('current_snapshot', {})
    scan_aggregate = token_data.get('scan_aggregate', {})

    # Extract available data
    last_price = current_snapshot.get('last_price') or scan_aggregate.get('avg_last_price', 'N/A')
    if isinstance(last_price, (int, float)):
        last_price = f"${last_price:,.6f}".rstrip('0').rstrip('.')

    tick_size = current_snapshot.get('tick_size', 'N/A')
    if isinstance(tick_size, (int, float)):
        tick_size = f"{tick_size:.8f}".rstrip('0').rstrip('.')

    # Placeholder for Phase 3 data
    contract_address = token_data.get('contract_address', 'Coming in Phase 3')
    chain = token_data.get('chain', 'Coming in Phase 3')
    listing_date = token_data.get('listing_date', 'Coming in Phase 3')
    total_supply = token_data.get('total_supply', 'Coming in Phase 3')

    html = f"""
    <div style='background: #f8fafc; padding: 15px; border-radius: 8px; border-left: 4px solid #3b82f6;'>
        <div style='display: grid; grid-template-columns: repeat(3, 1fr); gap: 15px;'>

            <div>
                <div style='font-size: 11px; color: #64748b; margin-bottom: 4px; font-weight: 600;'>Exchange</div>
                <div style='font-size: 14px; color: #1e293b; font-weight: 500;'>{exchange.upper()}</div>
            </div>

            <div>
                <div style='font-size: 11px; color: #64748b; margin-bottom: 4px; font-weight: 600;'>Symbol</div>
                <div style='font-size: 14px; color: #1e293b; font-weight: 500;'>{symbol}</div>
            </div>

            <div>
                <div style='font-size: 11px; color: #64748b; margin-bottom: 4px; font-weight: 600;'>Chain</div>
                <div style='font-size: 14px; color: #64748b; font-style: italic;'>{chain}</div>
            </div>

            <div>
                <div style='font-size: 11px; color: #64748b; margin-bottom: 4px; font-weight: 600;'>Current Price</div>
                <div style='font-size: 14px; color: #1e293b; font-weight: 500;'>{last_price}</div>
            </div>

            <div>
                <div style='font-size: 11px; color: #64748b; margin-bottom: 4px; font-weight: 600;'>Tick Size</div>
                <div style='font-size: 14px; color: #1e293b; font-weight: 500;'>{tick_size}</div>
            </div>

            <div>
                <div style='font-size: 11px; color: #64748b; margin-bottom: 4px; font-weight: 600;'>Listing Date</div>
                <div style='font-size: 14px; color: #64748b; font-style: italic;'>{listing_date}</div>
            </div>

        </div>
        <div style='margin-top: 10px; padding-top: 10px; border-top: 1px solid #e2e8f0;'>
            <div style='font-size: 11px; color: #64748b; margin-bottom: 4px; font-weight: 600;'>Contract Address</div>
            <div style='font-size: 12px; color: #64748b; font-style: italic; font-family: monospace;'>{contract_address}</div>
        </div>
    </div>
    """

    return html


def create_deposit_flow_chart(df: pd.DataFrame, target_balance: Optional[float] = None) -> go.Figure:
    """
    Create dual-axis chart: Deposit Balance (line) + Market Cap (area)
    Shows exchange wallet deposit tracking with movement alerts

    Args:
        df: DataFrame with columns ['timestamp', 'balance', 'market_cap_usd', 'movement_pct', 'movement_detected']
        target_balance: Optional target deposit balance for threshold line

    Returns:
        Plotly Figure with dual y-axes and movement alerts
    """
    if df.empty:
        fig = go.Figure()
        fig.add_annotation(
            text="No deposit data available. Configure on-chain tracking in Phase 3 settings.",
            xref="paper", yref="paper",
            x=0.5, y=0.5, showarrow=False,
            font=dict(size=14, color="gray")
        )
        fig.update_layout(height=350, title="Exchange Deposit & Market Cap History")
        return fig

    fig = go.Figure()

    # Market cap (area, secondary y-axis, background)
    fig.add_trace(go.Scatter(
        x=df['timestamp'],
        y=df['market_cap_usd'],
        name='Market Cap',
        mode='lines',
        fill='tozeroy',
        fillcolor='rgba(34, 197, 94, 0.15)',
        line=dict(color='#22c55e', width=1),
        yaxis='y2',
        hovertemplate='<b>Market Cap</b><br>$%{y:,.0f}<br>%{x}<extra></extra>'
    ))

    # Deposit balance (line, primary y-axis, foreground)
    fig.add_trace(go.Scatter(
        x=df['timestamp'],
        y=df['balance'],
        name='Deposit Balance',
        mode='lines+markers',
        line=dict(color='#3b82f6', width=2.5),
        marker=dict(size=4),
        hovertemplate='<b>Balance</b><br>%{y:,.0f} tokens<br>%{x}<extra></extra>'
    ))

    # Add movement alerts (red markers for >0.1% movements)
    if 'movement_detected' in df.columns:
        movement_df = df[df['movement_detected'] == True]
        if not movement_df.empty:
            fig.add_trace(go.Scatter(
                x=movement_df['timestamp'],
                y=movement_df['balance'],
                name='Large Movement (>0.1%)',
                mode='markers',
                marker=dict(
                    size=12,
                    color='#ef4444',
                    symbol='diamond',
                    line=dict(color='white', width=2)
                ),
                hovertemplate='<b>⚠️ Large Movement</b><br>%{y:,.0f} tokens<br>Change: ' +
                             movement_df['movement_pct'].apply(lambda x: f'{x:.2f}%').values +
                             '<br>%{x}<extra></extra>',
                showlegend=True
            ))

    # Target balance line (if provided)
    if target_balance and target_balance > 0:
        fig.add_hline(
            y=target_balance,
            line_dash="dash",
            line_color="#f97316",
            line_width=2,
            annotation_text=f"Target: {target_balance:,.0f}",
            annotation_position="left",
            annotation=dict(font=dict(size=11, color="#f97316")),
            yref='y'
        )

    # Layout with dual y-axes
    fig.update_layout(
        title='Exchange Deposit Balance & Market Cap - 30 Day History',
        xaxis=dict(
            title='Date',
            showgrid=True,
            gridcolor='rgba(229,231,235,0.3)'
        ),
        yaxis=dict(
            title='Deposit Balance (tokens)',
            side='left',
            showgrid=True,
            gridcolor='rgba(229,231,235,0.5)',
            rangemode='tozero'
        ),
        yaxis2=dict(
            title='Market Cap (USD)',
            side='right',
            overlaying='y',
            showgrid=False,
            rangemode='tozero'
        ),
        hovermode='x unified',
        height=350,
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1,
            bgcolor='rgba(255,255,255,0.8)'
        ),
        plot_bgcolor='rgba(248, 250, 252, 0.5)'
    )

    return fig
