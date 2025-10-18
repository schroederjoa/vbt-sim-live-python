# -*- coding: utf-8 -*-

import numpy as np
import indicators as inst


def indicator_strategy_vbt_caller(*input_args, **kwargs):
	"""
	Gets called by vbt's indicator factory and creates the corresponding indicator class with _ extension. 
	It will pass VBTs arguments (input args are vbts input_names + param_names ) to the _ indicator class,
	runs data preparation and returns a list of results (np arrays) for each output_name
	"""
	class_name_ind_ = getattr(inst, kwargs['class_name'] + "_")
	ih = class_name_ind_(input_args, kwargs)	
	ih.prepare()
	return ih.get()

def get_strategy_standard_output_names(short_name):

	""" helper function to create standard strategy output names based on the strategy's short name"""
	return [short_name + "_" + n for n in ['size','limit','stop','stoploss','profit','cancel_order']]
	
def get_strategy_feature_info(short_name):

	""" helper function to supply feature information of standard strategy outputs, names based on the strategy's short name"""
	
	return [
		{'name':short_name+'_size', 'type':int, 'type_np':np.int_, 'default':0},
		{'name':short_name+'_limit', 'type':float, 'type_np':np.float64, 'default':np.nan},
		{'name':short_name+'_stop', 'type':float, 'type_np':np.float64, 'default':np.nan},
		{'name':short_name+'_stoploss', 'type':float, 'type_np':np.float64, 'default':np.nan},
		{'name':short_name+'_profit', 'type':float, 'type_np':np.float64, 'default':np.nan},
		{'name':short_name+'_cancel_order', 'type':bool, 'type_np':np.bool_, 'default':None},
	]