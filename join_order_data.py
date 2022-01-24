import pandas as pd
from tkinter import Tk
from tkinter.filedialog import askopenfilename, asksaveasfilename

Tk().withdraw()

print('>> Choose orders file:')
orders_file = askopenfilename(title='Choose orders file')
print('>> Choose branches file:')
branches_file = askopenfilename(title='Choose branches file')


if '.csv' not in orders_file or '.csv' not in branches_file:
	print('Files must be CSV. Process stopped.')	
else:
	orders_df = pd.read_csv(orders_file)
	print(f'Orders: {orders_df.shape[0]} distinct orders.')
	branches_df = pd.read_csv(branches_file)
	print(f'Branches: {branches_df.shape[0]} distinct branches.')
	
	br_cols = ['branch_id','branch','br_lng','br_lat']
	cubr_cols = ['store_id','store'] + br_cols

	# 1. Merge through customer_branch_id
	cubr_merge = pd.merge(orders_df, branches_df[cubr_cols], left_on='customer_branch_id', right_on='branch_id')
	cubr_rename_cols = {col:name for (col,name) in zip(br_cols, ['cu_'+col for col in br_cols])}
	cubr_merge.rename(columns=cubr_rename_cols, inplace=True)

	# 2. Merge through shopper_branch_id
	shbr_merge = pd.merge(cubr_merge, branches_df[br_cols], left_on='shopper_branch_id', right_on='branch_id')
	shbr_rename_cols = {col:name for (col,name) in zip(br_cols, ['sh_'+col for col in br_cols])}
	shbr_merge.rename(columns=shbr_rename_cols, inplace=True)

	print('>> Choose save location:')
	save_file = asksaveasfilename(defaultextension='.csv', title='Choose save filename:')
	
	try:
		shbr_merge.to_csv(save_file, index=False)
		print('Order saved.')
	except:
		print('There was a problem. Try again.')
