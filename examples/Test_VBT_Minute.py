
"""
This example shows how to simulate / live trade with timeframes on minute level and higher (intraday).

In general, the sequence for running strategies would be as following:
	
	1. Load historical minute data (or live data with a certain lookback period)
	2. Set 1m data and resample other timeframes for it
	3. Set and prepare indicators for all timeframes
	4. Realign features to complete timeframes
	5. Set and prepare strategies (implemented as indicators with a set of standard features)
	6a. For sim: Run simulation on timeframe and evaluate sim results
	6b. For live trading: repeat steps 2-5 for updates and look into strategy return for trade signals
	
Change main() at the bottom of the file whether you would like to run simulation or live trading example.

"""

import _setpath

from datetime import datetime
from vbt_sim_live import GenericData, SimData, LiveData, TFs

import pandas as pd
import pytz
import time

# dictionary that holds information about which indicators should be
# used for a particular timeframe and its parameters

indicator_info = {
	'm1': {
	    'IndicatorRSI': {'period': 14},
		 'IndicatorBasic': {},
		 'IndicatorMAs': {},
		 'IndicatorVWAP': {},
		},
	'm5': {
	    'IndicatorRSI': {'period': 14},
		 'IndicatorBasic': {},
		 'IndicatorMAs': {},
		 'IndicatorVWAP': {},
		  },
	'm30': {
	    'IndicatorRSI': {'period': 14},
		 'IndicatorBasic': {},
		 'IndicatorMAs': {},
		 'IndicatorVWAP': {},
		  }	
	}

# dictionary that holds information about which strategies should be
# used for a particular timeframe and its parameters

strategy_info = {
	'm1': {
	    'StrategyRSI': {
			  'threshold_high':70,
			  'threshold_low':30,
			  'order_type':'limit',
			  'profit_rr': 3,
			  'min_risk': 0.1,
			  'risk_per_trade': 500
			  },
		 },
}

# dictionary that holds information about realignment, where
# 'align' can be 'open' or 'close'
# 'feature' is the name of an (existing) indicator feature on the source timeframe 'from'
# 'to' and 'from' are the particular target and source timeframes

realign_info = [ 
		{'align': 'close', 'feature': 'rsi', 'from': 'm5', 'to': 'm1'},
		{'align': 'close', 'feature': 's20', 'from': 'm5', 'to': 'm1'},	
		{'align': 'close', 'feature': 's200', 'from': 'm5', 'to': 'm1'},	
		{'align': 'close', 'feature': 's20', 'from': 'm30', 'to': 'm1'},	
		{'align': 'close', 'feature': 's200', 'from': 'm30', 'to': 'm1'},
]

# class to simulate data on a minute / intraday level
class TesterSim:
	
	def __init__(self):
		pass

	def run(self):
				
		# read minute data from csv file  	  
		df = pd.read_csv("OHLC_Test_Minute_Data.csv")

		# make sure we have the correct column names in our DataFrame
		df = GenericData.df_ensure_format(df)
				
		symbol = "NVDA"

		# dictionary to hold all our data classes with timeframe as key		
		sim_data = {}
		
		# create ohlc data for timeframes of interest
		# m1 data is coming from the source, other timeframes are resampled from m1		
		sim_data['m1'] = SimData.from_df(df, symbol, TFs['m1'])
		sim_data['m5'] = sim_data['m1'].resample(TFs['m5'])
		sim_data['m30'] = sim_data['m1'].resample(TFs['m30'])
		
		# set and prepare indicators for timeframes
		sim_data['m1'].set_indicators(indicator_info)
		sim_data['m1'].prepare_indicators()
		 
		sim_data['m5'].set_indicators(indicator_info)		
		sim_data['m5'].prepare_indicators()

		sim_data['m30'].set_indicators(indicator_info)		
		sim_data['m30'].prepare_indicators()
		
		# realign indicators
		sim_data['m1'].realign(sim_data['m5'], realign_info)
		sim_data['m1'].realign(sim_data['m30'], realign_info)
	
		# set and calculate strategies
		sim_data['m1'].set_strategies(strategy_info)
		sim_data['m1'].prepare_strategies()

		# define simulation parameters such as sim range and account size
		simulation_parameters = {
			'start': pytz.timezone('America/New_York').localize(datetime(2025,9,10,0,0,0)),
			'end': pytz.timezone('America/New_York').localize(datetime(2025,9,10,23,59,0)),
			'cash': 100000,
			}
		
		# simulate timeframe of interest on m1 data (which is same here)
		sim_data['m1'].simulate(simulation_parameters, sim_data['m1'])

		# convert m5 data to DataFrame and display the results
		df = sim_data['m5'].to_df(tz_convert=True)
		print(df)
		df.to_csv("sim_data_m5.csv")	
		
# class to run live data on a minute / intraday level
class TesterLive:
	
	def __init__(self):
		pass
			
	def run(self):
		  
		df = pd.read_csv("OHLC_Test_Minute_Data.csv")

		# make sure we have the correct column names in our DataFrame
		df = GenericData.df_ensure_format(df)
				
		symbol = "NVDA"
		
		# split up the source data so we can use part of it for preparation (bact calculation)
		# and the other part to feed updates
		df_pre = df[:-1000]
		df_update = df[-1000:]

		# dictionary to hold all our data classes with timeframe as key		
		live_data = {}

		# create ohlc data for timeframes of interest
		# m1 data is coming from the source, other timeframes are resampled from m1
		live_data['m1'] = LiveData.from_df(df_pre, symbol, TFs['m1'])
		live_data['m5'] = live_data['m1'].resample(TFs['m5'])
		live_data['m30'] = live_data['m1'].resample(TFs['m30'])

		# set and prepare indicators for timeframes
		live_data['m1'].set_indicators(indicator_info)
		live_data['m1'].prepare_indicators()
		 
		live_data['m5'].set_indicators(indicator_info)		
		live_data['m5'].prepare_indicators()

		live_data['m30'].set_indicators(indicator_info)		
		live_data['m30'].prepare_indicators()
		
		# realign indicators
		live_data['m1'].realign(live_data['m5'], realign_info)
		live_data['m1'].realign(live_data['m30'], realign_info)
		#live_data['m1'].get_info()

		# set and calculate strategies
		live_data['m1'].set_strategies(strategy_info)
		live_data['m1'].prepare_strategies()

		start_time = time.time()
		
		for i, update_m1 in df_update.iterrows():
			#print("Updating", update_m1.name)
			
			# update ohlc data for m1
			live_data['m1'].update(update_m1)
			
			# create HTF update through resampling
			update_m5 = live_data['m1'].resample(TFs['m5'], update=True)
			update_m30 = live_data['m1'].resample(TFs['m30'], update=True)
			
			# upate ohlc data for HTF
			live_data['m5'].update(update_m5)
			live_data['m30'].update(update_m30)
			
			# update all indicators
			live_data['m1'].update_indicators()
			live_data['m5'].update_indicators()
			live_data['m30'].update_indicators()

			# realign indicators
			live_data['m1'].realign(live_data['m5'], realign_info, update=True)
			live_data['m1'].realign(live_data['m30'], realign_info, update=True)
		
			# update all strategies
			live_data['m1'].update_strategies()
			
			# check if we have gotten a entry signal from our strategy
			row = live_data['m1'].get_row_range(range(-1,0), date_as_datetime=True, tz_convert=True, as_dict=True)
			if row[0]['stratrsi_size'] != 0:
				print("Trade signal")
				
				# in comparison to sim trading, we are continuously updating higher timeframes (m5)
				# while getting m1 updates. Since m5 indicators are part of our strategy, we may want to await
				# the close of the m5 candle even though the m1 signal triggered earlier. 
				# This is how we wait for the 5 Minute to close before actually taking a trade
				if update_m5['cpl']:
					print("  --> 5 MINUTE CLOSE", update_m5)
					
				# order management and communication with broker needs to go here

		time_elapsed = time.time() - start_time
		print(f"{len(df_update)} Updates processed in {time_elapsed:.2f} seconds ({time_elapsed/len(df_update)*1000:.3f}ms per update)")
		
		#live_data['m1'].get_info()

		# convert m5 data to DataFrame and display the results
		df = live_data['m5'].to_df(tz_convert=True)
		print(df)
		df.to_csv("live_data_m5.csv")
		
if __name__ == "__main__":

	#t = TesterSim()
	t = TesterLive()
	t.run()
