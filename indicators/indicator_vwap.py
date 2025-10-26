

from .indicator_root import IndicatorRoot
from .indicator_utils import indicator_strategy_vbt_caller
import numpy as np
import vectorbtpro as vbt

def intervaled_cumsum(ar: np.array, sizes: np.array):
	""" Calculate the cumulative sum based on input array ar and bins given in sizes"""	
	# Make a copy to be used as output array
	out = ar.copy()
	
	# Get cumumlative values of array
	arc = ar.cumsum()

	# Get cumsumed indices to be used to place differentiated values into
	# inp array's copy
	idx = sizes.cumsum()

	# Place differentiated values that when cumumlatively summed later on would
	# give us the desired intervaled cumsum
	out[idx[0]] = ar[idx[0]] - arc[idx[0]-1]
	out[idx[1:-1]] = ar[idx[1:-1]] - np.diff(arc[idx[:-1]-1])
	return out.cumsum() 
	
def indicator_vwap_func(high, low, close, vol, date_tz_d):
	
	""" vwap formula """
	# reduce volume to avoid RuntimeWarning: overflow encountered in ulonglong_scalars
	volume = vol / 1000
	
	# calculate vwap
	sizes = np.bincount(date_tz_d)
	sizes = sizes[sizes != 0]
	vold = intervaled_cumsum(volume, sizes)
	vold[vold == 0] = 1
	
	if close is None:
		volume_price = volume*(high + low)/2 
	else:
		volume_price = volume*(high + low + close)/3 
	return intervaled_cumsum(volume_price, sizes) / vold

# Feature definition, including types for creating np arrays and default values
IndicatorVWAP_feature_info = [
			{'name':'vwap', 'type':float, 'type_np':np.float64, 'default':np.nan},
			{'name':'vwap2', 'type':float, 'type_np':np.float64, 'default':np.nan},
		]
	
class IndicatorVWAP_(IndicatorRoot):

	"""Indicator to calculate two types of VWAP
	vwap based on HLC
	vwap2 based on HL
	"""
	
	def __init__(self, input_args, kwargs):
		super().__init__(input_args, kwargs)
		
	def prepare(self):
		self.vwap = indicator_vwap_func(self.high, self.low, self.close, self.volume, self.date_tz_d)
		self.vwap2 = indicator_vwap_func(self.high, self.low, None, self.volume, self.date_tz_d)
		
	def update(self):
		self.vwap[-1] = indicator_vwap_func(self.high, self.low, self.close, self.volume, self.date_tz_d)[-1]
		self.vwap2[-1] = indicator_vwap_func(self.high, self.low, None, self.volume, self.date_tz_d)[-1]

# VBT class for indicator, holding the input, param and output definitions
IndicatorVWAP = vbt.IF(

	class_name='IndicatorVWAP',
	short_name='indvwap',
	input_names=['high','low','close','volume','date_tz_d','ext'],
	param_names=[],
	output_names=['vwap','vwap2'],

).with_apply_func(

	indicator_strategy_vbt_caller, 
	takes_1d=True
)




