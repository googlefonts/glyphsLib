import openstep_plist
from functools import partial

plist_to_dict = openstep_plist.load
dict_to_plist = partial(openstep_plist.dumps, indent=0)
