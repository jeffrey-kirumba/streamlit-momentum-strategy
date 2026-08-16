import numpy as np 
import pandas as pd 
import requests 
import xlsxwriter  
import math 
from scipy import stats
import streamlit as st
from PIL import Image
from statistics import mean
import yfinance as yf
import datetime
import time
from typing import List
from concurrent.futures import ThreadPoolExecutor
        
class Momo:
    def __init__(self) -> None:
        self.columns = [
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
        self.mainFrame = pd.DataFrame(columns = self.columns)
        self.closeData = {}
    
    def chunks(self, lst, n):
        """Yield successive n-sized chunks from lst."""
        final = []
        for i in range(0, len(lst), n):
            final.append(lst[i:i + n])
        return final

    def getCloseData(self, tickers: List[str]):
         tickData = yf.download(tickers=tickers, period="1y")
         for tick in tickers:
                allCloseData = list(reversed(tickData.loc[:, ('Close', tick)].tolist()))
                self.closeData[tick] = allCloseData
 
    def getAllCloseData(self):
        stocks = pd.read_csv('sp_500_stocks.csv')
        allTickers = list(stocks['Ticker'])
        groups = len(allTickers) // 10
        args = self.chunks(list(allTickers), groups)
        for arg in args:
            self.getCloseData(tickers=arg)
        print(f"Got all close data")

    def getData(self):
        self.getAllCloseData()
        # print(f"Got all close data")
        for symbol in self.closeData.keys():
            allData = self.closeData[symbol]
            if len(allData) >= 250 :
                #year percent change
                yearPercentChange =  abs(allData[0] -  allData[-1]) /allData[-1]
                #6month percent
                sixMonthElement = len(allData) // 2
                sixMonthPercentChange = abs(allData[0] - allData[sixMonthElement])/ allData[sixMonthElement]
                #3month percent
                threeMonthElement = len(allData) // 4
                threeMonthPercentChange = abs(allData[0] - allData[threeMonthElement])/ allData[threeMonthElement]
                #1month percent
                oneMonthElement = len(allData) // 12
                oneMonthPercentChange = abs(allData[0] - allData[oneMonthElement])/ allData[oneMonthElement]
                series =  pd.Series([symbol, 
                            allData[0],
                            'N/A',
                            yearPercentChange,
                            'N/A',
                            sixMonthPercentChange,
                            'N/A',
                            threeMonthPercentChange,
                            'N/A',
                            oneMonthPercentChange,
                            'N/A',
                            'N/A'], 
                                index = self.columns)
                self.mainFrame.loc[-1] = series
                self.mainFrame.index+=1
                self.mainFrame.sort_index()
        print(f"Added all Returns")
        #remove nan values
        self.mainFrame["Price"] = pd.to_numeric(self.mainFrame["Price"], errors="coerce")
        self.mainFrame = self.mainFrame.dropna(subset=["Price"])

        print(f"Removed nan prices")
        time_periods = ['One-Year', 'Six-Month', 'Three-Month', 'One-Month']
        #remove nan or null return vals
        for row in self.mainFrame.index:
                for time_period in time_periods:
                    col = f"{time_period} Price Return"
                    self.mainFrame[col] = pd.to_numeric(self.mainFrame[col], errors="coerce")
                    self.mainFrame[col] = self.mainFrame[col].fillna(0)
        print(f"Replaced nan returns with zero")
        #calc percentiles
        for row in self.mainFrame.index:
            for time_period in time_periods:
                self.mainFrame.loc[row, f'{time_period} Return Percentile'] = stats.percentileofscore(self.mainFrame[f'{time_period} Price Return'], self.mainFrame.loc[row, f'{time_period} Price Return'])/100
        print(f"Calculated percentiles")
        #calc, then sort by HQM Score
        for row in self.mainFrame.index:
                momentum_percentiles = []
                for time_period in time_periods:
                    momentum_percentiles.append(self.mainFrame.loc[row, f'{time_period} Return Percentile'])
                self.mainFrame.loc[row, 'HQM Score'] = mean(momentum_percentiles)
        self.mainFrame = self.mainFrame.sort_values(by = 'HQM Score', ascending = False)
        self.mainFrame =  self.mainFrame[:50]
        self.mainFrame.reset_index(drop = True, inplace = True)
                        
         
    def applyPortfolioValue(self, capital):
        mainFrame = self.mainFrame
        position_size = float(capital) / len(mainFrame.index)
        for i in range(0, len(mainFrame['Ticker'])-1):
            try:
                mainFrame.loc[i, 'Number of Shares to Buy'] = math.floor(position_size / mainFrame['Price'][i])
            except Exception as e:
                 print(f'This was missing something: {e}')
        hqm_dataframe = mainFrame.replace(['N/A'], 0)
        return hqm_dataframe
    
# @st.cache_resource(show_spinner=False)
def buttonPushed():
    m = Momo()
    with st.spinner('Gathering data'):
        m.getData()
        st.session_state.displayFrame = m.mainFrame
    st.session_state.buttonPushed = True

          
m = Momo()
displayFrame = None
st.title('Quantitative Momentum Strategy')
st.write(""" ### This investing strategy selects 50 stocks from the S&P 500 with the highest price momentum. """)
st.write(""" ### From there, it will recommended trades for an equal-weight portfolio of these 50 stocks.""")
image = Image.open('momentum.jpg')
st.image(image, use_column_width=True)


if 'buttonPushed' not in st.session_state:
    st.button(label='Get Started', on_click=buttonPushed)

if 'displayFrame' in st.session_state and not st.session_state.displayFrame.empty:
    displayFrame = st.session_state.displayFrame
    capital = st.number_input('Enter the value of your portfolio')
    if capital > 0:
        m.mainFrame = st.session_state.displayFrame
        displayFrame = m.applyPortfolioValue(capital=capital)
    st.table(displayFrame)
else:
    st.write(st.session_state)


