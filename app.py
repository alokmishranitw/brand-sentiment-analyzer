import json
import datetime
import streamlit as st
import pandas as pd
from pytrends.request import TrendReq
import datetime
import time
from typing import List, Dict, Union
from openai import OpenAI
import os
# import matplotlib.pyplot as plt
# import seaborn as sns

# Initialize OpenAI
from env_variables import api_key
model = OpenAI(api_key=api_key)

requests_args = {
    'headers': {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/108.0.0.0 Safari/537.36'
    }
}

class GoogleTrendsBrandAnalyzer:
    def __init__(self):
        """Initialize the Google Trends analyzer with pytrends"""
        # self.pytrends = TrendReq(hl='en-US', tz=360)
        self.pytrends = TrendReq(requests_args=requests_args)
        self.timeout_retry = 5
        self.sleep_time = 60  # Sleep time in seconds when rate limit is hit
        self.backoff_time = 60  # Initial backoff time (in seconds)
        
    def get_interest_over_time(self, keywords: List[str], timeframe: str = 'today 3-m') -> pd.DataFrame:
        """
        Fetch interest over time for given keywords
        
        Args:
            keywords: List of keywords to analyze (max 5 keywords)
            timeframe: Time frame to analyze (e.g., 'today 3-m', 'today 12-m', etc.)
        
        Returns:
            DataFrame with interest over time data
        """
        retry_count = 0
        while retry_count < self.timeout_retry:
            try:
                # Build payload
                self.pytrends.build_payload(keywords, timeframe=timeframe)
                
                # Get interest over time
                interest_df = self.pytrends.interest_over_time()
                
                if not interest_df.empty:
                    return interest_df
                    
            except Exception as e:
                st.write(f"Error fetching trends data: {str(e)}")
                retry_count += 1
                if retry_count < self.timeout_retry:
                    st.write(f"Retrying in {self.sleep_time} seconds...")
                    time.sleep(self.sleep_time)
                    
        return pd.DataFrame()  # Return empty DataFrame if all retries fail
    
    def get_related_queries(self, keywords: List[str], timeframe: str = 'today 3-m') -> Dict:
        """
        Fetch related queries for given keywords
        
        Args:
            keywords: List of keywords to analyze
            timeframe: Time frame to analyze
            
        Returns:
            Dictionary containing related queries
        """
        try:
            self.pytrends.build_payload(keywords, timeframe=timeframe)
            related_queries = self.pytrends.related_queries()
            return related_queries
        except Exception as e:
            st.write(f"Error fetching related queries: {str(e)}")
            return {}
            
    def get_regional_interest(self, keywords: List[str], timeframe: str = 'today 3-m') -> pd.DataFrame:
        """
        Fetch regional interest for given keywords
        
        Args:
            keywords: List of keywords to analyze
            timeframe: Time frame to analyze
            
        Returns:
            DataFrame with regional interest data
        """
        try:
            self.pytrends.build_payload(keywords, timeframe=timeframe)
            regional_interest = self.pytrends.interest_by_region(resolution='COUNTRY')
            return regional_interest
        except Exception as e:
            st.write(f"Error fetching regional interest: {str(e)}")
            return pd.DataFrame()

    def analyze_trends(self,
                      keywords: List[str],
                      timeframe: str = 'today 3-m',
                      include_gpt_analysis: bool = True) -> Dict:
        """
        Comprehensive trends analysis including GPT insights
        
        Args:
            keywords: List of keywords to analyze
            timeframe: Time frame to analyze
            include_gpt_analysis: Whether to include GPT analysis
            
        Returns:
            Dictionary containing analysis results
        """
        analysis = {
            'timestamp': datetime.datetime.now().isoformat(),
            'keywords': keywords,
            'timeframe': timeframe
        }
        interest_df = pd.DataFrame()
        try:
            # Get interest over time
            interest_df = self.get_interest_over_time(keywords, timeframe)
            if not interest_df.empty:
                analysis['interest_over_time'] = interest_df.to_dict()
                
                # Calculate basic statistics
                analysis['statistics'] = {
                    'mean_interest': interest_df.mean().to_dict(),
                    'max_interest': interest_df.max().to_dict(),
                    'min_interest': interest_df.min().to_dict(),
                    'volatility': interest_df.std().to_dict()
                }
        except Exception as e:
            st.write("Error in getting interest over time : ", e)
            pass
        
        # Get related queries
        # related_queries = self.get_related_queries(keywords, timeframe)
        # if related_queries:
        #     analysis['related_queries'] = related_queries

        try:
            # Get regional interest
            regional_interest = self.get_regional_interest(keywords, timeframe)
            if not regional_interest.empty:
                analysis['regional_interest'] = regional_interest.to_dict()
        except Exception as e:
            st.write("Error in getting regional interest : ", e)
            pass
            
        # GPT Analysis
        if include_gpt_analysis and not interest_df.empty:
            trend_summary = self._get_gpt_analysis(interest_df, keywords)
            analysis['gpt_insights'] = trend_summary
            
        return analysis
    
    def _get_gpt_analysis(self, df: pd.DataFrame, keywords: List[str]) -> str:
        """
        Get GPT analysis of trends data
        
        Args:
            df: DataFrame containing trends data
            keywords: List of keywords analyzed
            
        Returns:
            String containing GPT analysis
        """
        try:
            # Prepare data summary for GPT
            data_summary = f"Trends data for keywords {', '.join(keywords)}:\n"
            data_summary += f"Time period: {df.index[0]} to {df.index[-1]}\n"
            data_summary += f"Average interest scores: {df.mean().to_dict()}\n"
            data_summary += f"Peak interest points: {df.idxmax().to_dict()}\n"

            response = model.chat.completions.create(
                model="gpt-4",  # changed "gpt-4-vision-preview" to gpt-4-turbo
                messages=[
                    {"role": "system", "content": "You are a trends analysis expert. Analyze the following Google Trends data and provide insights."},
                    {"role": "user", "content": f"Analyze these Google Trends patterns and provide key insights:\n{data_summary}"}
                ],
                max_tokens=1024,
                # response_format={"type": "json_object"},
                seed=1024
            )
            
            return response.choices[0].message.content
            
        except Exception as e:
            st.write(f"Error in GPT analysis: {str(e)}")
            return "GPT analysis unavailable"

# def main():
#     st.title("Text Analysis Tool")
#     user_input = st.text_area("Enter your text here:", height=150)
#     # Example usage
#     analyzer = GoogleTrendsBrandAnalyzer()

#     # Define brands/keywords to analyze
#     # keywords = ['BMW']  # Example keywords
#     keywords = [user_input]

#     # Process the input when the user clicks the "Analyze" button
#     if st.button("Analyze"):
#         if user_input.strip():
#             # Process the input and display analysis
#             # analysis = process_input(user_input)

#             # Perform analysis
#             analysis = analyzer.analyze_trends(
#                 keywords=keywords,
#                 timeframe='today 3-m',
#                 include_gpt_analysis=True
#             )

#             st.subheader("Analysis Results")
#             # st.write(f"Length of the text: {analysis['length']}")
#             # st.write(f"Uppercase version of text: {analysis['uppercase']}")
#             # st.write(f"Word count: {analysis['word_count']}")
#             st.write(analysis.get('gpt_insights', 'No Answer!!!'))
#         else:
#             st.error("Please enter some text to analyze.")

#     # try:
#     #     # Perform analysis
#     #     analysis = analyzer.analyze_trends(
#     #         keywords=keywords,
#     #         timeframe='today 3-m',
#     #         include_gpt_analysis=True
#     #     )
        
#     #     # st.write("Analysis is : ", analysis)
        
#     #     st.write(f"Analysis completed and saved")
        
#     # except Exception as e:
#     #     st.write(f"Error in main execution: {str(e)}")


import streamlit as st
import time

def generate_campaign_report(analysis, brand_name, start_date="2024-01-01", end_date="2025-02-21"):
    try:
        if analysis=="No Answer!!!":
            return "Campaign Report Can't be generated for empty analysis."
        response = model.chat.completions.create(
            model="gpt-4o",  # changed "gpt-4-vision-preview" to gpt-4-turbo
            messages=[
                {
                    "role": "system", 
                    "content": f"""Generate a comprehensive campaign report for {brand_name} based on sentiment analysis of discussions, reviews, and other relevant data from {start_date} to {end_date}. The report should include the following sections:

                    Overall Sentiment Analysis: Provide an overview of the general sentiment toward the brand during this period, categorizing it as positive, negative, or neutral. Highlight the key factors contributing to these sentiments.

                    Key Discussion Themes: Identify the major themes and topics that were discussed regarding the brand, including any trending keywords, customer feedback, or major points of interest during the period.

                    Potential Areas of Improvement: Highlight any areas where sentiment was negative or neutral, offering actionable insights on how the brand can improve in these aspects to strengthen its presence or image.

                    Campaign Suggestions Based on Positive Sentiment Areas: Suggest specific strategies or actions that can capitalize on areas with strong positive sentiment, such as highlighting successful product features, promoting positive reviews, or engaging in effective messaging.

                    Risk Areas Based on Negative Sentiment: Identify risk areas where the brand may be facing negative sentiment and propose strategies to address or mitigate these risks, such as handling complaints, addressing product/service issues, or improving customer support.

                    Competitor Comparison (if available): If competitor sentiment data is available, provide a comparison of how the brand stacks up against competitors in terms of customer perception, sentiment, and key discussion points.

                    Summarize these findings in a clear, concise report that includes actionable recommendations to optimize the brand’s campaign performance."
                    """
                },
                {
                    "role": "user", 
                    "content": f"Provide the campaign summary based on data given:\n{analysis}"
                }
            ],
            max_tokens=1024,
            # response_format={"type": "json_object"},
            seed=1024
        )
        campaign_summary = response.choices[0].message.content
        return campaign_summary
    
    except Exception as e:
        st.write("Inside Generate Campaign Report Exception : ", e)
        return "Not able to generate campaign reports."


def main():
    st.write("\nApp started....\n")
    # Set page config to ensure full width
    st.set_page_config(layout="wide")
    
    # Add custom CSS to remove side margins and ensure full width
    st.markdown(
        """
        <style>
            /* Set background image for the page */
            .reportview-container {
                background-image: url('https://www.example.com/your-image.jpg');  /* Replace with your image URL */
                background-size: cover;
                background-position: center;
                background-attachment: fixed;
                height: 100vh;  /* Full height */
                margin: 0;
                padding: 0;
            }

            /* Full screen max-width */
            .main {
                max-width: 100% !important;
            }

            /* Block container with padding */
            .block-container {
                padding: 2rem !important;
                color: white;  /* White text color for visibility on dark background */
                border-radius: 15px;
                background-color: rgba(0, 0, 0, 0.5);  /* Semi-transparent background */
            }

            /* Title and headers styling */
            h1, h2, h3 {
                color: #FFD700;  /* Golden color for headings */
            }

            /* Button Styling */
            .stButton > button {
                background-color: #4CAF50;  /* Green background */
                color: white;
                padding: 10px 20px;
                border-radius: 5px;
                font-size: 16px;
                transition: background-color 0.3s ease;
            }

            .stButton > button:hover {
                background-color: #45a049;  /* Darker green on hover */
            }

            /* Styling the columns */
            .css-1d391kg {
                border: 2px solid #FFD700;  /* Golden border around columns */
                border-radius: 10px;
                padding: 20px;
                background-color: rgba(0, 0, 0, 0.5);  /* Semi-transparent background */
            }

            /* Progress bar styling */
            .stProgress {
                # background-color: #4CAF50;
                border-radius: 10px;
            }
        </style>
        """,
        unsafe_allow_html=True,
    )
    st.title("Text Analysis Tool")

    # Create 3 columns: left, center, and right
    col1, col2, col3 = st.columns([2, 4, 2])  # You can adjust the proportions

    # Left Column - Display data with progress bars
    with col1:
        st.subheader("Platforms Data")
        platforms = {
            "Twitter": 45,
            "Facebook": 29,
            "GoogleTrends": 20
        }
        
        for platform, percentage in platforms.items():
            st.write(f"{platform}: {percentage}%")
            st.progress(percentage / 100)  # Progress bar based on the percentage

    # Center Column - Text input and analysis
    with col2:
        user_input = st.text_area("Enter your text here:", height=70)
        analyzer = GoogleTrendsBrandAnalyzer()  # Assuming your GoogleTrendsBrandAnalyzer is defined

        keywords = [user_input]

        if st.button("Analyze"):
            if user_input.strip():
                # # Perform analysis
                st.write("\nGetting Analysis...\n")
                analysis = analyzer.analyze_trends(
                    keywords=keywords,
                    timeframe='today 3-m',
                    include_gpt_analysis=True
                )

                st.subheader("Campaign Summary : Action Plan")
                # st.write(analysis.get('gpt_insights', 'No Answer!!!'))
                st.write("Analysis is : ", analysis.get('gpt_insights', 'No Answer!!!'))
                campaign_report = generate_campaign_report(analysis.get('gpt_insights', 'No Answer!!!'), brand_name=user_input)
                # st.write("Campaign Report is : ", campaign_report)
                st.write(campaign_report)
            else:
                st.error("Please enter some text to analyze.")

    # Right Column - Filter buttons for Time Period and Region
    with col3:
        st.subheader("Filters")

        # Time Period Filter
        time_period = st.selectbox(
            "Select Time Period",
            ["30 Days", "15 Days", "7 Days"]
        )

        # Region Filter
        region = st.selectbox(
            "Select Region",
            ["Saudi Arabia", "India", "America"]
        )

        st.write(f"Selected Time Period: {time_period}")
        st.write(f"Selected Region: {region}")

if __name__ == "__main__":
    main()
