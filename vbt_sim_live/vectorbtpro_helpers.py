
from datetime import datetime, timedelta, timezone
import numpy as np
import pandas as pd
import pytz

def is_last_day_of_week(last_date):

	return last_date.weekday() == 4 # Friday?

def is_last_day_of_month(last_date):
	
	start = (last_date - timedelta(weeks=8)).replace(tzinfo=None)
	end = (last_date + timedelta(weeks=5)).replace(tzinfo=None)
	
	bussiness_days_rng = pd.date_range(start, end, freq='BME', tz=pytz.timezone('UTC')).to_pydatetime()
	bussiness_days_rng = [b.date() for b in bussiness_days_rng]

	return last_date.date() in bussiness_days_rng # last_date is last business day of the month	

def get_unix_day_from_date(d):

	dt = datetime.combine(d, datetime.min.time())
	dt_zero = datetime.fromtimestamp(0, timezone.utc).replace(tzinfo=None)
	days = (dt - dt_zero).days

	# do not return an pd index object because this is not mutable
	if isinstance(days, pd.core.indexes.base.Index):
		days = np.array(days)
					
	return days
	
	
def get_unix_day_from_datetime(dt):

	#  timezone.utc is needed to give a proper 00:00, not 01:00 on 1.1.1970
	# see here https://stackoverflow.com/questions/72489169/why-does-python-datetime-timestamp0-return-1am-as-opposed-to-0000
	# remove tzinfo afterwards so that is complies with incoming non-tz-aware datetime
	
	dt_zero = datetime.fromtimestamp(0, timezone.utc).replace(tzinfo=None)
	days = (dt - dt_zero).days

	# do not return an pd index object because this is not mutable
	if isinstance(days, pd.core.indexes.base.Index):
		days = np.array(days)
					
	return days

'''	
def create_indicator_df(ind, index):

	ind_new = {}
	for k in ind.keys():
		#print(k, len(ind5[k]), type(ind5[k]))
		
		is_series = type(pd.Series()) == type(ind[k])
		if is_series:
			ind_new[k] = ind[k].values
		else:
			ind_new[k] = ind[k]

	df = pd.DataFrame(ind_new)
	return df.set_index(index)

# takes a multi-column/multi index dataframe and reduces it 
# based on the dict values provided in column_value_dict
def reduce_by_column_value(df, column_value_dict):

	if isinstance(df, pd.DataFrame):
		nlevels = df.columns.nlevels
		column_name = df.columns.get_level_values(0).name
		if column_name not in column_value_dict.keys():
			print("Missing key", column_name)
			return df
		value = column_value_dict[column_name]
		if nlevels == 1:
			# last level reached, flatten this level
			df = df[value]
		else:
			# more levels to come, step one level lower
			df = reduce_by_column_value(df[value], column_value_dict)

	return df


def combine_ohlcv_indicators(dfin, indicators, return_dict = True):
	
	df = pd.concat([dfin.copy(), pd.DataFrame(indicators).set_index(dfin.index)], axis=1)
	
	lastindex = np.where(np.isnan(df['Open']))[0][0] #-1
	
	df = df[:lastindex]
	
	if return_dict:
		df = df.reset_index()
		df = df.rename(columns={'index':'Date'})
		df['Date'] = (df['Date'] - pd.Timestamp("1970-01-01", tz='utc')) // pd.Timedelta('1s')
		df['Date_l'] = (df['Date_l'] - pd.Timestamp("1970-01-01", tz='utc')) // pd.Timedelta('1s')
		#print(df.dtypes)
		return df.to_dict("records")
	else:
		return df[:lastindex]
'''

def get_target_index(source_index, timeframe):
	
	freq_seconds = timeframe.value
	
	date_base = (source_index.astype(np.int64) / 10**9)
	date_base = date_base.astype(np.int64) // freq_seconds
	date_base = np.unique(date_base)
	
	target_index = pd.to_datetime(date_base * freq_seconds, unit='s', origin='unix', utc=True)
	target_index = target_index.tz_convert(tz=source_index.tzinfo)
		
	return target_index
	

'''
def resample_to_first_occurrence(source_series, timeframe):
	
	print("incoming", source_series)

	freq_seconds = timeframe.value

	date_base = ((source_series.index.astype(np.int64) + timeframe.value) / 10**9)
	date_base = (date_base.astype(np.int64) // freq_seconds)
	
	new_series = pd.Series(index=source_series.index, data=date_base)
	print("new series", new_series)

	new_series = new_series.drop_duplicates(keep='first')
	
	print("new series", new_series)
	
	idx_diff = source_series.index.difference(new_series.index, sort=False)
	#print("index diff", idx_diff)
	
	final_series = source_series.copy()
	
	#print("single", final_series.loc[[idx_diff[0]]])
	
	final_series.loc[idx_diff] = False
	
	#print("final_series", final_series)
	
	return final_series
'''

		
		