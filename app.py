import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime, timedelta
from ga4_client import GA4Client
from auth import GA4Auth
import os

# Page configuration
st.set_page_config(
    page_title="GA4 Traffic Comparison Dashboard",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for better alignment and professional look
st.markdown("""
    <style>
    .main {
        padding: 2rem;
    }
    .stMetric {
        background-color: #F5F7FA;
        padding: 1rem;
        border-radius: 0.5rem;
        border: 1px solid #E5E7EB;
    }
    h1 {
        font-weight: 600;
        margin-bottom: 2rem;
    }
    h2 {
        font-weight: 600;
        margin-top: 2rem;
        margin-bottom: 1.5rem;
    }
    h3 {
        font-weight: 500;
        margin-bottom: 1rem;
    }
    .block-container {
        padding-top: 2rem;
    }
    div[data-testid="stExpander"] {
        background-color: #FFFFFF;
        border: 1px solid #E5E7EB;
        border-radius: 0.5rem;
    }
    .auth-button {
        background-color: #0066CC;
        color: white;
        padding: 0.75rem 2rem;
        border-radius: 0.5rem;
        text-decoration: none;
        display: inline-block;
        font-weight: 500;
    }
    .auth-section {
        background-color: #F5F7FA;
        padding: 2rem;
        border-radius: 0.5rem;
        border: 1px solid #E5E7EB;
        margin: 2rem 0;
        text-align: center;
    }
    </style>
    """, unsafe_allow_html=True)


# Helper functions
def format_metric_value(value, format_type=None):
    """Format metric values based on type"""
    if format_type == "time":
        minutes = int(value // 60)
        seconds = int(value % 60)
        return f"{minutes}m {seconds}s"
    elif format_type == "percentage":
        return f"{value:.2f}%"
    else:
        return f"{value:,.0f}"


def calculate_percentage_change(organic_value, ai_value):
    """Calculate percentage change between organic and AI traffic"""
    if organic_value == 0:
        return 0
    return ((ai_value - organic_value) / organic_value) * 100


def create_comparison_chart(organic_df, ai_df, metric_column, title, y_axis_title):
    """Create a comparison line chart for trends"""
    fig = go.Figure()

    # Convert date strings to datetime objects for proper plotting
    organic_dates = pd.to_datetime(organic_df['date'])
    ai_dates = pd.to_datetime(ai_df['date'])

    # Add organic traffic line
    fig.add_trace(go.Scatter(
        x=organic_dates,
        y=organic_df[metric_column],
        name='Organic Traffic',
        mode='lines+markers',
        line=dict(color='#0066CC', width=3),
        marker=dict(size=7)
    ))

    # Add AI mode traffic line
    fig.add_trace(go.Scatter(
        x=ai_dates,
        y=ai_df[metric_column],
        name='AI Mode Traffic',
        mode='lines+markers',
        line=dict(color='#10B981', width=3),
        marker=dict(size=7)
    ))

    fig.update_layout(
        title={
            'text': title,
            'font': {'size': 16, 'color': '#262730'}
        },
        xaxis_title='Date',
        yaxis_title=y_axis_title,
        hovermode='x unified',
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1,
            bgcolor='rgba(255,255,255,0.8)',
            bordercolor='#E5E7EB',
            borderwidth=1
        ),
        height=400,
        plot_bgcolor='#FFFFFF',
        paper_bgcolor='#FFFFFF',
        font=dict(color='#262730'),
        xaxis=dict(
            showgrid=True,
            gridcolor='#F5F7FA',
            linecolor='#E5E7EB'
        ),
        yaxis=dict(
            showgrid=True,
            gridcolor='#F5F7FA',
            linecolor='#E5E7EB'
        )
    )

    return fig


# Initialize session state
if 'auth' not in st.session_state:
    st.session_state.auth = GA4Auth()

auth = st.session_state.auth

# Title and subtitle
st.title("GA4 Traffic Comparison Dashboard")
st.markdown("### Compare Organic Traffic with AI Mode Traffic Metrics")

# Authentication Section
if not auth.is_authenticated():
    # Check for auth code in query params (OAuth callback)
    query_params = st.query_params
    if 'code' in query_params:
        auth_code = query_params['code']
        with st.spinner("Authenticating..."):
            if auth.authenticate_with_code(auth_code):
                st.query_params.clear()
                st.rerun()
            else:
                st.error("Authentication failed. Please try again.")

    # Show sign in button
    st.markdown('<div class="auth-section">', unsafe_allow_html=True)
    auth_url = auth.get_auth_url()
    if auth_url:
        st.markdown("### Sign in to access your GA4 data")
        st.markdown(f'<a href="{auth_url}" target="_self" class="auth-button">Sign in with Google</a>', unsafe_allow_html=True)
        st.markdown("")
        st.caption("You'll be asked to authorize access to your Google Analytics properties")
    else:
        st.error("Authentication service unavailable. Please try again later.")

    st.markdown('</div>', unsafe_allow_html=True)
    st.stop()

# User is authenticated - show dashboard
with st.sidebar:
    st.success("Signed in successfully")
    st.caption("Connected to Google Analytics")

    if st.button("Sign Out"):
        auth.logout()
        st.rerun()

    st.divider()

# Initialize GA4 client with OAuth credentials
ga4_client = GA4Client(credentials=st.session_state.auth.get_credentials())

# Sidebar for filters
with st.sidebar:
    st.header("Dashboard Filters")

    # Fetch properties using OAuth
    with st.spinner("Loading GA4 properties..."):
        properties = auth.get_ga4_properties()

    if not properties:
        st.error("No GA4 properties found. Please ensure you have access to at least one GA4 property.")
        st.stop()

    selected_property = st.selectbox(
        "Select GA4 Property",
        options=properties,
        format_func=lambda x: f"{x['display_name']} ({x['parent_account']})"
    )

    st.divider()

    # Date range selector
    st.subheader("Date Range")
    col1, col2 = st.columns(2)
    with col1:
        start_date = st.date_input(
            "Start Date",
            value=datetime.now() - timedelta(days=30)
        )
    with col2:
        end_date = st.date_input(
            "End Date",
            value=datetime.now()
        )

    st.divider()

    # AI Source filter
    st.subheader("AI Traffic Sources")
    ai_source_options = [
        "ChatGPT / OpenAI",
        "Perplexity",
        "Google Gemini / Bard",
        "Microsoft Copilot",
        "Bing Edge AI",
        "Claude AI",
        "Meta AI"
    ]

    selected_ai_sources = st.multiselect(
        "Select AI Sources to Include",
        options=ai_source_options,
        default=ai_source_options,  # All selected by default
        help="Choose which AI platforms to include in the AI traffic comparison. Select 'All' to include all sources."
    )

    # Display selected sources info
    if len(selected_ai_sources) == len(ai_source_options):
        st.caption("📊 Showing data from **all AI sources**")
    elif len(selected_ai_sources) == 0:
        st.warning("⚠️ No AI sources selected. AI traffic data will be empty.")
    else:
        st.caption(f"📊 Showing data from **{len(selected_ai_sources)}** selected source(s)")

# Fetch data when property is selected
if selected_property:
    property_id = selected_property['property_id']

    with st.spinner("Fetching GA4 data..."):
        # Fetch organic traffic data
        organic_data = ga4_client.get_traffic_data(
            property_id=property_id,
            start_date=start_date.strftime("%Y-%m-%d"),
            end_date=end_date.strftime("%Y-%m-%d"),
            traffic_source="organic"
        )

        # Fetch AI mode traffic data with selected sources
        ai_traffic_data = ga4_client.get_traffic_data(
            property_id=property_id,
            start_date=start_date.strftime("%Y-%m-%d"),
            end_date=end_date.strftime("%Y-%m-%d"),
            traffic_source="ai_mode",
            ai_sources=selected_ai_sources if len(selected_ai_sources) > 0 else None
        )

    # Metrics Overview Section
    st.header("Key Metrics Comparison")
    st.markdown("---")

    # Create metrics comparison cards with better layout
    metrics_to_compare = [
        {
            "name": "Sessions",
            "organic": organic_data['summary']['sessions'],
            "ai": ai_traffic_data['summary']['sessions'],
        },
        {
            "name": "Avg Session Duration",
            "organic": organic_data['summary']['avg_session_duration'],
            "ai": ai_traffic_data['summary']['avg_session_duration'],
            "format": "time"
        },
        {
            "name": "Conversions",
            "organic": organic_data['summary']['conversions'],
            "ai": ai_traffic_data['summary']['conversions'],
        },
        {
            "name": "Bounce Rate",
            "organic": organic_data['summary']['bounce_rate'],
            "ai": ai_traffic_data['summary']['bounce_rate'],
            "format": "percentage"
        }
    ]

    # Display each metric in a row with clear Organic vs AI comparison
    for metric in metrics_to_compare:
        st.subheader(metric['name'])
        col1, col2, col3 = st.columns([1, 1, 1])

        with col1:
            st.metric(
                label="🔵 Organic Traffic",
                value=format_metric_value(metric['organic'], metric.get('format')),
            )

        with col2:
            delta = calculate_percentage_change(metric['organic'], metric['ai'])
            st.metric(
                label="🟢 AI Mode Traffic",
                value=format_metric_value(metric['ai'], metric.get('format')),
                delta=f"{delta:+.1f}% vs Organic"
            )

        with col3:
            # Show absolute difference
            if metric.get('format') == 'percentage':
                diff = metric['ai'] - metric['organic']
                st.metric(
                    label="Difference",
                    value=f"{diff:+.2f}pp"
                )
            elif metric.get('format') == 'time':
                diff = metric['ai'] - metric['organic']
                st.metric(
                    label="Difference",
                    value=f"{diff:+.0f}s"
                )
            else:
                diff = metric['ai'] - metric['organic']
                st.metric(
                    label="Difference",
                    value=f"{diff:+,.0f}"
                )

        st.markdown("---")

    # Additional metrics in expandable section
    st.markdown("###")
    with st.expander("View Additional Metrics"):
        additional_cols = st.columns(3)

        additional_metrics = [
            {
                "name": "Pages per Session",
                "organic": organic_data['summary']['pages_per_session'],
                "ai": ai_traffic_data['summary']['pages_per_session'],
            },
            {
                "name": "New Users",
                "organic": organic_data['summary']['new_users'],
                "ai": ai_traffic_data['summary']['new_users'],
            },
            {
                "name": "Engagement Rate",
                "organic": organic_data['summary']['engagement_rate'],
                "ai": ai_traffic_data['summary']['engagement_rate'],
                "format": "percentage"
            }
        ]

        for idx, metric in enumerate(additional_metrics):
            with additional_cols[idx]:
                st.markdown(f"**{metric['name']}**")
                col_a, col_b = st.columns(2)

                with col_a:
                    st.metric(
                        label="Organic",
                        value=format_metric_value(metric['organic'], metric.get('format')),
                    )

                with col_b:
                    delta = calculate_percentage_change(metric['organic'], metric['ai'])
                    st.metric(
                        label="AI Mode",
                        value=format_metric_value(metric['ai'], metric.get('format')),
                        delta=f"{delta:+.1f}%"
                    )

    st.markdown("---")

    # Trends Section
    st.header("Traffic Trends Over Time")

    # Prepare trend data
    organic_trends = pd.DataFrame(organic_data['trends'])
    ai_trends = pd.DataFrame(ai_traffic_data['trends'])

    # Sessions trend
    st.subheader("Sessions")
    fig_sessions = create_comparison_chart(
        organic_trends,
        ai_trends,
        metric_column='sessions',
        title='Sessions: Organic vs AI Mode',
        y_axis_title='Sessions'
    )
    st.plotly_chart(fig_sessions, use_container_width=True)

    st.markdown("###")

    # Create two columns for additional trends
    trend_col1, trend_col2 = st.columns(2)

    with trend_col1:
        st.subheader("Average Session Duration")
        fig_duration = create_comparison_chart(
            organic_trends,
            ai_trends,
            metric_column='avg_session_duration',
            title='Avg Session Duration (seconds)',
            y_axis_title='Duration (seconds)'
        )
        st.plotly_chart(fig_duration, use_container_width=True)

    with trend_col2:
        st.subheader("Conversions")
        fig_conversions = create_comparison_chart(
            organic_trends,
            ai_trends,
            metric_column='conversions',
            title='Conversions Comparison',
            y_axis_title='Conversions'
        )
        st.plotly_chart(fig_conversions, use_container_width=True)

    st.markdown("###")

    # Additional trend charts
    trend_col3, trend_col4 = st.columns(2)

    with trend_col3:
        st.subheader("Bounce Rate")
        fig_bounce = create_comparison_chart(
            organic_trends,
            ai_trends,
            metric_column='bounce_rate',
            title='Bounce Rate Comparison',
            y_axis_title='Bounce Rate (%)'
        )
        st.plotly_chart(fig_bounce, use_container_width=True)

    with trend_col4:
        st.subheader("Pages per Session")
        fig_pages = create_comparison_chart(
            organic_trends,
            ai_trends,
            metric_column='pages_per_session',
            title='Pages per Session',
            y_axis_title='Pages'
        )
        st.plotly_chart(fig_pages, use_container_width=True)

    st.markdown("---")

    # Data table section
    with st.expander("View Raw Data"):
        tab1, tab2 = st.tabs(["Organic Traffic", "AI Mode Traffic"])

        with tab1:
            st.dataframe(organic_trends, use_container_width=True)
            st.download_button(
                label="Download Organic Data (CSV)",
                data=organic_trends.to_csv(index=False),
                file_name=f"organic_traffic_{start_date}_{end_date}.csv",
                mime="text/csv"
            )

        with tab2:
            st.dataframe(ai_trends, use_container_width=True)
            st.download_button(
                label="Download AI Mode Data (CSV)",
                data=ai_trends.to_csv(index=False),
                file_name=f"ai_traffic_{start_date}_{end_date}.csv",
                mime="text/csv"
            )

else:
    st.info("Please select a GA4 property from the sidebar to begin")
