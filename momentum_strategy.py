import numpy as np 
import pandas as pd 
import requests 
import xlsxwriter  
import math 
from scipy import stats
import streamlit as st
from PIL import Image
from statistics import mean

#It's good practice to keep the key in a different app but this key is public 
IEX_CLOUD_API_TOKEN = 'Tpk_059b97af715d417d9f49f50b51b1c448'





def chunks(lst, n):
    """Yield successive n-sized chunks from lst."""
    for i in range(0, len(lst), n):
        yield lst[i:i + n] 
  


def build_df(portfolio_size): 
    stocks = pd.read_csv('sp_500_stocks.csv')
    symbol_groups = list(chunks(stocks['Ticker'], 100))
    symbol_strings = []

    for i in range(0, len(symbol_groups)):
        symbol_strings.append(','.join(symbol_groups[i]))

    hqm_columns = [
                    'Ticker', 
                    'Price', 
                    'Number of Shares to Buy', 
                    'One-Year Price Return', 
                    'One-Year Return Percentile',
                    'Six-Month Price Return',
                    'Six-Month Return Percentile',
                    'Three-Month Price Return',
                    'Three-Month Return Percentile',
                    'One-Month Price Return',
                    'One-Month Return Percentile',
                    'HQM Score'
                    ]

    hqm_dataframe = pd.DataFrame(columns = hqm_columns)

    for symbol_string in symbol_strings:
    #     print(symbol_strings)
        batch_api_call_url = f'https://sandbox.iexapis.com/stable/stock/market/batch/?types=stats,quote&symbols={symbol_string}&token={IEX_CLOUD_API_TOKEN}'
        data = requests.get(batch_api_call_url).json()
        for symbol in symbol_string.split(','):
            if not(data.get(symbol) is None):

                hqm_dataframe = hqm_dataframe.append(
                                                pd.Series([symbol, 
                                                        data[symbol]['quote']['latestPrice'],
                                                        'N/A',
                                                        data[symbol]['stats']['year1ChangePercent'],
                                                        'N/A',
                                                        data[symbol]['stats']['month6ChangePercent'],
                                                        'N/A',
                                                        data[symbol]['stats']['month3ChangePercent'],
                                                        'N/A',
                                                        data[symbol]['stats']['month1ChangePercent'],
                                                        'N/A',
                                                        'N/A'
                                                        ], 
                                                        index = hqm_columns), 
                                                ignore_index = True)

        time_periods = [
                        'One-Year',
                        'Six-Month',
                        'Three-Month',
                        'One-Month'
                        ]
        for row in hqm_dataframe.index:
            for time_period in time_periods:
                if hqm_dataframe.loc[row, f'{time_period} Price Return'] == None:
                    hqm_dataframe.loc[row, f'{time_period} Price Return'] = 0

        for row in hqm_dataframe.index:
            for time_period in time_periods:
                hqm_dataframe.loc[row, f'{time_period} Return Percentile'] = stats.percentileofscore(hqm_dataframe[f'{time_period} Price Return'], hqm_dataframe.loc[row, f'{time_period} Price Return'])/100


        for time_period in time_periods:
            print(hqm_dataframe[f'{time_period} Return Percentile'])

        for row in hqm_dataframe.index:
            momentum_percentiles = []
            for time_period in time_periods:
                momentum_percentiles.append(hqm_dataframe.loc[row, f'{time_period} Return Percentile'])
            hqm_dataframe.loc[row, 'HQM Score'] = mean(momentum_percentiles)

        hqm_dataframe.sort_values(by = 'HQM Score', ascending = False)
        hqm_dataframe = hqm_dataframe[:51]
        hqm_dataframe.reset_index(drop = True, inplace = True)

        position_size = float(portfolio_size) / len(hqm_dataframe.index)
    for i in range(0, len(hqm_dataframe['Ticker'])-1):
        hqm_dataframe.loc[i, 'Number of Shares to Buy'] = math.floor(position_size / hqm_dataframe['Price'][i])
    
   
    hqm_dataframe = hqm_dataframe.replace(['N/A'], 0)
    return hqm_dataframe

        
        

st.title('Quantitative Momentum Strategy')

st.write("""
### This investing strategy selects 50 stocks from the S&P 500 with the highest price momentum. """)

image = Image.open('momentum.jpg')
st.image(image, use_column_width=True)

st.write("""
### From there, it will calculate recommended trades for an equal-weight portfolio of these 50 stocks.
""")

capital = st.number_input('Enter the value of your portfolio')
final_df = build_df(capital)
st.table(final_df)
