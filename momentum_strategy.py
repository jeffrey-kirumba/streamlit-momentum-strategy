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

    def getCloseData(self, ticker):
        symbObj = yf.Ticker(ticker)
        data = symbObj.history(period="1y")
        allCloseData = list(reversed(data['Close'].tolist()))
        self.closeData[ticker] = allCloseData 

    def getAllCloseData(self):
        stocks = pd.read_csv('sp_500_stocks.csv')
        allTickers = list(stocks['Ticker'])
        with ThreadPoolExecutor() as executor:
              executor.map(self.getCloseData, allTickers)

    def getData(self): #speed this up w/ batch queries and threading
        self.getAllCloseData()
        for symbol in self.closeData.keys():
            allData = self.closeData[symbol]
            if len(allData) > 0:
                #year percent change
                yearPercentChange =  allData[0] -  allData[-1] /allData[-1]
                #6month percent
                sixMonthPercentChange = allData[0] - allData[180] / allData[180]
                #3month percent
                threeMonthPercentChange = allData[0] - allData[90] / allData[90]
                #1month percent
                oneMonthPercentChange = allData[0] - allData[30] / allData[30]
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
                                                                'N/A'
                                ], 
                                index = self.columns)
                self.mainFrame.loc[-1] = series
                self.mainFrame.index+=1
                self.mainFrame.sort_index()
        time_periods = ['One-Year', 'Six-Month', 'Three-Month', 'One-Month']
        for row in self.mainFrame.index:
                for time_period in time_periods:
                        if self.mainFrame.loc[row, f'{time_period} Price Return'] == None:
                            self.mainFrame.loc[row, f'{time_period} Price Return'] = 0

                for row in self.mainFrame.index:
                    for time_period in time_periods:
                        self.mainFrame.loc[row, f'{time_period} Return Percentile'] = stats.percentileofscore(self.mainFrame[f'{time_period} Price Return'], self.mainFrame.loc[row, f'{time_period} Price Return'])/100
        print('# of Tickers collected after', len(self.mainFrame.index))
         
    def applyPortfolioValue(self, capital):
        time_periods = ['One-Year', 'Six-Month', 'Three-Month', 'One-Month']
        mainFrame = self.mainFrame
        for row in mainFrame.index:
                momentum_percentiles = []
                for time_period in time_periods:
                    momentum_percentiles.append(mainFrame.loc[row, f'{time_period} Return Percentile'])
                mainFrame.loc[row, 'HQM Score'] = mean(momentum_percentiles)
        mainFrame = mainFrame.sort_values(by = 'HQM Score', ascending = False)
        mainFrame =  mainFrame[:50]
        mainFrame.reset_index(drop = True, inplace = True)
        position_size = float(capital) / len(mainFrame.index)
        for i in range(0, len(mainFrame['Ticker'])-1):
            try:
                mainFrame.loc[i, 'Number of Shares to Buy'] = math.floor(position_size / mainFrame['Price'][i])
            except Exception as e:
                 print(f'This was missing something: {e}')
        hqm_dataframe = mainFrame.replace(['N/A'], 0)
        return hqm_dataframe

m = Momo()
displayFrame = None
st.title('Quantitative Momentum Strategy')
st.write(""" ### This investing strategy selects 50 stocks from the S&P 500 with the highest price momentum. """)
st.write(""" ### From there, it will recommended trades for an equal-weight portfolio of these 50 stocks.""")
image = Image.open('momentum.jpg')
st.image(image, use_column_width=True)
capital = st.number_input('Enter the value of your portfolio')
if 'displayFrame' not in st.session_state:
    with st.spinner('Gathering data'):
        m.getData()
        st.session_state.displayFrame = m.mainFrame
        displayFrame = m.mainFrame
elif capital > 0:
    m.mainFrame = st.session_state.displayFrame
    displayFrame = m.applyPortfolioValue(capital=capital)
st.table(displayFrame)


