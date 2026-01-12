"""Layout components and custom theme for Streamlit UI."""

import streamlit as st
from typing import Dict, Any
from config import THEME_COLORS


def apply_custom_theme():
    """
    Apply terminal-inspired finance theme with custom CSS.
    
    Features:
    - Dark background (#0E1117)
    - Matrix green primary color (#00FF41)
    - Monospace fonts for data
    - Subtle hover effects
    - Clean spacing
    """
    st.markdown(f"""
    <style>
        /* Global theme */
        :root {{
            --primary-color: {THEME_COLORS['primary']};
            --secondary-color: {THEME_COLORS['secondary']};
            --background-color: {THEME_COLORS['background']};
            --surface-color: {THEME_COLORS['surface']};
            --text-color: {THEME_COLORS['text']};
        }}
        
        /* Headers with mono font */
        h1, h2, h3 {{
            font-family: 'IBM Plex Mono', 'Courier New', monospace;
            font-weight: 700;
            letter-spacing: -0.5px;
        }}
        
        h1 {{
            color: {THEME_COLORS['primary']};
            font-size: 2.5rem;
        }}
        
        h2 {{
            color: {THEME_COLORS['secondary']};
            font-size: 1.8rem;
            margin-top: 2rem;
        }}
        
        h3 {{
            color: {THEME_COLORS['text']};
            font-size: 1.3rem;
            margin-top: 1.5rem;
        }}
        
        /* Metric cards */
        [data-testid="stMetricValue"] {{
            font-family: 'JetBrains Mono', 'Consolas', monospace;
            font-size: 1.5rem;
            font-weight: 600;
        }}
        
        [data-testid="stMetricLabel"] {{
            font-size: 0.85rem;
            color: {THEME_COLORS['text_dim']};
            text-transform: uppercase;
            letter-spacing: 0.5px;
        }}
        
        /* Positive deltas in green */
        [data-testid="stMetricDelta"] > div:first-child {{
            color: {THEME_COLORS['win']};
        }}
        
        /* Buttons */
        .stButton > button {{
            background-color: {THEME_COLORS['surface']};
            color: {THEME_COLORS['text']};
            border: 1px solid {THEME_COLORS['primary']};
            border-radius: 6px;
            padding: 0.5rem 1rem;
            font-family: 'Inter', sans-serif;
            font-weight: 500;
            transition: all 0.2s ease;
        }}
        
        .stButton > button:hover {{
            background-color: {THEME_COLORS['primary']};
            color: {THEME_COLORS['background']};
            border-color: {THEME_COLORS['primary']};
            box-shadow: 0 0 10px {THEME_COLORS['primary']}40;
        }}
        
        .stButton > button:disabled {{
            opacity: 0.5;
            cursor: not-allowed;
        }}
        
        /* Primary button variant */
        .stButton > button[kind="primary"] {{
            background-color: {THEME_COLORS['primary']};
            color: {THEME_COLORS['background']};
            font-weight: 600;
        }}
        
        /* Tabs */
        .stTabs [data-baseweb="tab-list"] {{
            gap: 8px;
            background-color: {THEME_COLORS['surface']};
            padding: 8px;
            border-radius: 8px;
        }}
        
        .stTabs [data-baseweb="tab"] {{
            background-color: transparent;
            border-radius: 6px;
            color: {THEME_COLORS['text_dim']};
            font-weight: 500;
            padding: 8px 16px;
        }}
        
        .stTabs [aria-selected="true"] {{
            background-color: {THEME_COLORS['background']};
            color: {THEME_COLORS['primary']};
            border: 1px solid {THEME_COLORS['primary']};
        }}
        
        /* Sidebar */
        [data-testid="stSidebar"] {{
            background-color: {THEME_COLORS['surface']};
            padding: 2rem 1rem;
        }}
        
        [data-testid="stSidebar"] h2 {{
            color: {THEME_COLORS['primary']};
            font-size: 1.2rem;
        }}
        
        /* Tables */
        .dataframe {{
            font-family: 'JetBrains Mono', monospace;
            font-size: 0.85rem;
        }}
        
        /* File uploader */
        [data-testid="stFileUploader"] {{
            background-color: {THEME_COLORS['surface']};
            border: 2px dashed {THEME_COLORS['text_dim']};
            border-radius: 8px;
            padding: 1.5rem;
        }}
        
        [data-testid="stFileUploader"]:hover {{
            border-color: {THEME_COLORS['primary']};
        }}
        
        /* Expander */
        .streamlit-expanderHeader {{
            background-color: {THEME_COLORS['surface']};
            border-radius: 6px;
            font-weight: 500;
        }}
        
        /* Info boxes */
        .stAlert {{
            background-color: {THEME_COLORS['surface']};
            border-left: 4px solid {THEME_COLORS['secondary']};
            border-radius: 4px;
        }}
        
        /* Code blocks */
        code {{
            background-color: {THEME_COLORS['surface']};
            color: {THEME_COLORS['primary']};
            padding: 2px 6px;
            border-radius: 4px;
            font-family: 'JetBrains Mono', monospace;
        }}
        
        /* Progress bar */
        .stProgress > div > div > div {{
            background-color: {THEME_COLORS['primary']};
        }}
        
        /* Tooltips */
        [data-testid="stTooltipIcon"] {{
            color: {THEME_COLORS['text_dim']};
        }}
        
        /* Dividers */
        hr {{
            border-color: {THEME_COLORS['text_dim']};
            opacity: 0.2;
        }}
    </style>
    """, unsafe_allow_html=True)


def render_summary_cards(metrics: Dict[str, Any]):
    """
    Render top-level summary metrics in a card layout.
    
    Shows 5 key metrics:
    - Total Return
    - Max Drawdown
    - Win Rate
    - Avg Trade P&L
    - Trades per Day
    
    Args:
        metrics: Dictionary of calculated metrics
    """
    st.markdown("### 📊 Performance Summary")
    
    col1, col2, col3, col4, col5 = st.columns(5)
    
    with col1:
        total_pnl = metrics.get("total_pnl", 0.0)
        delta = f"${total_pnl:+,.2f}"
        st.metric(
            label="Total Return",
            value=f"${total_pnl:,.2f}",
            delta=delta,
            delta_color="normal" if total_pnl >= 0 else "inverse"
        )
    
    with col2:
        max_dd = metrics.get("max_drawdown", 0.0)
        max_dd_pct = metrics.get("max_drawdown_pct", 0.0)
        st.metric(
            label="Max Drawdown",
            value=f"${max_dd:,.2f}",
            delta=f"{-abs(max_dd_pct):.2f}%",
            delta_color="inverse"
        )
    
    with col3:
        win_rate = metrics.get("win_rate", 0.0)
        wins = metrics.get("wins", 0)
        losses = metrics.get("losses", 0)
        st.metric(
            label="Win Rate",
            value=f"{win_rate:.1f}%",
            delta=f"{wins}W / {losses}L"
        )
    
    with col4:
        avg_pnl = metrics.get("avg_pnl", 0.0)
        st.metric(
            label="Avg Trade",
            value=f"${avg_pnl:,.2f}",
            delta=f"${avg_pnl:+,.2f}",
            delta_color="normal" if avg_pnl >= 0 else "inverse"
        )
    
    with col5:
        total_trades = metrics.get("trades", 0)
        # Rough estimate: assume 252 trading days per year
        trades_per_day = 0.0
        if "date_range_days" in metrics and metrics["date_range_days"] > 0:
            trades_per_day = total_trades / (metrics["date_range_days"] / 252) / 252
        st.metric(
            label="Total Trades",
            value=f"{total_trades}",
            delta=f"{trades_per_day:.2f}/day" if trades_per_day > 0 else None
        )


def render_sidebar(app_state: Dict[str, Any]):
    """
    Render sidebar with quick stats and controls.
    
    Args:
        app_state: Current application state
    """
    with st.sidebar:
        st.markdown("## ⚙️ Controls")
        
        # Clear cache button
        if st.button("🗑️ Clear Cache", use_container_width=True):
            st.cache_data.clear()
            st.success("Cache cleared!")
            st.rerun()
        
        st.markdown("---")
        
        # Quick stats if results available
        if app_state.get("has_results", False):
            st.markdown("## 📈 Quick Stats")
            
            metrics = app_state.get("metrics", {})
            
            st.metric("Total P&L", f"${metrics.get('total_pnl', 0):,.2f}")
            st.metric("Win Rate", f"{metrics.get('win_rate', 0):.1f}%")
            st.metric("Trades", f"{metrics.get('trades', 0)}")
            
            st.markdown("---")
        
        # About section
        st.markdown("## ℹ️ About")
        st.caption("""
        **Iron Condor Backtester v2.0**
        
        High-performance options strategy backtester
        with rule-based entries and exits.
        
        Built with Streamlit, NumPy, and Plotly.
        """)


def create_card(title: str, content: str, color: str = None):
    """
    Create a styled card component.
    
    Args:
        title: Card title
        content: Card content (can include HTML)
        color: Optional border color
    """
    border_color = color if color else THEME_COLORS['text_dim']
    
    st.markdown(f"""
    <div style="
        background-color: {THEME_COLORS['surface']};
        border-left: 4px solid {border_color};
        border-radius: 8px;
        padding: 1.5rem;
        margin: 1rem 0;
    ">
        <h4 style="margin: 0 0 0.5rem 0; color: {THEME_COLORS['text']};">
            {title}
        </h4>
        <div style="color: {THEME_COLORS['text_dim']};">
            {content}
        </div>
    </div>
    """, unsafe_allow_html=True)


def render_validation_status(validation_result):
    """
    Render data validation status with errors/warnings.
    
    Args:
        validation_result: ValidationResult object
    """
    if validation_result.is_valid:
        st.success(f"✅ Data validated: {validation_result}")
    else:
        st.error(f"❌ Validation failed: {validation_result}")
    
    if validation_result.errors:
        with st.expander("❌ Errors", expanded=True):
            for error in validation_result.errors:
                st.error(error)
    
    if validation_result.warnings:
        with st.expander("⚠️ Warnings"):
            for warning in validation_result.warnings:
                st.warning(warning)
