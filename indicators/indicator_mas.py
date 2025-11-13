

from .indicator_root import IndicatorRoot
from .indicator_utils import indicator_strategy_vbt_caller
import numpy as np
import talib
import vectorbtpro as vbt

# Feature definition, including types for creating np arrays and default values
# e9 stands for EMA with period of 9, s for SMA
IndicatorMAs_feature_info = [
			{'name':'e9', 'type':float, 'type_np':np.float64, 'default':np.nan},
			{'name':'e20', 'type':float, 'type_np':np.float64, 'default':np.nan},
			{'name':'e50', 'type':float, 'type_np':np.float64, 'default':np.nan},
			{'name':'e100', 'type':float, 'type_np':np.float64, 'default':np.nan},
			{'name':'e200', 'type':float, 'type_np':np.float64, 'default':np.nan},
			{'name':'s9', 'type':float, 'type_np':np.float64, 'default':np.nan},
			{'name':'s20', 'type':float, 'type_np':np.float64, 'default':np.nan},
			{'name':'s30', 'type':float, 'type_np':np.float64, 'default':np.nan},
			{'name':'s50', 'type':float, 'type_np':np.float64, 'default':np.nan},
			{'name':'s100', 'type':float, 'type_np':np.float64, 'default':np.nan},
			{'name':'s200', 'type':float, 'type_np':np.float64, 'default':np.nan},
		]
	
class IndicatorMAs_(IndicatorRoot):

	"""Indicator to calculate moving averages (both simple and exponential) for a set of standard periods based on talib library"""
	
	def __init__(self, input_args, kwargs):
		super().__init__(input_args, kwargs)

	def prepare(self):
		self.e9 = talib.EMA(self.close, 9)
		self.e20 = talib.EMA(self.close, 20)
		self.e50 = talib.EMA(self.close, 50)
		self.e100 = talib.EMA(self.close, 100)
		self.e200 = talib.EMA(self.close, 200)

		self.s9 = talib.SMA(self.close, 9)
		self.s20 = talib.SMA(self.close, 20)
		self.s30 = talib.SMA(self.close, 30)
		self.s50 = talib.SMA(self.close, 50)
		self.s100 = talib.SMA(self.close, 100)
		self.s200 = talib.SMA(self.close, 200)

	def update(self):
		self.e9[-1] = talib.EMA(self.close, 9)[-1]
		self.e20[-1] = talib.EMA(self.close, 20)[-1]
		self.e50[-1] = talib.EMA(self.close, 50)[-1]
		self.e100[-1] = talib.EMA(self.close, 100)[-1]
		self.e200[-1] = talib.EMA(self.close, 200)[-1]

		self.s9[-1] = talib.SMA(self.close, 9)[-1]
		self.s20[-1] = talib.SMA(self.close, 20)[-1]
		self.s30[-1] = talib.SMA(self.close, 30)[-1]
		self.s50[-1] = talib.SMA(self.close, 50)[-1]
		self.s100[-1] = talib.SMA(self.close, 100)[-1]
		self.s200[-1] = talib.SMA(self.close, 200)[-1]

# VBT class for indicator, holding the input, param and output definitions
IndicatorMAs = vbt.IF(

	class_name='IndicatorMAs',
	short_name='indmas',
	input_names=['close'],
	param_names=[],
	output_names=['e9','e20','e50','e100','e200','s9','s20','s30','s50','s100','s200'],

).with_apply_func(

	indicator_strategy_vbt_caller, 
	takes_1d=True
)




