
from .indicator_root import IndicatorRoot
from .indicator_utils import get_strategy_standard_output_names, get_strategy_feature_info, indicator_strategy_vbt_caller
import numpy as np
import vectorbtpro as vbt


class StrategyRSI_(IndicatorRoot):
	
	""" RSI strategy that takes trades based on RSI levels of two different timeframes (own timeframe, like 1m or 2m, and m5 timeframe).
	rsim5 needs to be supplied as realiged RSI signal taken from m5.
	"""
	
	def __init__(self, input_args, kwargs):
		super().__init__(input_args, kwargs)

	def prepare(self):
				
		for j in range(len(self.low)):
			#print(j)
			ret = strategy_rsi_func_single(j, self)
			for i, n in enumerate(self.output_names): self.__dict__[n][j] = ret[i]

	def update(self):
		ret = strategy_rsi_func_single(-1, self)
		for i, n in enumerate(self.output_names): self.__dict__[n][-1] = ret[i]
	
	
def strategy_rsi_func_single(i: int, obj: StrategyRSI_):
	
	""" Function to calculate strategy results for a single datapoint.
	Receives data point index and reference to Indicator object
	returns list of results, corresponding to output_names.
	"""
	
	size = 0
	limit = np.nan
	stop = np.nan
	stoploss = np.nan
	profit = np.nan
	cancel_order = False
		
	enter_trade = False
	
	# go short if both rsis above threshold_high
	if obj.rsi[i] > obj.threshold_high and obj.rsim5[i] > obj.threshold_high:
		enter_trade = True
		entry = obj.close[i]
		# stop goes above the high
		stoploss = max(obj.high[i] + 0.01, entry + obj.min_risk)
	
	# go long if both rsis below threshold low
	elif obj.rsi[i] < obj.threshold_low and obj.rsim5[i] < obj.threshold_low:
		enter_trade = True
		entry = obj.close[i]
		limit = entry
		# stop goes below the low
		stoploss = min(obj.low[i] - 0.01, entry - obj.min_risk)
		
	if enter_trade:
		risk = entry - stoploss
		size = int(obj.risk_per_trade / risk)
		limit = entry
		profit = entry + obj.profit_rr*risk
	
	return size, limit, stop, stoploss, profit, cancel_order


# VBT class for RSI strategy, holding the input, param and output definitions
StrategyRSI = vbt.IF(
	
	class_name='StrategyRSI',
	short_name='stratrsi',
	input_names=['close', 'low', 'high', 'rsi', 'rsim5'],
	param_names=['threshold_high', 'threshold_low','order_type','profit_rr', 'min_risk','risk_per_trade'],
	output_names=get_strategy_standard_output_names('stratrsi'),

).with_apply_func(

	indicator_strategy_vbt_caller, 
	takes_1d=True
)

# Strategy feature definition. Only using standard features here, but could possibly be more
StrategyRSI_feature_info = get_strategy_feature_info(StrategyRSI.short_name)
