# -*- coding: utf-8 -*-

import numpy as np

class IndicatorRoot:
	
	"""
	Root class for all indicators. Mainly keeping track of all input, param and output variables
	 and additional information that may be supplied (e.g. support and resistance lines as part of kwargs)
	 
	"""
	def __init__(self, input_args, kwargs):
		
		# re-engineer input, param and output names from the corresponding vbt class
		# to use the same terminology here for numpy arrays and class attributes
		indicator_class_name = type(self).__name__
		vbt_class_name = indicator_class_name[:-1]
		vbt_class = getattr(inst, vbt_class_name)
		self.input_names = vbt_class.input_names
		self.param_names = vbt_class.param_names
		self.output_names = vbt_class.output_names

		# store additional information in the root class for potential use in indicator methods,
		# such as timeframe, timezone and generic kwargs
		self.feature_info = getattr(inst, indicator_class_name + "feature_info")
		self.length = len(input_args[0])
		self.timeframe = kwargs['timeframe']
		self.tz = kwargs['tz']
		self.kwargs = kwargs
		
		# make sure we receive correct number of input arguments
		if len(self.input_names) + len(self.param_names) != len(input_args):
			raise Exception("Wrong argumnent length for", indicator_class_name)

		# create object attributes for input and parameters
		# for easy access from indicators
		for i, f in enumerate(self.input_names):
			self.__dict__[f] = input_args[i]

		for i, f in enumerate(self.param_names):
			self.__dict__[f] = input_args[i + len(self.input_names)]
		
		# create default data arrays
		self.create_features()
	
	
	def create_features(self):
		"""
		create numpy arrays of specific length, filled with default values,
		and set the feature name as attribute for the indicator class
		"""		
		for f in self.feature_info:
			self.__dict__[f['name'] ] = np.full(self.length, f['default'] , dtype=f['type_np'] )		
		
	def get(self):
		""" return list of numpy arrays with order of indicator's output names"""
		return [self.__dict__[n] for n in self.output_names]


# avoid circular import
import indicators as inst
	