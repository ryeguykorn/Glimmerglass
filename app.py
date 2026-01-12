"""
Iron Condor Backtester v2.0
============================

High-performance options strategy backtester with rule-based entries and exits.

Author: Refactored from streamlit_app.py
Date: 2026-01-12
"""

import streamlit as st
import pandas as pd
from datetime import datetime

# Core imports
from core.io import (
    load_csv_data,
    parse_blackout_dates,
    validate_dataframe,
    clean_dataframe,
    compute_file_hash,
)
from core.resample import resample_data, get_bb_window
from core.backtest import run_backtest
from core.metrics import calculate_monthly_breakdown

# UI imports
from ui.layout import (
    apply_custom_theme,
    render_summary_cards,
    render_sidebar,
    render_validation_status,
)
from ui.charts import (
    create_equity_chart,
    create_drawdown_chart,
    create_price_chart,
    create_pnl_distribution,
)
from ui.exports import (
    export_trades_csv,
    export_equity_csv,
    export_rejected_csv,
    export_run_config_json,
)

# Config
from config import (
    APP_TITLE,
    APP_ICON,
    TIMEFRAME_OPTIONS,
    DEFAULT_HV_MIN,
    DEFAULT_HV_MAX,
    DEFAULT_ADX_EXIT,
    DEFAULT_VWAP_K,
    DEFAULT_TREND_METHOD,
    DEFAULT_BIAS_STRENGTH,
    DEFAULT_WING_EXT_PCT,
    DEFAULT_DAYS_BEFORE,
    DEFAULT_DAYS_AFTER,
    MAX_TABLE_ROWS,
)

# Page config
st.set_page_config(
    page_title=APP_TITLE,
    page_icon=APP_ICON,
    layout="wide",
    initial_sidebar_state="expanded"
)

# Apply custom theme
apply_custom_theme()

# Initialize session state
if "backtest_result" not in st.session_state:
    st.session_state.backtest_result = None

if "data_hash" not in st.session_state:
    st.session_state.data_hash = None

# Header
st.markdown(f"# {APP_ICON} {APP_TITLE}")
st.markdown("---")

# Main tabs
tab_database, tab_data, tab_params, tab_results, tab_trades, tab_rejections, tab_diagnostics = st.tabs([
    "💾 Database",
    "📊 Data",
    "⚙️ Parameters",
    "📈 Results",
    "📋 Trades",
    "🚫 Rejections",
    "🔍 Diagnostics"
])

# ==================== TAB 0: DATABASE ====================
with tab_database:
    st.header("📦 Data Management (Tier 0)")
    
    # Import database modules
    try:
        from db.schema import get_connection, get_datasets, init_database
        from db.ingest import ingest_dataframe
        from db.query import query_all_symbols, query_time_series
        
        # Initialize database if needed
        try:
            conn = get_connection()
            conn.close()
        except Exception as e:
            conn = get_connection()
            init_database(conn)
            conn.close()
            st.info("🔧 Database initialized")
        
        # Upload section
        st.subheader("📤 Upload New Data")
        
        col1, col2, col3 = st.columns([2, 1, 1])
        
        with col1:
            upload_file = st.file_uploader(
                "Upload CSV File",
                type=["csv"],
                help="CSV must have: timestamp, open, high, low, close, volume",
                key="db_upload"
            )
        
        with col2:
            symbol = st.text_input("Symbol", value="SPY", help="Ticker symbol (e.g., SPY, QQQ)")
        
        with col3:
            timeframe = st.selectbox("Timeframe", ["1min", "5min", "15min", "1h", "1d"], index=0)
        
        if upload_file and symbol:
            if st.button("🚀 Ingest to Database", type="primary"):
                with st.spinner("Processing..."):
                    try:
                        # Load CSV
                        df = pd.read_csv(upload_file)
                        
                        # Validate required columns
                        required = ["timestamp", "open", "high", "low", "close", "volume"]
                        missing = [col for col in required if col not in df.columns]
                        
                        if missing:
                            st.error(f"❌ Missing required columns: {', '.join(missing)}")
                        else:
                            # Parse timestamp
                            df["timestamp"] = pd.to_datetime(df["timestamp"])
                            
                            # Show preview
                            st.write(f"📊 Preview ({len(df):,} rows):")
                            st.dataframe(df.head(10), use_container_width=True)
                            
                            # Ingest
                            parquet_path, dataset_id = ingest_dataframe(
                                df=df,
                                symbol=symbol.upper(),
                                timeframe=timeframe,
                                asset_type="equity",
                                vendor="streamlit_upload"
                            )
                            
                            st.success(f"✅ Data ingested successfully!")
                            st.info(f"Dataset ID: {dataset_id}")
                            st.caption(f"Stored at: {parquet_path}")
                            
                            # Refresh the page data
                            st.rerun()
                            
                    except Exception as e:
                        st.error(f"❌ Error: {str(e)}")
                        st.exception(e)
        
        st.markdown("---")
        
        # Show available datasets
        st.subheader("📊 Available Datasets")
        
        df_symbols = query_all_symbols()
        
        if df_symbols.empty:
            st.info("No datasets yet. Upload data above to get started.")
        else:
            st.dataframe(
                df_symbols,
                use_container_width=True,
                column_config={
                    "symbol": st.column_config.TextColumn("Symbol", width="small"),
                    "asset_type": st.column_config.TextColumn("Type", width="small"),
                    "dataset_count": st.column_config.NumberColumn("Datasets", width="small"),
                    "timeframe_count": st.column_config.NumberColumn("Timeframes", width="small"),
                    "earliest_date": st.column_config.DateColumn("Start Date", width="medium"),
                    "latest_date": st.column_config.DateColumn("End Date", width="medium"),
                    "total_rows": st.column_config.NumberColumn("Rows", format="%,d"),
                    "total_size_mb": st.column_config.NumberColumn("Size (MB)", format="%.2f"),
                }
            )
            
            # Load data section
            st.markdown("---")
            st.subheader("🔍 Load Data for Backtesting")
            
            col1, col2, col3 = st.columns(3)
            
            with col1:
                available_symbols = df_symbols["symbol"].tolist()
                selected_symbol = st.selectbox("Select Symbol", available_symbols, key="load_symbol")
            
            with col2:
                # Get timeframes for selected symbol
                conn = get_connection()
                datasets = get_datasets(conn, symbol=selected_symbol)
                conn.close()
                
                available_timeframes = list(set(ds["timeframe"] for ds in datasets))
                selected_timeframe = st.selectbox("Select Timeframe", available_timeframes, key="load_tf")
            
            with col3:
                st.write("")  # Spacing
                st.write("")
                if st.button("📥 Load Dataset", type="secondary"):
                    with st.spinner("Loading from database..."):
                        try:
                            df_loaded = query_time_series(
                                symbol=selected_symbol,
                                timeframe=selected_timeframe
                            )
                            
                            st.success(f"✅ Loaded {len(df_loaded):,} rows")
                            st.dataframe(df_loaded.head(20), use_container_width=True)
                            
                            # Store in session state for backtesting
                            st.session_state.df_raw = df_loaded
                            st.info("💡 Data loaded! Go to the 'Data' tab to continue with backtesting.")
                            
                        except Exception as e:
                            st.error(f"❌ Error loading data: {str(e)}")
            
            # Delete dataset section
            with st.expander("⚠️ Delete Dataset"):
                st.warning("This will remove the dataset from the database. The Parquet file will remain.")
                
                col1, col2 = st.columns([2, 1])
                
                with col1:
                    conn = get_connection()
                    all_datasets = get_datasets(conn)
                    conn.close()
                    
                    if all_datasets:
                        dataset_options = [
                            f"ID {ds['dataset_id']}: {ds['symbol']} @ {ds['timeframe']} ({ds['start_date']} to {ds['end_date']})"
                            for ds in all_datasets
                        ]
                        selected_to_delete = st.selectbox("Select dataset to delete", dataset_options)
                    else:
                        st.info("No datasets to delete")
                        selected_to_delete = None
                
                with col2:
                    st.write("")
                    st.write("")
                    if selected_to_delete and st.button("🗑️ Delete", type="primary"):
                        # Extract dataset_id from selection
                        dataset_id = int(selected_to_delete.split(":")[0].replace("ID ", ""))
                        
                        try:
                            conn = get_connection()
                            conn.execute("DELETE FROM datasets WHERE dataset_id = ?", (dataset_id,))
                            conn.commit()
                            conn.close()
                            
                            st.success(f"✅ Dataset {dataset_id} deleted")
                            st.rerun()
                        except Exception as e:
                            st.error(f"❌ Error: {str(e)}")
    
    except ImportError:
        st.error("❌ Database modules not found. Make sure Tier 0 is set up correctly.")
        st.code("pip install duckdb pyarrow", language="bash")
    except Exception as e:
        st.error(f"❌ Error: {str(e)}")
        st.exception(e)

# ==================== TAB 1: DATA ====================
with tab_data:
    st.header("Data Upload & Validation")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("OHLCV + VWAP Data")
        uploaded_csv = st.file_uploader(
            "Upload CSV File",
            type=["csv"],
            help="CSV with columns: timestamp, open, high, low, close, vwap"
        )
        
        if uploaded_csv:
            # Compute file hash for caching
            file_hash = compute_file_hash(uploaded_csv)
            
            # Load data
            try:
                df_raw = load_csv_data(uploaded_csv, file_hash)
                st.success(f"✅ Loaded {len(df_raw):,} rows")
                
                # Validate
                validation = validate_dataframe(df_raw)
                render_validation_status(validation)
                
                if validation.is_valid:
                    # Show preview
                    with st.expander("📋 Data Preview"):
                        st.dataframe(df_raw.head(50), use_container_width=True)
                    
                    # Store in session
                    st.session_state.df_raw = df_raw
                    st.session_state.validation = validation
                    
            except Exception as e:
                st.error(f"❌ Error loading CSV: {str(e)}")
    
    with col2:
        st.subheader("Blackout Dates")
        uploaded_blackout = st.file_uploader(
            "Upload Blackout Dates (TXT)",
            type=["txt"],
            help="One date per line (YYYY-MM-DD). Lines with '#' are ignored."
        )
        
        if uploaded_blackout:
            file_hash = compute_file_hash(uploaded_blackout)
            blackout_dates = parse_blackout_dates(uploaded_blackout, file_hash)
            
            st.success(f"✅ Loaded {len(blackout_dates)} blackout dates")
            
            if blackout_dates:
                with st.expander("📅 Blackout Dates"):
                    for date in blackout_dates[:20]:  # Show first 20
                        st.text(date.strftime("%Y-%m-%d"))
                    if len(blackout_dates) > 20:
                        st.caption(f"... and {len(blackout_dates) - 20} more")
            
            # Store in session
            st.session_state.blackout_dates = blackout_dates
        else:
            st.session_state.blackout_dates = []

# ==================== TAB 2: PARAMETERS ====================
with tab_params:
    st.header("Backtest Configuration")
    
    # Check if data is loaded
    if "df_raw" not in st.session_state:
        st.info("👈 Please upload data in the Data tab first")
        st.stop()
    
    # Timeframe selection
    st.subheader("Timeframe")
    timeframe = st.selectbox(
        "Resample to:",
        options=TIMEFRAME_OPTIONS,
        index=0,
        help="Data will be resampled to this frequency"
    )
    
    st.markdown("---")
    
    # Parameters in columns
    col_left, col_right = st.columns(2)
    
    with col_left:
        with st.expander("📊 Entry Filters", expanded=True):
            hv_min = st.number_input(
                "Min Historical Volatility (%)",
                value=DEFAULT_HV_MIN,
                min_value=0.0,
                max_value=200.0,
                step=1.0,
                help="Minimum annualized volatility for entry"
            )
            
            hv_max = st.number_input(
                "Max Historical Volatility (%)",
                value=DEFAULT_HV_MAX,
                min_value=0.0,
                max_value=200.0,
                step=1.0,
                help="Maximum annualized volatility for entry"
            )
        
        with st.expander("🚪 Exit Rules", expanded=True):
            adx_exit = st.number_input(
                "ADX Exit Threshold",
                value=DEFAULT_ADX_EXIT,
                min_value=10,
                max_value=100,
                step=5,
                help="Exit when ADX rises above this level (trend emerging)"
            )
            
            vwap_k = st.number_input(
                "VWAP Exit Distance (k)",
                value=DEFAULT_VWAP_K,
                min_value=0.0,
                max_value=5.0,
                step=0.1,
                help="Multiple of BB half-width for VWAP exit trigger"
            )
    
    with col_right:
        with st.expander("📈 Trend Bias", expanded=True):
            use_bias = st.checkbox(
                "Enable Trend Bias",
                value=False,
                help="Adjust strikes based on detected trend direction"
            )
            
            trend_method = st.selectbox(
                "Trend Detection Method",
                options=["VWAP Slope", "VWAP vs SMA20", "ADX + DI"],
                index=0,
                help="Method for determining trend direction"
            )
            
            bias_strength = st.number_input(
                "Bias Strength ($)",
                value=DEFAULT_BIAS_STRENGTH,
                min_value=0.0,
                max_value=20.0,
                step=0.5,
                disabled=not use_bias,
                help="Dollar amount to shift strikes in trend direction"
            )
            
            wing_ext_pct = st.number_input(
                "Wing Extension (%)",
                value=DEFAULT_WING_EXT_PCT,
                min_value=0.0,
                max_value=100.0,
                step=5.0,
                help="Percentage to extend wings in special regimes"
            )
        
        with st.expander("📅 Blackout Windows", expanded=True):
            days_before = st.number_input(
                "Days Before Event",
                value=DEFAULT_DAYS_BEFORE,
                min_value=0,
                max_value=30,
                step=1,
                help="Days before earnings/event to block entries"
            )
            
            days_after = st.number_input(
                "Days After Event",
                value=DEFAULT_DAYS_AFTER,
                min_value=0,
                max_value=30,
                step=1,
                help="Days after earnings/event to block entries"
            )
    
    st.markdown("---")
    
    # Run button
    run_button = st.button(
        "▶️ Run Backtest",
        type="primary",
        use_container_width=True
    )
    
    if run_button:
        # Clean and resample data
        with st.spinner("Preparing data..."):
            df_clean = clean_dataframe(st.session_state.df_raw)
            df_resampled = resample_data(df_clean, timeframe)
            bb_window = get_bb_window(timeframe)
            
            st.info(f"Resampled to {timeframe}: {len(df_resampled):,} bars")
        
        # Run backtest
        with st.spinner("Running backtest..."):
            progress_bar = st.progress(0)
            
            try:
                result = run_backtest(
                    df=df_resampled,
                    blackout_dates=st.session_state.blackout_dates,
                    hv_min=hv_min,
                    hv_max=hv_max,
                    adx_exit_threshold=adx_exit,
                    vwap_exit_k=vwap_k,
                    use_bias=use_bias,
                    bias_strength=bias_strength,
                    trend_method=trend_method,
                    wing_ext_pct=wing_ext_pct,
                    days_before=days_before,
                    days_after=days_after,
                    bb_window=bb_window,
                    progress_callback=progress_bar
                )
                
                # Store result
                st.session_state.backtest_result = result
                st.session_state.timeframe = timeframe
                st.session_state.params = {
                    "timeframe": timeframe,
                    "hv_min": hv_min,
                    "hv_max": hv_max,
                    "adx_exit": adx_exit,
                    "vwap_k": vwap_k,
                    "use_bias": use_bias,
                    "trend_method": trend_method,
                    "bias_strength": bias_strength,
                    "wing_ext_pct": wing_ext_pct,
                    "days_before": days_before,
                    "days_after": days_after,
                    "bb_window": bb_window,
                }
                
                st.success("✅ Backtest complete!")
                st.balloons()
                
            except Exception as e:
                st.error(f"❌ Backtest failed: {str(e)}")
            finally:
                progress_bar.empty()

# ==================== TAB 3: RESULTS ====================
with tab_results:
    st.header("Backtest Results")
    
    if st.session_state.backtest_result is None:
        st.info("👈 Run a backtest in the Parameters tab to see results")
    else:
        result = st.session_state.backtest_result
        
        # Summary cards
        render_summary_cards(result.summary)
        
        st.markdown("---")
        
        # Charts
        col1, col2 = st.columns(2)
        
        with col1:
            st.subheader("Equity Curve")
            fig_equity = create_equity_chart(result.equity_curve)
            st.plotly_chart(fig_equity, use_container_width=True)
        
        with col2:
            st.subheader("Drawdown")
            fig_dd = create_drawdown_chart(result.equity_curve)
            st.plotly_chart(fig_dd, use_container_width=True)
        
        # P&L Distribution
        st.subheader("P&L Distribution")
        fig_dist = create_pnl_distribution(result.trades)
        st.plotly_chart(fig_dist, use_container_width=True)
        
        # Detailed metrics
        with st.expander("📊 Detailed Statistics"):
            col1, col2, col3 = st.columns(3)
            
            with col1:
                st.metric("Profit Factor", f"{result.summary.get('profit_factor', 0):.2f}")
                st.metric("Avg Win", f"${result.summary.get('avg_win', 0):,.2f}")
                st.metric("Win Streak", f"{result.summary.get('win_streak', 0)}")
            
            with col2:
                st.metric("Reward/Risk", f"{result.summary.get('reward_risk_ratio', 0):.2f}")
                st.metric("Avg Loss", f"${result.summary.get('avg_loss', 0):,.2f}")
                st.metric("Loss Streak", f"{result.summary.get('loss_streak', 0)}")
            
            with col3:
                st.metric("Return on Risk", f"{result.summary.get('return_on_risk_pct', 0):.2f}%")
                st.metric("Avg Risk", f"${result.summary.get('avg_risk', 0):,.2f}")
                st.metric("Best Trade", f"${result.summary.get('best_trade', 0):,.2f}")

# ==================== TAB 4: TRADES ====================
with tab_trades:
    st.header("Trade History")
    
    if st.session_state.backtest_result is None:
        st.info("👈 Run a backtest first")
    else:
        result = st.session_state.backtest_result
        
        if result.trades.empty:
            st.warning("No trades executed")
        else:
            # Export button
            csv_trades = export_trades_csv(result.trades)
            st.download_button(
                "📥 Download Trades CSV",
                data=csv_trades,
                file_name=f"trades_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                mime="text/csv"
            )
            
            # Monthly breakdown
            with st.expander("📅 Monthly Breakdown"):
                monthly = calculate_monthly_breakdown(result.trades)
                st.dataframe(monthly, use_container_width=True)
            
            # Full trades table
            st.subheader("All Trades")
            trades_display = result.trades.copy()
            
            # Format for display
            for col in ["short_put", "long_put", "short_call", "long_call", "net_credit", "expiry_close", "pnl"]:
                if col in trades_display.columns:
                    trades_display[col] = trades_display[col].map(lambda x: f"{x:.2f}" if pd.notnull(x) else x)
            
            for col in ["entry_date", "expiry_date"]:
                if col in trades_display.columns:
                    trades_display[col] = pd.to_datetime(trades_display[col]).dt.strftime("%Y-%m-%d %H:%M")
            
            # Limit rows for performance
            if len(trades_display) > MAX_TABLE_ROWS:
                st.caption(f"Showing last {MAX_TABLE_ROWS} of {len(trades_display)} trades")
                trades_display = trades_display.tail(MAX_TABLE_ROWS)
            
            st.dataframe(trades_display, use_container_width=True, height=500)

# ==================== TAB 5: REJECTIONS ====================
with tab_rejections:
    st.header("Rejected Entries")
    
    if st.session_state.backtest_result is None:
        st.info("👈 Run a backtest first")
    else:
        result = st.session_state.backtest_result
        
        rejected_count = len(result.rejected)
        st.metric("Total Rejected", f"{rejected_count:,}")
        
        if result.rejected.empty:
            st.info("No rejected entries")
        else:
            # Export button
            csv_rejected = export_rejected_csv(result.rejected)
            st.download_button(
                "📥 Download Rejections CSV",
                data=csv_rejected,
                file_name=f"rejected_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                mime="text/csv"
            )
            
            # Reason breakdown
            st.subheader("Rejection Reasons")
            reasons_series = result.rejected["reasons"].str.split(", ").explode()
            reason_counts = reasons_series.value_counts()
            
            for reason, count in reason_counts.items():
                st.metric(reason, f"{count:,}", delta=f"{100*count/rejected_count:.1f}%")
            
            # Full table
            st.subheader("All Rejections")
            rejected_display = result.rejected.copy()
            
            if "date" in rejected_display.columns:
                rejected_display["date"] = pd.to_datetime(rejected_display["date"]).dt.strftime("%Y-%m-%d %H:%M")
            
            # Limit rows
            if len(rejected_display) > MAX_TABLE_ROWS:
                st.caption(f"Showing last {MAX_TABLE_ROWS} of {len(rejected_display)} rejections")
                rejected_display = rejected_display.tail(MAX_TABLE_ROWS)
            
            st.dataframe(rejected_display, use_container_width=True, height=500)

# ==================== TAB 6: DIAGNOSTICS ====================
with tab_diagnostics:
    st.header("Diagnostics & Charts")
    
    if st.session_state.backtest_result is None:
        st.info("👈 Run a backtest first")
    else:
        result = st.session_state.backtest_result
        
        # Price chart with indicators
        st.subheader("Price Chart with Indicators")
        show_trend = st.checkbox("Show Trend Markers", value=True)
        
        fig_price = create_price_chart(
            df=result.df_indicators,
            trades_df=result.trades,
            blackout_dates=st.session_state.blackout_dates,
            days_before=st.session_state.params.get("days_before", 7),
            days_after=st.session_state.params.get("days_after", 1),
            show_trend=show_trend
        )
        st.plotly_chart(fig_price, use_container_width=True, height=600)
        
        # Run configuration
        with st.expander("⚙️ Run Configuration"):
            data_info = {
                "rows": len(st.session_state.df_raw),
                "timeframe": st.session_state.timeframe,
                "resampled_rows": len(result.df_indicators),
            }
            
            if "validation" in st.session_state:
                val = st.session_state.validation
                if val.date_range:
                    data_info["start_date"] = val.date_range[0].strftime("%Y-%m-%d")
                    data_info["end_date"] = val.date_range[1].strftime("%Y-%m-%d")
            
            config_json = export_run_config_json(
                data_info=data_info,
                parameters=st.session_state.params,
                summary=result.summary
            )
            
            st.download_button(
                "📥 Download Config JSON",
                data=config_json,
                file_name=f"config_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
                mime="application/json"
            )
            
            st.code(config_json, language="json")

# Render sidebar
app_state = {
    "has_results": st.session_state.backtest_result is not None,
    "metrics": st.session_state.backtest_result.summary if st.session_state.backtest_result else {}
}
render_sidebar(app_state)
