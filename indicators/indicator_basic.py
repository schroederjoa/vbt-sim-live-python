

from indicator_root import IndicatorRoot
from indicator_utils import indicator_strategy_vbt_caller
import numpy as np
import pandas as pd
import vectorbtpro as vbt
import vectorbtpro_helpers as vbth

def find_runs(x):
    """Find runs of consecutive items in an array."""

    # ensure array
    x = np.asanyarray(x)
    if x.ndim != 1:
        raise ValueError('only 1D array supported')
    n = x.shape[0]

    # handle empty array
    if n == 0:
        return np.array([]), np.array([]), np.array([])

    else:
        # find run starts
        loc_run_start = np.empty(n, dtype=bool)
        loc_run_start[0] = True
        np.not_equal(x[:-1], x[1:], out=loc_run_start[1:])
        run_starts = np.nonzero(loc_run_start)[0]

        # find run values
        run_values = x[loc_run_start]

        # find run lengths
        run_lengths = np.diff(np.append(run_starts, n))

        return run_values, run_starts, run_lengths

# Feature definition, including types for creating np arrays and default values
IndicatorBasic_feature_info = [
	{'name':'body_high', 'type':float, 'type_np':np.float64, 'default':np.nan},
	{'name':'body_low', 'type':float, 'type_np':np.float64, 'default':np.nan},
	{'name':'body', 'type':float, 'type_np':np.float64, 'default':np.nan},
	{'name':'range', 'type':float, 'type_np':np.float64, 'default':np.nan},
	{'name':'wick_high', 'type':float, 'type_np':np.float64, 'default':np.nan},
	{'name':'wick_low', 'type':float, 'type_np':np.float64, 'default':np.nan},
	{'name':'wick_high_pct', 'type':float, 'type_np':np.float64, 'default':np.nan},
	{'name':'wick_low_pct', 'type':float, 'type_np':np.float64, 'default':np.nan},
	
	{'name':'date_hm', 'type':int, 'type_np':np.int_, 'default':0},
	{'name':'date_tz_i', 'type':int, 'type_np':np.int_, 'default':0},
	{'name':'ext', 'type':bool, 'type_np':np.bool_, 'default':False},
	{'name':'pre', 'type':bool, 'type_np':np.bool_, 'default':False},
	{'name':'date_tz_d', 'type':int, 'type_np':np.int_, 'default':0},
	{'name':'date_tz_dl', 'type':int, 'type_np':np.int_, 'default':0},			

	{'name':'col', 'type':int, 'type_np':np.int_, 'default':0},			
	{'name':'num_col', 'type':int, 'type_np':np.int_, 'default':0},			
]
		
class IndicatorBasic_(IndicatorRoot):

	""" Indicator that calculates basic features that are required by many other indicators and strategies."""
	
	def __init__(self, input_args, kwargs):
		super().__init__(input_args, kwargs)
	
	def prepare(self):
		
		# body levels, size and overall candle size
		self.body_high = np.maximum(self.open, self.close)
		self.body_low = np.minimum(self.open, self.close)
		self.body = self.body_high - self.body_low
		self.range = np.maximum(self.high - self.low, 0.00000001)
		
		# wich lenght as values and in percent
		self.wick_high = self.high - self.body_high
		self.wick_low = self.body_low - self.low
		self.wick_high_pct = self.wick_high / self.range*100.0
		self.wick_low_pct = self.wick_low / self.range*100.0
			
		# extdatanew class (live) will deliver a numpy array, while vbt.data (simulation) will deliver a datetimeindex , tz-aware
		if isinstance(self.date, np.ndarray):		
			t = pd.DatetimeIndex(self.date, tz='utc').tz_convert(self.tz)
		else:
			t = self.date

		# int value showing the candles timestamp as time of day, e.g. 930 for 09:30
		# if we dont do np.array() we get "Index does not support mutable operations" later during update()
		# this will ensure that we do not have a DatetimeIndex anymore, which would be immutable
		hm = t.hour*100 + t.minute
		self.date_hm = np.array(hm, dtype=np.int_) 

		# index of candle in seconds for current day			
		tzi = t.hour*3600 + t.minute * 60 + t.second
		self.date_tz_i = np.array(tzi, dtype=np.int_)

		# whether candle is in extended hours or pre market hours
		if self.timeframe.is_intraday():
			self.ext = (tzi < 34200) | (tzi >= 57600)
			self.pre = (tzi < 34200)

		#print(self.timeframe.is_intraday(), self.ext)

		# index of the current day with respect to Unix Epoch
		tl = pd.DatetimeIndex(self.date_l)
		self.date_tz_d = vbth.get_unix_day_from_datetime(t.tz_localize(None))	
		self.date_tz_dl = vbth.get_unix_day_from_datetime(tl.tz_localize(None))

		# candle color as 1 (green) or -1 (red)
		self.col[self.close > self.open] = 1
		self.col[self.close < self.open] = -1
		
		# number of consecutive colors in a row
		run_lengths = find_runs(self.col)[2]
		self.num_col = np.array([i+1 for r in run_lengths for i in range(r)])

	def update(self):
		
		self.body_high[-1] = max(self.open[-1], self.close[-1]) #np.maximum(self.open, self.close)
		self.body_low[-1] = min(self.open[-1], self.close[-1]) # np.minimum(self.open, self.close)
		self.body[-1] = self.body_high[-1] - self.body_low[-1]
		self.range[-1] = max(self.high[-1] - self.low[-1], 0.00000001) # np.maximum(self.high - self.low, 0.00000001)
			
		self.wick_high[-1] = self.high[-1] - self.body_high[-1]
		self.wick_low[-1] = self.body_low[-1] - self.low[-1]
		self.wick_high_pct[-1] = self.wick_high[-1] / self.range[-1]*100.0
		self.wick_low_pct[-1] = self.wick_low[-1] / self.range[-1]*100.0
			
		t = pd.Timestamp(self.date[-1], tz='utc').tz_convert(self.tz)
		tzi = t.hour*3600 + t.minute * 60 + t.second

		self.date_hm[-1] = t.hour * 100 + t.minute 
		self.date_tz_i[-1] = tzi

		if self.timeframe.is_intraday():
			self.ext[-1] = (tzi < 34200) | (tzi >= 57600)
			self.pre[-1] = (tzi < 34200)

		tl = pd.Timestamp(self.date_l[-1])
		self.date_tz_d[-1] = vbth.get_unix_day_from_datetime(t.tz_localize(None))		
		self.date_tz_dl[-1] = vbth.get_unix_day_from_datetime(tl.tz_localize(None))

		self.col[-1] = 1 if self.close[-1] > self.open[-1] else -1 if self.close[-1] < self.open[-1] else 0

		if self.num_col.size > 1:
			self.num_col[-1] = self.num_col[-2] + 1 if self.col[-2] == self.col[-1] else 1
		else:
			self.num_col[-1] = 1	

# VBT class for indicator, holding the input, param and output definitions
IndicatorBasic = vbt.IF(

	class_name='IndicatorBasic',
	short_name='indbasic',
	input_names=['date','date_l','open','high','low','close'],
	param_names=[],
	output_names=['body_high','body_low','body','range','wick_high','wick_low','wick_high_pct','wick_low_pct','date_hm','date_tz_i','ext','pre','date_tz_d','date_tz_dl','col','num_col'],

).with_apply_func(

	indicator_strategy_vbt_caller, 
	takes_1d=True
)




