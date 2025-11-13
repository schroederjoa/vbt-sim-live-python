# -*- coding: utf-8 -*-

from .indicator_root import IndicatorRoot
from .indicator_utils import indicator_strategy_vbt_caller
import numpy as np
import talib
import vectorbtpro as vbt

# Indicator feature definition
IndicatorRSI_feature_info = [
			{'name':'rsi', 'type':float, 'type_np':np.float64, 'default':np.nan},
		]		
		
class IndicatorRSI_(IndicatorRoot):
	
	"""Indicator to calculate RSI based on talib library"""
	
	def __init__(self, input_args, kwargs):
		super().__init__(input_args, kwargs)
		
	def prepare(self):
		self.rsi = talib.RSI(self.close, self.period)
		
	def update(self):
		self.rsi[-1] = talib.RSI(self.close, self.period)[-1]

# VBT class for indicator, holding the input, param and output definitions
IndicatorRSI = vbt.IF(

	class_name='IndicatorRSI',
	short_name='indrsi',
	input_names=['close'],
	param_names=['period'],
	output_names=['rsi'],

).with_apply_func(

	indicator_strategy_vbt_caller, 
	takes_1d=True
)