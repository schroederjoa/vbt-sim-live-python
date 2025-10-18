# -*- coding: utf-8 -*-

import datetime
import indicators as inst
import numpy_indexed as npi
import numpy as np
import pandas as pd
import pytz
from typing import Dict, List
from vbt_sim_live import GenericData, TFs
import vectorbtpro_helpers as vbth
		
class LiveData(GenericData):

	"""Data class that can holds live data in form of numpy arrays""" 

	def __init__(self, data, symbol, timeframe, tz):
		super().__init__(data, symbol, timeframe, tz)
		
	@classmethod		
	def from_barlist(cls, bars, timeframe, tz = 'America/New_York'):

		"""
		TODO
		""" 
		symbol, df = GenericData.barlist_to_df(bars)
		
		data = {c: df[c].to_numpy() for c in df.columns if c not in ['date','date_l']}
		data['date'] = df.index.values#.tz_convert(tz).to_pydatetime()
		data['date_l'] = df['date_l'].values#.tz_convert(tz).to_pydatetime()
		return cls(
			data = data,
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

		data = {c: df[c].to_numpy() for c in df.columns}
		data['date'] = df.index.values
				
		return cls(
			data = data,
			symbol = symbol,
			timeframe = timeframe,
			tz = tz
	)

	def add_feature(self, feature_name: str, feature_data: np.ndarray) -> None:

		"""This function will add feature data to the class, and possibly overwrite existing features with the same name."""	

		self.data[feature_name] = feature_data
		
	def get_dtype(self, feature_name: str) -> np.dtype:

		"""This function return the dtype of a feature."""	
		
		data = self.get_feature(feature_name)
		return data.dtype
		
	def get_feature(self, feature_name: str) -> np.ndarray:

		"""This function will return feature data based on the feature name.
		In case the feature name does not exist, it will reais an exception
		"""	

		try:
			return self.data[feature_name]
		except:
			raise Exception("No feature with name", feature_name)
	
	def get_row_range(self, idx_range: range, date_as_datetime=False, tz_convert=False, as_dict=False) -> List[Dict] | List[np.ndarray]:
		
		"""This function will return a number of rows of all data arrays, defined by an index rang idx_range.
		date_as_datetime: specifies whether date and date_l columns should be converted to datetime or unix timestamp [s]
		tz_convert: specifies whether timezone conversion should be performed in case of date_as_datetime=True.
		as_dict: specified whether to export data as list of np arrays or as list of dicts.
		"""
		
		if isinstance(idx_range, int):
			idx_range = range(idx_range, idx_range+1)
			
		data = [self.get_feature(f)[idx_range].tolist( )if f not in ['date','date_l'] else self.get_feature(f)[idx_range] for f in self.get_feature_names() ]
		
		# date columns are always first and second
		assert self.get_feature_names()[0] == "date" and self.get_feature_names()[1] == "date_l", "Column order mismatch, 1st must be date, 2nd must be date_l"
		
		if date_as_datetime:
			if tz_convert:
				data[0] = [datetime.datetime.utcfromtimestamp(d).astimezone(pytz.timezone(self.tz)) for d in data[0].astype('datetime64[s]').astype('int64')]
				data[1] = [datetime.datetime.utcfromtimestamp(d).astimezone(pytz.timezone(self.tz)) for d in data[1].astype('datetime64[s]').astype('int64')]

			else:
				data[0] = data[0].astype('datetime64[s]').tolist()
				data[1] = data[1].astype('datetime64[s]').tolist()

		else:
			data[0] = data[0].astype('datetime64[s]').astype('int64').tolist()
			data[1] = data[1].astype('datetime64[s]').astype('int64').tolist()
			
		if as_dict:
			return [ {n: data[i][j] for i, n in enumerate(self.get_feature_names())} for j in range(len(data[0]))]
		else:
			return data# self.data['close'][idx_range] 
		
	def to_df(self, tz_convert: bool = False, set_index: bool = True) -> pd.DataFrame:

		"""This function will convert data to a Pandas DataFrame.
		tz_convert: specifies whether to aply timezone conversion
		set_index: specifies whether date should be set as index or not
		"""	

		df = pd.DataFrame(self.data)
				
		if tz_convert:
			#df.index = df.index.tz_convert(self.tz)
			df['date'] = df['date'].dt.tz_localize('UTC').dt.tz_convert(self.tz)
			df['date_l'] = df['date_l'].dt.tz_localize('UTC').dt.tz_convert(self.tz)
			
		if set_index: df = df.set_index('date')
		return df

	def resample(self, timeframe: TFs, update: bool = False):

		"""This function resamples (downsampling) the current OHLCV data into a new LiveData class.
		timeframe: defines the timeframe of the new class
		update:  specifies whether we will processing the entire dataset or only the last part, resuling in a single resampled row.
		
		The general idea is to generate a key that will hold the number of resampled candles since Unix Epoch.
		This key will then be used to perform groupby. Special attention is required to re-generate date and cpl of the 
		resampled data, since this must be done individually for specific timeframes.
		"""	
				
		if update:
			start_index = max(0, len(self.data['cpl'])-2*timeframe.value//60)
		else:
			start_index = 0
			
		date = self.data['date'][start_index:]
		datel = self.data['date_l'][start_index:]
		open = self.data['open'][start_index:]
		high = self.data['high'][start_index:]
		low = self.data['low'][start_index:]
		close = self.data['close'][start_index:]
		volume = self.data['volume'][start_index:]
		
		# intraday
		if timeframe.value < 24*60*60:
			date_base = date.astype('int64') // 10**9
			date_base = date_base // timeframe.value
			
		# unfortunately, no embedded week function in datetime64
		elif timeframe.name == "w1":
			date_base = date.astype('int64') // 10**9 + 345600 # weeks from 1.1.1970, starting the first monday
			date_base = date_base // timeframe.value		
		elif timeframe.name == 'M1':
			date_base = pd.to_datetime(date.astype('datetime64[M]')).astype('int64')
		else:
			self.log.error("Error resample(), no valid timeframe for resamling, aborting", timeframe)
			return None
		
		groupby = npi.group_by(date_base)

		ret = {}

		keys, ret['date_l'] = groupby.last(datel)
		keys, ret['open'] = groupby.first(open)	
		keys, ret['high'] = groupby.max(high)
		keys, ret['low'] = groupby.min(low)
		keys, ret['close'] = groupby.last(close)
		keys, ret['volume'] = groupby.sum(volume)
		
		ret['cpl'] = np.full(len(ret['open']), False, dtype=np.bool_)
		
		if timeframe.value < 24*60*60:
			ret['date'] = (keys * timeframe.value * 10**9).astype('datetime64[ns]')
			
			src_last_entry_complete = self.data['cpl'][-1]			
			# check if this was the last update within this key
			next_minute = ret['date_l'][-1].astype('datetime64[s]') + 60#timedelta(minutes=1)
			next_minute_key = next_minute.astype('int64') // timeframe.value
			
			# set last candle status of resampled array if 1m src candle was complete and was last one in this key period
			last_candle_complete = src_last_entry_complete and next_minute_key != keys[-1]
		
		elif timeframe.name == 'w1':
			ret['date'] = ((keys * timeframe.value + 345600-604800) * 10**9 ).astype('datetime64[ns]')
			last_date = pd.Timestamp(ret['date_l'][-1]).to_pydatetime('utc')
			
			last_candle_complete = vbth.is_last_day_of_week(last_date)
			
		elif timeframe.name == 'M1':
			ret['date'] = (keys * 10**9).astype('datetime64[ns]')#.astype('int64')	
			last_date = pd.Timestamp(ret['date_l'][-1]).to_pydatetime('utc')
			
			last_candle_complete = vbth.is_last_day_of_month(last_date)

		else:
			self.log.error("Error resample(), no valid timeframe for resamling, aborting", timeframe)
			return None		
		
		ret['cpl'][:-1] = True
		ret['cpl'][-1] = last_candle_complete
		
		# in case of update, return last ohlcv row only and avoid creating a new LiveData object
		if update:
			return {
				'date': ret['date'][-1], #datetime.fromtimestamp(ret['date'][-1], pytz.utc),
				'date_l': ret['date_l'][-1], #datetime.fromtimestamp(ret['date_l'][-1].astype('int64'), pytz.utc),
				'open': ret['open'][-1],
				'high': ret['high'][-1],
				'low': ret['low'][-1],
				'close': ret['close'][-1],
				'volume': ret['volume'][-1],
				'cpl': ret['cpl'][-1],
			}
		else:
			return LiveData(ret, self.symbol, timeframe, self.tz)

	def realign(self, data_source, realign_info: dict, update: bool = False) -> None:

		"""This function realigns data from the given data_source into the current data object,
		taking into account information in realign_info. Information in realign_info, that does 
		not match both involved data classes, will be disregarded.
		
		In case of update=True, we will simply copy/update the last datapoint.
		"""	
		
		if data_source.timeframe.value <= self.timeframe.value:
			raise Exception("Can only realign higher timeframes to lower timeframes, not", data_source.timeframe, "to", self.timeframe)
				
		for r in realign_info:
			
			# consider only realign info that is relevant for these two timeframes involved
			if r['from'] == data_source.timeframe.name and r['to'] == self.timeframe.name:
				
				realign_from_dates = data_source.get_feature('date')			
				realign_to_dates = self.get_feature('date')
				realign_from_values = data_source.get_feature(r['feature'])
					
				if update:

					# When trading live, we want to see how a higher TF value develops,
					# and receive live updates rather than looking at the previous "close" value.
					# Therefore, we simply copy the latest HTF value.
					realign_to_values = self.get_feature(r['feature']+r['from'])
					realign_to_values[-1] = realign_from_values[-1]
					
				else:
					print("Realigning", r)
	
					# create dataframe "to" with date and key
					df_to = pd.DataFrame()
					df_to['date'] = realign_to_dates
					
					# pick the correct key, depending on realignment type "open" or "close"
					if r['align'] == 'open':
						df_to['key'] = realign_to_dates.astype('datetime64[s]').astype(np.int64) // TFs[r['from']].value
					else:
						df_to['key'] = (realign_to_dates.astype('datetime64[s]').astype(np.int64) - TFs[r['from']].value + 1*TFs[r['to']].value) // TFs[r['from']].value

					# create dataframe "from" with date, key and values to be realigned			
					df_from = pd.DataFrame()		
					df_from['date'] = realign_from_dates
					df_from['key'] = realign_from_dates.astype('datetime64[s]').astype(np.int64) // TFs[r['from']].value
					df_from['values'] = realign_from_values
					
					# merge both DataFrames based on key
					df_merge = pd.merge(df_to, df_from, how='left', on='key')
		
					# copy feature info from source and add it to target data
					# with timeframe "from" appended to name
					feature_info = data_source.get_feature_info(r['feature'])
					if len(feature_info) != 1:
						raise Exception("Unable to get feature info for", r['feature'])
						
					feature_info = dict(feature_info[0])
					feature_info['name'] += r['from']
					self.add_feature_info([feature_info])

					# extract realigned values and add new feature data
					realigned_column = np.array(df_merge['values'].to_numpy(), dtype=feature_info['type_np'])
					self.add_feature(feature_info['name'], realigned_column)	
				
			
	def run_indicators(self, info: dict, run_args: dict={}) -> []:

		"""This function will run a specific indicator (or strategy) on the current timeframe. 
		
		info: provides indicator information as dict with {indicator name: indicator params}
		e.g. {
		    'IndicatorRSI': {'period': 14},
			 'IndicatorBasic': {},
			 'IndicatorMAs': {},
			}
		
		run_args: may contain additional data, parameters etc. that will be made available to indicator classes
		
		In detail, it will prepare the arguments, depending on definitions in IF implementations,
		provide additional kwargs, create a live indicator (with _ extension), run its prepare() method,
		retrieve the results, add feature information and data to this class.
		
		Returns a list of created indicator objects.
		"""	
		
		indicators = []
		
		for i in info.items():
			print("Preparing indicator/strategy",i, "for timeframe", self.timeframe)
			
			# get indicator classes
			vbt_indicator = getattr(inst, i[0])
			live_indicator = getattr(inst, i[0] + "_")
			
			# collect input arguments from IF definitions
			input_args = [self.get_feature(n) for n in vbt_indicator.input_names]
			input_args += [i[1].get(n, None) for n in vbt_indicator.param_names]
	
			input_args_is_none = [n is None for n in input_args]
				
			if any(input_args_is_none):
				missing_fields = [n for i, n in enumerate(vbt_indicator.input_names + vbt_indicator.param_names) if input_args_is_none[i] ]
				raise Exception("Could not populate all input args, missing", missing_fields)
			
			# assembly kwargs
			kwargs = {
				'timeframe': self.timeframe,
				'tz': self.tz,
				}
			kwargs.update(run_args)
			
			# create indicator, run prepare() and retrieve results
			ind = live_indicator(input_args, kwargs)
			ind.prepare()
			ret = ind.get()
			indicators.append(ind)
			
			# find feature info and add
			feature_info = getattr(inst, i[0] + "_feature_info")
			self.add_feature_info(feature_info)
			
			feature_info_names = [f['name'] for f in feature_info]
			if feature_info_names != list(vbt_indicator.output_names):
				raise Exception("Feature info and output names do not match for indicator/strategy", i[0], feature_info_names, vbt_indicator.output_names)
			
			# add feature data
			for i,n in enumerate(vbt_indicator.output_names):
				self.add_feature(n, ret[i])
				
		return indicators

	def update_indicators(self) -> None:
		
		""" This function runs updates on all indicators, gets the results and updates the 
		features accordingly. update() must be called before to update OHLCV prior.
		"""
		
		for ind in self.indicators:
			ind.update()
			ret = ind.get()

			for i,n in enumerate(ind.output_names):
				self.add_feature(n, ret[i])				

	def update_strategies(self) -> None:

		""" This function runs updates on all strategies, gets the results and updates the 
		features accordingly. update() must be called before to update OHLCV prior.
		"""
		
		for ind in self.strategies:
			ind.update()
			ret = ind.get()

			for i,n in enumerate(ind.output_names):
				self.add_feature(n, ret[i])				
				
	def update(self, row: pd.Series | dict) -> tuple[bool, bool]:

		""" This function updates OHLCV based on new information given in row.
		
		row: New candle information, can be either pd.Series object or dict. Must include feature 
		names as defined in generic_data.
			
		Returns whether an update was performed and if it included a roll.
		A roll is a data shift once a new candle has opened.
		
		Note: row must provide the full information for the current (or new) candle. If only tick data is available,
		a candle must be aggregated from those ticks in a previous step, in order to create candle updates for
		this function.
		"""
		
		if isinstance(row, pd.core.series.Series):
			row_dict = row.to_dict()
			row_dict['date'] = row.name
		else:
			row_dict = row
			
		roll = True
	
		if len(self.data['date']):
		
			if row_dict['date'] < self.data['date'][-1]:
				# abort if outdated info comes in
				return False, False
		
			elif row_dict['date'] == self.data['date'][-1]:
				roll = False
				
		# we need to shift/roll in case will be adding new data, not updating the current candle
		if roll:
			self.roll()
		
		# in any case, new data will go into the last row
		self.data['date'][-1] = row_dict['date']
		self.data['date_l'][-1] = row_dict['date_l']
		self.data['open'][-1] = row_dict['open']
		self.data['high'][-1] = row_dict['high']
		self.data['low'][-1] = row_dict['low']
		self.data['close'][-1] = row_dict['close']
		self.data['volume'][-1] = row_dict['volume']
		self.data['cpl'][-1] = row_dict['cpl']
		
		return True, roll
		
	def roll(self):

		"""rolls all numpy arrays 1 step back for each feature name.
		We work with fixed array sizes and therefore copy the data instead
		of re-creating arrays (which np.roll() would do).
		"""
		
		for f in self.get_feature_names():
			self.data[f][0:-1] = self.data[f][1:]	