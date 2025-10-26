

"""
This example shows how to simulate / live trade with timeframes on daily level and higher.

Change main() at the bottom of the file whether you would like to run simulation or live trading example.


TODO
Test update functionality of 1d with both 1d and 1m inputs

"""


import _setpath

import pandas as pd
from vbt_sim_live import GenericData, SimData, LiveData, TFs

# dictionary that holds information about which indicators should be
# used for a particular timeframe and its parameters
indicator_info = {
	'd1': {
	    'IndicatorRSI': {'period': 14},
		 'IndicatorBasic': {},
		 'IndicatorMAs': {},
		},
	'w1': {
	    'IndicatorRSI': {'period': 14},
		 'IndicatorBasic': {},
		 'IndicatorMAs': {},
		  },
	'M1': {
	    'IndicatorRSI': {'period': 14},
		 'IndicatorBasic': {},
		 'IndicatorMAs': {},
		  }	
	}

class TesterSim:

	"""class to simulate data on a daily and beyond level"""
	
	def __init__(self):
		pass
			
	def run(self):
				
		# read daily data from csv file  
		df = pd.read_csv("OHLC_Test_Daily_Data.csv")

		# make sure we have the correct column names in our DataFrame
		df = GenericData.df_ensure_format(df)
				
		symbol = "NVDA"
		
		# dictionary to hold all our data classes with timeframe as key
		sim_data = {}
		
		# create ohlc data for timeframes of interest
		sim_data['d1'] = SimData.from_df(df, symbol, TFs['d1'])
		sim_data['w1'] = sim_data['d1'].resample(TFs['w1'])
		sim_data['M1'] = sim_data['d1'].resample(TFs['M1'])

		# set and prepare indicators for timeframes
		sim_data['d1'].set_indicators(indicator_info)
		sim_data['d1'].prepare_indicators()
		 
		sim_data['w1'].set_indicators(indicator_info)		
		sim_data['w1'].prepare_indicators()

		sim_data['M1'].set_indicators(indicator_info)		
		sim_data['M1'].prepare_indicators()

		# convert weekly data to DataFrame and display the results		
		df = sim_data['w1'].to_df(tz_convert=False)
		print(df)
		df.to_csv("sim_data_w1.csv")	

class TesterLive:
	
	"""class to run live data on a daily and beyond level"""

	def __init__(self):
		pass
			
	def run(self):

		# make sure we have the correct column names in our DataFrame		  
		df = pd.read_csv("OHLC_Test_Daily_Data.csv")

		# make sure we have the correct column names in our DataFrame
		df = GenericData.df_ensure_format(df)
				
		symbol = "NVDA"

		# dictionary to hold all our data classes with timeframe as key		
		live_data = {}

		# create ohlc data for timeframes of interest
		live_data['d1'] = LiveData.from_df(df, symbol, TFs['d1'])
		live_data['w1'] = live_data['d1'].resample(TFs['w1'])
		live_data['M1'] = live_data['d1'].resample(TFs['M1'])
		
		# set and prepare indicators for timeframes
		live_data['d1'].set_indicators(indicator_info)
		live_data['d1'].prepare_indicators()
		
		live_data['w1'].set_indicators(indicator_info)		
		live_data['w1'].prepare_indicators()

		live_data['M1'].set_indicators(indicator_info)		
		live_data['M1'].prepare_indicators()
		
		# updating of data not yet included
		# needs to be defined what possible input is to update daily candles
		# would this be minute updates or daily updates?

		# convert monthly data to DataFrame and display the results
		df = live_data['M1'].to_df(tz_convert=False)
		print(df)
		df.to_csv("live_data_M1.csv")
		
if __name__ == "__main__":

	#t = TesterSim()
	t = TesterLive()
	t.run()
