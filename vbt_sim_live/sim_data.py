# -*- coding: utf-8 -*-

import indicators as inst
import pandas as pd
import numpy as np
import vectorbtpro as vbt
import vectorbtpro_helpers as vbth
from vbt_sim_live import GenericData, TFs
 
class SimData(GenericData):

	"""Data class that can holds sim data in form of a vbt.Data class""" 
    
	def __init__(self, data, symbol, timeframe, tz):
		super().__init__(data, symbol, timeframe, tz)
  
	@classmethod		
	def from_barlist(cls, bars, timeframe, tz = 'America/New_York'):
		
		"""
		TODO
		"""
		
		symbol, df = GenericData.barlist_to_df(bars)
		
		return cls(
			data = vbt.Data.from_data(df, single_key=True, tz_convert=None), #pytz.timezone(tz)
			symbol = symbol,
			timeframe = timeframe,
			tz = tz
	)

	@classmethod		
	def from_df(cls, df: pd.DataFrame, symbol: str, timeframe: TFs, tz = 'America/New_York'):

		"""This method creates a LiveData object based on
		df: DataFrame with input data, needs to have correct feature names and date as index
		symbol: ticker to define stock
		timeframe: timeframe for the given input data (no auto detect)
		
		Returns a new LiveData object.
		""" 
		return cls(
			data = vbt.Data.from_data(df, single_key=True, tz_convert=None),
			symbol = symbol,
			timeframe = timeframe,
			tz = tz
	)
	
	def get_dtype(self, feature_name: str) -> pd.Series.dtype:

		"""This function return the dtype of a feature."""	

		data = self.get_feature(feature_name)
		return data.dtype
	
	def get_feature(self, feature_name: str) -> np.ndarray | pd.Series:

		"""This function will return feature data based on the feature name.
		In case the feature name does not exist, it will reais an exception
		"""

		try:
			if feature_name == "date": return self.data.index.values # return datetime64 without (UTC) timezone
			else: return self.data.get(feature_name)
		except:
			raise Exception("No feature with name", feature_name)	

	def to_df(self, tz_convert: bool = False) -> pd.DataFrame:

		"""This function will convert data to a Pandas DataFrame.
		tz_convert: specifies whether to aply timezone conversion
		"""	

		df = self.data.get()
		
		if tz_convert:
			df.index = df.index.tz_convert(self.tz)
			df['date_l'] = df['date_l'].dt.tz_localize('UTC').dt.tz_convert(self.tz)
		else:
			df.index = df.index.values
			df['date_l'] = df['date_l'].values
			
		df.index.rename('date', inplace=True)
		
		return df 
	
	def resample(self, timeframe: TFs):

		"""This function will resample (downsample) the current data to a new timeframe.
		timeframe: Specifies the new timeframe.
		
		date_l and cpl have special dtypes other than float (int64, bool) and therefore need special treatment.
		Perhaps there is a better way but for now I need to remove and re-add those features.
		
		vbth.get_target_index is required to close possible gaps in the target index, see below.
		
		Returns a new SimData object.
		"""	
		
		if timeframe.is_intraday() and self.timeframe != TFs['m1']:
			raise Exception("m1 timeframe required as source timeframe when resampling to intraday timeframes")

		elif timeframe.is_outsideday() and self.timeframe != TFs['d1']:
			raise Exception("d1 timeframe required as source timeframe when resampling to weekly or monthly timeframes")

		elif timeframe == self.timeframe:
			raise Exception("source and target timeframes cannot be same", timeframe, self.timeframe)

		print("resampling")
		# temporarily set date_l to int for proper resampling
		date_l = self.data.get('date_l').astype('int64')
			
		# remove_features is required to update dtype properly from object to int - otherwise will remain what was before = object
		self.data = self.data.remove_features('date_l').add_feature('date_l', date_l)
		
		# define resampler for special fields
		self.data.feature_config["date_l"] = dict(resample_func=lambda self, obj, resampler: obj.vbt.resample_apply(resampler, vbt.nb.last_reduce_nb))
		self.data.feature_config["cpl"] = dict(resample_func=lambda self, obj, resampler: obj.vbt.resample_apply(resampler, vbt.nb.last_reduce_nb))

		
		# we need to correct the target timeframe for intraday in case of missing data.
		# e.g. a missing 19:50 candle on the 1m still needs to create a 19:50 5m candle.
		
		if timeframe.is_intraday():
			data_resampled = self.data.resample(vbth.get_target_index(self.data.index, timeframe), timeframe.flip())
		else:
			data_resampled = self.data.resample(timeframe.flip())

		# need to convert and re-add feature to obtain bool type
		cpl = data_resampled.get('cpl').astype(bool)
		data_resampled = data_resampled.remove_features('cpl').add_feature('cpl', cpl)
				
		date_l = data_resampled.get('date_l').astype('datetime64[ns]')
		data_resampled = data_resampled.remove_features('date_l').add_feature('date_l',date_l)

		volume = data_resampled.get('volume').astype('int64')
		data_resampled = data_resampled.remove_features('volume').add_feature('volume',volume)

		# now set date_l back to datetime after resampling is complete with int type
		date_l = self.data.get('date_l').astype('datetime64[ns]')
		self.data = self.data.remove_features('date_l').add_feature('date_l', date_l)
				
		return SimData(data_resampled, self.symbol, timeframe, self.tz)


	def realign(self, data_source, realign_info: dict) -> None:

		"""This function realigns data from the given data_source into the current data object,
		taking into account information in realign_info. Information in realign_info, that does 
		not match both involved data classes, will be disregarded.
		
		The process is straightforward based on the vbt methods and docs.
		"""	
		
		if data_source.timeframe.value <= self.timeframe.value:
			raise Exception("Can only realign higher timeframes to lower timeframes, not", data_source.timeframe, "to", self.timeframe)

		if data_source.timeframe.is_outsideday():
			raise Exception("Can only realign intraday data")
			
		for r in realign_info:

			# consider only realign info that is relevant for these two timeframes involved			
			if r['from'] == data_source.timeframe.name and r['to'] == self.timeframe.name:
				
				print("Realigning", r)
				
				realign_from_date = data_source.get_feature('date')			
				realign_from_values = data_source.get_feature(r['feature'])
				realign_to_date = self.get_feature('date')
				
				resampler = vbt.Resampler(realign_from_date, realign_to_date, target_freq=self.timeframe.flip(), source_freq=data_source.timeframe.flip()) 
				
				if r['align'] == 'close':
					realigned_column = realign_from_values.vbt.realign_closing(resampler)
				else:
					realigned_column = realign_from_values.vbt.realign_opening(resampler)

				# copy feature info from source and add it to target data
				# with timeframe "from" appended to name					
				feature_info = data_source.get_feature_info(r['feature'])
				
				if len(feature_info) != 1:
					raise Exception("Unable to get feature info for", r['feature'])
					
				feature_info = dict(feature_info[0])
				
				feature_info['name'] += r['from']
				self.add_feature_info([feature_info])

				# add new feature data				
				self.data = self.data.add_feature(feature_info['name'], realigned_column)			
		

	def run_indicators(self, info: dict, run_args: dict={}) -> None:

		"""This function will run a specific indicator (or strategy) on the current timeframe. 
		
		info: provides indicator information as dict with {indicator name: indicator params}
		e.g. {
		    'IndicatorRSI': {'period': 14},
			 'IndicatorBasic': {},
			 'IndicatorMAs': {},
			}
		
		run_args: may contain additional data, parameters etc. that will be made available to indicator classes
		
		In detail, it will prepare the arguments, depending on definitions in IF implementations,
		provide additional kwargs, run the sim indicator,
		retrieve the results, add feature information and data to this class.
		
		"""	
		
		for i in info.items():
			print("Preparing indicator/strategy",i, "for timeframe", self.timeframe)
			
			vbt_indicator = getattr(inst, i[0])

			# collect input arguments from IF definitions			
			input_args = [self.get_feature(n) for n in vbt_indicator.input_names]
			input_args += [i[1].get(n, None) for n in vbt_indicator.param_names]
	
			input_args_is_none = [n is None for n in input_args]
				
			if any(input_args_is_none):
				missing_fields = [n for i, n in enumerate(vbt_indicator.input_names + vbt_indicator.param_names) if input_args_is_none[i] ]
				raise Exception("Could not populate all input args, missing", missing_fields)
			
			kwargs = {
				 'timeframe':self.timeframe, 
				  'tz': self.tz,				 
				 'class_name':i[0],
				 'param_product':True
				}
			kwargs.update(run_args)
			ret = vbt_indicator.run(*input_args, **kwargs)

			# find feature info and add			
			feature_info = getattr(inst, i[0] + "_feature_info")
			self.add_feature_info(feature_info)

			feature_info_names = [f['name'] for f in feature_info]
			if feature_info_names != list(vbt_indicator.output_names):
				raise Exception("Feature info and output names do not match for indicator/strategy", i[0], feature_info_names, vbt_indicator.output_names)

			# add feature data			
			for i,n in enumerate(vbt_indicator.output_names):
				self.data = self.data.add_feature(n, getattr(ret, n))			

	def simulate(self, simulation_parameters: dict, vbt_data_target) -> None:

		"""
		This function simulates the data of this object, and its particular strategy signals, 
		on target data given by vbt_data_target. This is useful to simulate e.g. a 5m strategy with
		better resolution on a 1m timeframe.
		
		It will only consider the time range given in the simulation parameters, not the entire data
		that is available (and most likely has a large lookback for indicator calculation).
		
		Example:
			simulation_parameters = {
				'start': pytz.timezone('America/New_York').localize(datetime(2025,9,10,0,0,0)),
				'end': pytz.timezone('America/New_York').localize(datetime(2025,9,10,23,59,0)),
				'cash': 100000,
				}			

		For each strategy that is defined for this data object, we will 
		1. extract trading signals from standard strategy outputs
		2. resample signals to target/simulation timeframe
		3. run portfolio calculation
		"""		

		if self.strategy_info is None:
			raise Exception("No strategy info set for symbol, timeframe", self.symbol, self.timeframe)
			
		if vbt_data_target.timeframe.value > self.timeframe.value:
			raise Exception("Cannot simulate timeframe", self.timeframe, "on a higher timeframe target", vbt_data_target.timeframe)
			
		date_range = slice(simulation_parameters['start'],simulation_parameters['end'])

		for strategy in self.strategy_info.keys():
			print("Simulating strategy", strategy, "from", simulation_parameters['start'], "to", simulation_parameters['end'])

			vbt_indicator = getattr(inst, strategy)
			strategy_short_name = vbt_indicator.short_name
			
			# use only sim range here for portfolio evaluation
			# fetch standard signals for the current strategy
			data_source = self.data.loc[date_range]
			price = self.get_feature(strategy_short_name + '_limit').loc[date_range]
			sl_stop = self.get_feature(strategy_short_name + '_stoploss').loc[date_range]
			tp_stop = self.get_feature(strategy_short_name + '_profit').loc[date_range]
			size = self.get_feature(strategy_short_name + '_size').loc[date_range]

			# automatically derive entry signals from size values
			entries_long = size > 0
			entries_short = size < 0
			
			data_target = vbt_data_target.data.loc[date_range]
			
			# resample source signals to target signals
			resampler = vbt.Resampler(data_source.index, data_target.index, target_freq=vbt_data_target.timeframe.flip(), source_freq=self.timeframe.flip()) 
			
			price_target = price.vbt.realign_closing(resampler)
			size_target = np.abs(size.vbt.realign_closing(resampler))
			sl_stop_target = sl_stop.vbt.realign_closing(resampler)
			tp_stop_target = tp_stop.vbt.realign_closing(resampler)

			# in case we are simulating a higher timeframe on a lower timeframe, e.g. 5m strategy on a 1m target timeframe:
			# we cannot forward fill entries, otherwise we could have
			# multiple buy/sells within a 5m window, where we only want to trigger once on the close of the 5m candle
			entries_long_target = entries_long.vbt.realign_closing(resampler, nan_value=False, ffill=False)
			entries_short_target = entries_short.vbt.realign_closing(resampler, nan_value=False, ffill=False)

			# portfolio generation, see vbt docs for details
			pf = vbt.Portfolio.from_signals(
				#close=data.get("Close"), 
				data_target,
				long_entries = entries_long_target, 
				short_entries = entries_short_target,
				#long_exits=ind['exits'],
				price = price_target,
				sl_stop = sl_stop_target,
				tp_stop = tp_stop_target,
				delta_format="target",
				size = size_target, 
				size_type = 'Amount',#'value',
				order_type = self.strategy_info[strategy]['order_type'], #"limit",
				stop_order_type = self.strategy_info[strategy]['order_type'],
				init_cash = simulation_parameters['cash'],
				accumulate = False,
				freq = vbt_data_target.timeframe.flip(),
			)	
	
			# generate stats, orders and print results
			stats = pf.stats([
				'start_value',
				'end_value',
				'total_return', 
				'total_trades', 
				'win_rate', 
				'expectancy',
			], agg_func=None)

			print("Statistics","\n",stats)
			
			orders = pf.orders.records_readable
			
			print("Orders","\n",orders)
			