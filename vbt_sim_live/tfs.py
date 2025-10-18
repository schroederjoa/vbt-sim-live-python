# -*- coding: utf-8 -*-

from enum import Enum

class TFs(Enum):
	
	"""Timeframe class that holds names and corresponding timeframe length in seconds."""	

	m1 = 60
	m2 = 2*60
	m3 = 2*60
	m5 = 5*60
	m15 = 15*60
	m30 = 30*60
	d1 = 24*60*60
	w1 = d1*7
	M1 = d1*31
	
	def flip(self) -> str:
		"""Return name with digits and unit shifted, e.g. "m1" -> "1m" """			
		return self.name[1:len(self.name)] + self.name[0]
		
	def is_intraday(self) -> bool:
		"""True if timeframe is below one day """			
		return self.value < 24*60*60

	def is_outsideday(self) -> bool:
		"""True if timeframe is day or higher """			
		return self.value >= 24*60*60