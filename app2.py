import json
from datetime import datetime, timedelta
import streamlit as st
import time
import pandas as pd
from pytrends.request import TrendReq
import time
from typing import List, Dict, Union
from openai import OpenAI
import os

from serpapi.google_search import GoogleSearch
# from serpapi import GoogleSearch
import pandas as pd
import json
# import matplotlib.pyplot as plt
# import seaborn as sns

# Initialize OpenAI
# from env_variables import api_key
api_key = st.secrets["api_key"]
model = OpenAI(api_key=api_key)
pytrends = TrendReq(hl='en-US',  tz=360)

params = {
	'api_key': '318cc5149d146fa52ccb064984a2e941b6c14a8dc61044b40153c617af0dc2a5',                       # https://serpapi.com/manage-api-key
	'engine': 'google_trends',				# SerpApi search engine	
	'date': 'today 3-m',					# by default Past 12 months
	'cat': 0,								# by default All categories
	# 'geo': '',							# by default Worldwide
	# 'gprop': 'images',					# by default Web Search
	# 'data_type': '',						# type of search (defined in the function)
	# 'q': '',								# query (defined in the function)
}

# def analyze_trends(keywords: List[str],
#                     timeframe: str = 'today 3-m',
#                     include_gpt_analysis: bool = True) -> Dict:
#     """
#     Comprehensive trends analysis including GPT insights
    
#     Args:
#         keywords: List of keywords to analyze
#         timeframe: Time frame to analyze
#         include_gpt_analysis: Whether to include GPT analysis
        
#     Returns:
#         Dictionary containing analysis results
#     """
#     analysis = {
#         'timestamp': datetime.datetime.now().isoformat(),
#         'keywords': keywords,
#         'timeframe': timeframe
#     }
#     interest_df = pd.DataFrame()
#     try:
#         # Get interest over time
#         pytrends.build_payload(keywords, cat=0, timeframe='today 5-y', geo='', gprop='')
#         interest_df = pytrends.interest_over_time()
#         if not interest_df.empty:
#             analysis['interest_over_time'] = interest_df.to_dict()
            
#             # Calculate basic statistics
#             analysis['statistics'] = {
#                 'mean_interest': interest_df.mean().to_dict(),
#                 'max_interest': interest_df.max().to_dict(),
#                 'min_interest': interest_df.min().to_dict(),
#                 'volatility': interest_df.std().to_dict()
#             }
#     except Exception as e:
#         print("Error in getting interest over time : ", e)
#         pass
    
#     # Get related queries
#     # related_queries = self.get_related_queries(keywords, timeframe)
#     # if related_queries:
#     #     analysis['related_queries'] = related_queries

#     try:
#         # Get regional interest
#         regional_interest = self.get_regional_interest(keywords, timeframe)
#         if not regional_interest.empty:
#             analysis['regional_interest'] = regional_interest.to_dict()
#     except Exception as e:
#         print("Error in getting regional interest : ", e)
#         pass
        
#     # GPT Analysis
#     if include_gpt_analysis and not interest_df.empty:
#         trend_summary = get_gpt_analysis(interest_df, keywords)
#         analysis['gpt_insights'] = trend_summary
        
#     return analysis

def get_start_end_date(time_period):
    start_date="2024-01-01"
    end_date="2025-02-21"
    end_date = datetime.now()
    if time_period == "now 7-d":
        start_date = end_date - timedelta(days=7)
    elif time_period == "now 15-d":
        start_date = end_date - timedelta(days=15)
    elif time_period == "today 1-m":
        start_date = end_date - timedelta(days=30)
    elif time_period == "today 2-m":
        start_date = end_date - timedelta(days=60)
    else: # Default is 90 Days
        start_date = end_date - timedelta(days=90)
    return start_date.strftime('%Y-%m-%d'), end_date.strftime('%Y-%m-%d')

def scrape_google_trends(data_type: str, key: str, query: str, geo: str = "", timeframe: str = "today 3-m")-> dict:
    params['data_type'] = data_type
    params['q'] = query
    params['geo'] = geo
    params['date'] = timeframe
    print("Params : ", params)
    search = GoogleSearch(params)           # where data extraction happens on the SerpApi backend
    results = search.get_dict()         	# JSON -> Python dict

    # print("Result : ", results)
    return results

def analyze_trends(query, geo = "", timeframe='today 3-m', include_gpt_analysis=True):
    analysis = {}
    interest_over_time = scrape_google_trends('TIMESERIES', 'interest_over_time', query, geo, timeframe)
    interest_df = pd.DataFrame(interest_over_time["interest_over_time"]['timeline_data'])
    interest_df = interest_df.explode('values')
    df_value = pd.json_normalize(interest_df["values"])[["value"]].rename(columns={"value":query})
    interest_df = pd.concat([interest_df, df_value], axis=1)[["date", query]]
    interest_df[query] = pd.to_numeric(interest_df[query], errors='coerce')
    interest_df[query] = interest_df[query].fillna(0).astype(int)
    interest_df["date"] = pd.to_datetime(interest_df["date"])
    interest_df = interest_df.set_index(["date"])
    analysis['interest_over_time'] = interest_df.to_dict()
            
    # Calculate basic statistics
    analysis['statistics'] = {
        'mean_interest': interest_df.mean().to_dict(),
        'max_interest': interest_df.max().to_dict(),
        'min_interest': interest_df.min().to_dict(),
        'volatility': interest_df.std().to_dict()
    }

    # GPT Analysis
    if include_gpt_analysis and not interest_df.empty:
        trend_summary = get_gpt_analysis(interest_df, query)
        analysis['gpt_insights'] = trend_summary
    return analysis
    
def get_gpt_analysis(df: pd.DataFrame, keywords: List[str]) -> str:
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
    

def generate_campaign_report(analysis, brand_name,  time_period, country_code, country_codes):
    try:
        if analysis=="No Answer!!!":
            return "Campaign Report Can't be generated for empty analysis."
        
        start_date, end_date = get_start_end_date(time_period)
        country_codes = {v:k for k, v in country_codes.items()}
        country_name = country_codes[country_code]
        country_name = country_name + f"({country_code})" if country_name != "Global" else country_name
        response = model.chat.completions.create(
            model="gpt-4o",  # changed "gpt-4-vision-preview" to gpt-4-turbo
            messages=[
                {
                    "role": "system", 
                    "content": f"""Generate a comprehensive campaign report for {brand_name} based on sentiment analysis of discussions, reviews, and other relevant data from {start_date} to {end_date} for {country_name}. 
                    The report should include the following sections:

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
    # Set page config to ensure full width
    st.set_page_config(layout="wide")

    with open('country_codes.json', 'r') as fp:
        country_codes = json.load(fp)
    
    country_names = list(country_codes.keys())
    country_names = ["Global"] + country_names
    country_codes["Global"] = ""
    date_range_mapping = {
        "7 Days": "now 7-d",
        # "15 Days": "now 15-d",
        "30 Days": "today 1-m",
        # "60 Days": "today 2-m",
        "90 Days": "today 3-m"
    }
    
    # Use session state to store country_code
    if 'country_code' not in st.session_state:
        st.session_state.country_code = ""  # Set it to global by default
    if 'date_range' not in st.session_state:
        st.session_state.date_range = "today 3-m"
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
        keywords = [user_input]
        # print("Country Code in col2 : ", st.session_state.country_code)
        if st.button("Analyze"):
            if user_input.strip():
                # # Perform analysis
                analysis = analyze_trends(
                    query=user_input,
                    geo=st.session_state.country_code,
                    # timeframe='today 3-m',
                    timeframe=st.session_state.date_range,
                    include_gpt_analysis=True
                )
                
                st.subheader("Campaign Summary : Action Plan")
                # st.write(analysis.get('gpt_insights', 'No Answer!!!'))

                campaign_report = generate_campaign_report(analysis.get('gpt_insights', 'No Answer!!!'), brand_name=user_input, time_period=st.session_state.date_range, country_code = st.session_state.country_code, country_codes = country_codes)
                # print("Campaign Report is : ", campaign_report)
                st.write(campaign_report)
            else:
                st.error("Please enter some text to analyze.")

    # Right Column - Filter buttons for Time Period and Region
    with col3:
        st.subheader("Filters")

        # Time Period Filter
        time_period = st.selectbox(
            "Select Time Period",
            # ["7 Days", "15 Days", "30 Days", "60 Days", "90 Days"],
	    ["7 Days", "30 Days", "90 Days"],
            index=2
        )

        # Region Filter
        region = st.selectbox(
            "Select Region",
            # ["Saudi Arabia", "India", "America"]
            country_names
        )

        st.session_state.country_code = country_codes[region]
        st.session_state.date_range = date_range_mapping[time_period]
        st.write(f"Selected Time Period: {time_period}")
        st.write(f"Selected Region: {region}")
        st.write(f"Selected Region Code : {country_codes[region]}")

if __name__ == "__main__":
    main()
