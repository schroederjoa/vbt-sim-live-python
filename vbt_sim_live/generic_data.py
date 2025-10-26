# -*- coding: utf-8 -*-

from collections.abc import Callable
import datetime
import numpy as np
import pandas as pd
from .tfs import TFs
import vectorbtpro as vbt

ENABLE_DEBUG = False

# Feature definition for standard OHLCV, including types for creating np arrays and default values
# in addition, we use date_l to represent the latest timestamp of an update (where date is more like an id of that candle)
# cpl will indicate whether a candle is pending or complete (cpl=True)
ohlc_feature_info = [
	{'name':'date', 'type':datetime.datetime, 'type_np':'datetime64[ns]', 'default':np.nan},
	{'name':'date_l', 'type':datetime.datetime, 'type_np':'datetime64[ns]', 'default':np.nan},
	{'name':'open', 'type':float, 'type_np':np.float64, 'default':np.nan},
	{'name':'high', 'type':float, 'type_np':np.float64, 'default':np.nan},
	{'name':'low', 'type':float, 'type_np':np.float64, 'default':np.nan},
	{'name':'close', 'type':float, 'type_np':np.float64, 'default':np.nan},
	{'name':'volume', 'type':float, 'type_np':np.float64, 'default':np.nan},
	{'name':'cpl', 'type':bool, 'type_np':np.bool_, 'default':False}		
]

class GenericData():
	
	"""Data class that can hold either live or sim data, along with timeframe info and feature information.
	The timezone tz can be stored along with the data, but will not be used internally for date or date_l.
	It only affects the output when calling to_df or get_row_range methods of child classes.
	""" 
   
	def __init__(self, data: vbt.Data | dict, symbol: str, timeframe: TFs, tz: str, log_handler: Callable):
		self.data = data
		self.symbol = symbol
		self.timeframe = timeframe
		self.tz = tz
		self.log_handler = log_handler
		self.feature_info = []
		self.feature_names = []
		
		self.indicator_info = None
		self.strategy_info = None
		self.indicators = []
		self.strategies = []

		# populate feature info with default OHCLV info
		self.add_feature_info(ohlc_feature_info)
		

 
	@staticmethod
	def barlist_to_df(bars) -> pd.DataFrame:
		
		"""This function will make sure to convert bars object to the required format that GenericData expects."""	
		
		df = bars.to_df()
		df = df.rename(columns={'t':'date', 'tl':'date_l', 'o':'open','h':'high','l':'low','c':'close','v':'volume'})
		df = df.drop(columns=['s','y'])
		df = df.set_index('date')
		df['date_l'] = df['date_l'].values
		return bars.lst[0].s, df

	@staticmethod
	def df_ensure_format(df: pd.DataFrame) -> pd.DataFrame:
		
		"""This function will make sure to convert the given DataFrame to the required format that GenericData expects."""	
					
		#change all column names to lowercase, including index
		df = df.rename(columns={c:c.lower() for c in df.columns})
		
		if df.index.name is not None: 
			df = df.index.rename(df.index.name.lower())
			
		# default rename columns
		df = df.rename(columns={'d':'date','dl':'date','t':'date', 'tl':'date_l', 'o':'open','h':'high','l':'low','c':'close','v':'volume'})
		
		# set index if date column is found
		if 'date' in df.columns:
			df = df.set_index('date')
		
		# add cpl = "complete" column if not present
		if 'cpl' not in df.columns:
			df['cpl'] = True

		# add date_l column if not present
		if 'date_l' not in df.columns:
			df['date_l'] = df.index	
			
		# ensure proper date formats - we want 'datetime64[ns]' without timezone info
		if df['date_l'].dtype != "datetime64[ns]":
			df['date_l'] = pd.to_datetime(df['date_l'], utc=True).values

		if df.index.dtype != "datetime64[ns]":
			df.index = pd.to_datetime(df.index, utc=True).values
		
		return df

	def log(self, *text):
		if self.log_handler is not None: self.log_handler(*text)		

	def add_feature_info(self, info: list) -> None:
		
		"""Add feature infos from list. Check and raise Exception if feature name already exists"""
		
		for i in info:
			if i['name'] in self.feature_names:
				raise Exception("Feature name already exists", i['name'])
			else:
				self.log("Adding feature info", i, "to", self.timeframe)
				self.feature_info.append(i)	
				self.feature_names = [f['name'] for f in self.feature_info]
		
 
	def get_feature_info(self, name: str=None) -> list:
		
		"""Return feature info list for given name, or entire list"""		
		
		if name is None:
			return self.feature_info
		else:
			return [f for f in self.feature_info if f['name'] == name]

	def get_feature(self, feature_name: str):
		
		"""Return feature data for given name."""		
		
		raise NotImplementedError("Must override get_feature()")

	def get_feature_names(self):
		"""Return all feature names."""		
		return self.feature_names
		
	def has_feature(self, f: str) -> bool:
		
		"""Return True if feature exists."""	
		
		return f in self.get_feature_names()		    

	def get_info(self) -> dict:
		
		"""Return basic info of GenericData class and data types."""	
		
		df = self.to_df()
		
		info = {
			"Symbol": self.symbol,
			"Data DF Types": df.dtypes.to_dict(),
			"Data DF Index Types": df.index.dtype,
			"Raw dtypes": [{f['name']: self.get_dtype(f['name'])} for f in self.feature_info],
			"Timezone": self.tz,
			"Feature info": self.feature_info,
			"Timeframe": self.timeframe,
		}
		return info

	def set_indicators(self, info: dict) -> None:
		
		"""Set indicator info for the timeframe of this class.
		Example:
			
			indicator_info = {
				'm1': {
				    'IndicatorRSI': {'period': 14},
					 'IndicatorBasic': {},
					 'IndicatorMAs': {},
					 'IndicatorVWAP': {},
					}
				}
			"""	
		
		if self.timeframe.name not in info.keys():
			raise Exception("No indicator info available for timeframe", self.timeframe)
			
		self.log('Setting indicator info', info[self.timeframe.name])
		self.indicator_info = info[self.timeframe.name]

	def set_strategies(self, info: dict) -> None:
		
		"""Set strategy info for the timeframe of this class.
		Example:
			
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
		
		"""	
		
		if self.timeframe.name not in info.keys():
			raise Exception("No strategy info available for timeframe", self.timeframe)
			
		self.log('Setting strategy info', info)
		self.strategy_info = info[self.timeframe.name]

	def prepare_indicators(self, run_args: dict = {}) -> None:
		
		"""Run batch calculation of indicators."""	
		
		if self.indicator_info is None:
			raise Exception("No indicator info set for symbol, timeframe", self.symbol, self.timeframe)

		self.indicators = self.run_indicators(self.indicator_info, run_args)
		
	def prepare_strategies(self, run_args: dict = {}) -> None:
		
		"""Run batch calculation of strategies."""	

		if self.strategy_info is None:
			raise Exception("No strategy info set for symbol, timeframe", self.symbol, self.timeframe)
		
		self.strategies = self.run_indicators(self.strategy_info, run_args)

	def run_indicators(self, info: dict) -> None:
		
		"""Generic function to run indicators or strategies."""	
		
		raise NotImplementedError("Must override run_indicators()")