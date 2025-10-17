from google.analytics.data_v1beta import BetaAnalyticsDataClient
from google.analytics.data_v1beta.types import (
    DateRange,
    Dimension,
    Metric,
    RunReportRequest,
    FilterExpression,
    Filter,
)
from google.oauth2.service_account import Credentials
import os
import json
from datetime import datetime


class GA4Client:
    """Client for fetching Google Analytics 4 data"""

    def __init__(self, credentials_path=None, credentials=None):
        """
        Initialize GA4 client with credentials

        Args:
            credentials_path: Path to service account JSON file.
            credentials: OAuth credentials object (from google.oauth2.credentials)
                        If None, will look for GOOGLE_APPLICATION_CREDENTIALS env var
        """
        if credentials:
            # Use provided OAuth credentials
            self.credentials = credentials
        elif credentials_path:
            self.credentials = Credentials.from_service_account_file(credentials_path)
        else:
            # Use environment variable
            credentials_path = os.getenv('GOOGLE_APPLICATION_CREDENTIALS')
            if credentials_path and os.path.exists(credentials_path):
                self.credentials = Credentials.from_service_account_file(credentials_path)
            else:
                self.credentials = None

        if self.credentials:
            self.client = BetaAnalyticsDataClient(credentials=self.credentials)
        else:
            self.client = None

    def get_properties(self):
        """
        Get list of available GA4 properties

        Returns:
            list: List of property dictionaries with property_id and display_name
        """
        # In a real implementation, you would fetch this from the Admin API
        # For now, return properties from environment variable or config
        properties_json = os.getenv('GA4_PROPERTIES')

        if properties_json:
            return json.loads(properties_json)

        # Default fallback - you should configure this
        return [
            {
                'property_id': '123456789',
                'display_name': 'My Website - GA4'
            }
        ]

    def get_traffic_data(self, property_id, start_date, end_date, traffic_source, ai_sources=None):
        """
        Fetch traffic data from GA4

        Args:
            property_id: GA4 property ID
            start_date: Start date in YYYY-MM-DD format
            end_date: End date in YYYY-MM-DD format
            traffic_source: Either 'organic' or 'ai_mode'
            ai_sources: List of AI source names to filter (only used when traffic_source='ai_mode')

        Returns:
            dict: Dictionary containing summary metrics and trends
        """
        if not self.client:
            # Return mock data if no credentials
            return self._get_mock_data(start_date, end_date, traffic_source)

        # Define metrics to fetch
        metrics = [
            Metric(name="sessions"),
            Metric(name="averageSessionDuration"),
            Metric(name="conversions"),
            Metric(name="bounceRate"),
            Metric(name="screenPageViewsPerSession"),
            Metric(name="newUsers"),
            Metric(name="engagementRate"),
        ]

        # Define dimensions
        dimensions = [
            Dimension(name="date"),
        ]

        # Create filter based on traffic source
        dimension_filter = self._create_traffic_filter(traffic_source, ai_sources)

        # Run the report
        request = RunReportRequest(
            property=f"properties/{property_id}",
            dimensions=dimensions,
            metrics=metrics,
            date_ranges=[DateRange(start_date=start_date, end_date=end_date)],
            dimension_filter=dimension_filter,
        )

        response = self.client.run_report(request)

        # Process response
        return self._process_response(response)

    def _create_traffic_filter(self, traffic_source, ai_sources=None):
        """Create dimension filter for traffic source

        Args:
            traffic_source: Either 'organic' or 'ai_mode'
            ai_sources: List of AI source names to filter (only used when traffic_source='ai_mode')
        """
        if traffic_source == "organic":
            # Filter for organic search traffic
            return FilterExpression(
                filter=Filter(
                    field_name="sessionDefaultChannelGroup",
                    string_filter=Filter.StringFilter(value="Organic Search"),
                )
            )
        elif traffic_source == "ai_mode":
            # Map of AI source names to their regex patterns
            ai_source_patterns = {
                "ChatGPT / OpenAI": r"(chatgpt\.com|openai\.com)",
                "Perplexity": r".*perplexity.*",
                "Google Gemini / Bard": r"(gemini|bard)\.google\.com",
                "Microsoft Copilot": r"copilot\.microsoft\.com",
                "Bing Edge AI": r"edge(pilot|services)\.bing\.com",
                "Claude AI": r"claude\.ai",
                "Meta AI": r"meta\.ai"
            }

            # If no specific sources selected, use all
            if not ai_sources or len(ai_sources) == 0:
                selected_patterns = list(ai_source_patterns.values())
            else:
                selected_patterns = [ai_source_patterns[source] for source in ai_sources if source in ai_source_patterns]

            # If no valid patterns, return None (no filter)
            if not selected_patterns:
                return None

            # Combine patterns with OR
            combined_pattern = r"^.*(" + "|".join(selected_patterns) + r")$"

            return FilterExpression(
                filter=Filter(
                    field_name="sessionSource",
                    string_filter=Filter.StringFilter(
                        value=combined_pattern,
                        match_type=Filter.StringFilter.MatchType.FULL_REGEXP
                    ),
                )
            )
        return None

    def _process_response(self, response):
        """Process GA4 API response into structured data"""
        # Use a dictionary to aggregate data by date
        date_data = {}
        totals = {
            'sessions': 0,
            'avg_session_duration': 0,
            'conversions': 0,
            'bounce_rate': 0,
            'pages_per_session': 0,
            'new_users': 0,
            'engagement_rate': 0,
        }

        for row in response.rows:
            date_str = row.dimension_values[0].value
            date_formatted = datetime.strptime(date_str, "%Y%m%d").strftime("%Y-%m-%d")

            sessions = float(row.metric_values[0].value)
            avg_duration = float(row.metric_values[1].value)
            conversions = float(row.metric_values[2].value)
            bounce_rate = float(row.metric_values[3].value) * 100
            pages_per_session = float(row.metric_values[4].value)
            new_users = float(row.metric_values[5].value)
            engagement_rate = float(row.metric_values[6].value) * 100

            # Aggregate by date (sum counters, average rates)
            if date_formatted not in date_data:
                date_data[date_formatted] = {
                    'sessions': 0,
                    'avg_session_duration': [],
                    'conversions': 0,
                    'bounce_rate': [],
                    'pages_per_session': [],
                    'new_users': 0,
                    'engagement_rate': [],
                }

            date_data[date_formatted]['sessions'] += sessions
            date_data[date_formatted]['avg_session_duration'].append(avg_duration)
            date_data[date_formatted]['conversions'] += conversions
            date_data[date_formatted]['bounce_rate'].append(bounce_rate)
            date_data[date_formatted]['pages_per_session'].append(pages_per_session)
            date_data[date_formatted]['new_users'] += new_users
            date_data[date_formatted]['engagement_rate'].append(engagement_rate)

        # Convert aggregated data to trends list
        trends = []
        for date_formatted in sorted(date_data.keys()):
            data = date_data[date_formatted]

            # Average the rate metrics
            import numpy as np
            avg_duration = np.mean(data['avg_session_duration'])
            bounce_rate = np.mean(data['bounce_rate'])
            pages_per_session = np.mean(data['pages_per_session'])
            engagement_rate = np.mean(data['engagement_rate'])

            trends.append({
                'date': date_formatted,
                'sessions': data['sessions'],
                'avg_session_duration': avg_duration,
                'conversions': data['conversions'],
                'bounce_rate': bounce_rate,
                'pages_per_session': pages_per_session,
                'new_users': data['new_users'],
                'engagement_rate': engagement_rate,
            })

            # Accumulate totals
            totals['sessions'] += data['sessions']
            totals['avg_session_duration'] += avg_duration
            totals['conversions'] += data['conversions']
            totals['bounce_rate'] += bounce_rate
            totals['pages_per_session'] += pages_per_session
            totals['new_users'] += data['new_users']
            totals['engagement_rate'] += engagement_rate

        # Calculate averages for summary
        row_count = len(trends)
        if row_count > 0:
            totals['avg_session_duration'] = totals['avg_session_duration'] / row_count
            totals['bounce_rate'] = totals['bounce_rate'] / row_count
            totals['pages_per_session'] = totals['pages_per_session'] / row_count
            totals['engagement_rate'] = totals['engagement_rate'] / row_count

        return {
            'summary': totals,
            'trends': trends
        }

    def _get_mock_data(self, start_date, end_date, traffic_source):
        """Generate mock data for testing purposes"""
        import pandas as pd
        import numpy as np

        # Generate date range
        date_range = pd.date_range(start=start_date, end=end_date, freq='D')

        # Base multiplier for AI vs Organic
        multiplier = 0.3 if traffic_source == 'ai_mode' else 1.0

        # Generate realistic mock data
        np.random.seed(42 if traffic_source == 'organic' else 24)

        trends = []
        for date in date_range:
            # Add some randomness and weekly patterns
            day_of_week = date.dayofweek
            weekend_factor = 0.7 if day_of_week >= 5 else 1.0

            base_sessions = 1000 * multiplier * weekend_factor
            sessions = int(base_sessions + np.random.normal(0, base_sessions * 0.2))

            trends.append({
                'date': date.strftime('%Y-%m-%d'),
                'sessions': max(sessions, 0),
                'avg_session_duration': max(120 + np.random.normal(0, 30), 30) * (1.2 if traffic_source == 'ai_mode' else 1.0),
                'conversions': max(int(sessions * 0.02 + np.random.normal(0, 5)), 0),
                'bounce_rate': min(max(45 + np.random.normal(0, 5), 20), 80) * (0.8 if traffic_source == 'ai_mode' else 1.0),
                'pages_per_session': max(2.5 + np.random.normal(0, 0.5), 1) * (1.3 if traffic_source == 'ai_mode' else 1.0),
                'new_users': max(int(sessions * 0.6 + np.random.normal(0, 50)), 0),
                'engagement_rate': min(max(55 + np.random.normal(0, 5), 30), 90) * (1.15 if traffic_source == 'ai_mode' else 1.0),
            })

        # Calculate summary
        summary = {
            'sessions': sum(t['sessions'] for t in trends),
            'avg_session_duration': np.mean([t['avg_session_duration'] for t in trends]),
            'conversions': sum(t['conversions'] for t in trends),
            'bounce_rate': np.mean([t['bounce_rate'] for t in trends]),
            'pages_per_session': np.mean([t['pages_per_session'] for t in trends]),
            'new_users': sum(t['new_users'] for t in trends),
            'engagement_rate': np.mean([t['engagement_rate'] for t in trends]),
        }

        return {
            'summary': summary,
            'trends': trends
        }
