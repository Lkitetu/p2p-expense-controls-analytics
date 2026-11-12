"""Recomputes every figure quoted in exception_memo.md from the output tables and writes a validation log.
Run from the project root: python3 scripts/validate_memo.py"""
import json, pandas as pd

O = 'output/'
h = json.load(open(O + 'headline.json'))
f = pd.read_csv(O + 'fact_payments.csv', dtype={'voucher': str, 'po': str}, usecols=['voucher', 'date', 'dept', 'vendor', 'path', 'amount'])
ex = pd.read_csv(O + 'exceptions.csv', dtype={'voucher': str})
summ = pd.read_csv(O + 'summary_by_test.csv').set_index('test')
splits = pd.read_csv(O + 'split_purchase_clusters.csv')
rec = pd.read_csv(O + 'recurring_direct_vouchers.csv')
conc = pd.read_csv(O + 'supplier_concentration.csv')
ben = pd.read_csv(O + 'benford_by_department.csv')
mon = pd.read_csv(O + 'monthly_spend.csv').set_index('month')['paid_$M']

M = lambda x: round(x / 1e6, 1)
pairs = ex[ex.test == 'T1 Duplicate - pair']
regents = f[f.vendor.str.startswith('REGENTS OF THE UNIV') & (f.amount == 21646221.0)]
big10 = conc[conc.spend >= 10e6]; hi = big10[big10.HHI > 2500]
siemens = conc[conc.category == 'Automotive & Other Vehicles'].iloc[0]
mck = conc[conc.category == 'Pharmaceutical'].iloc[0]

flagged = ex.drop_duplicates('voucher')
rows = []
def check(claim, memo_value, recomputed):
    rows.append((claim, memo_value, recomputed, '✓' if str(memo_value) == str(recomputed) else '✗ MISMATCH'))

check('In-scope vouchers', '443,596', f'{len(f):,}')
check('In-scope paid ($B)', '8.83', f'{f.amount.sum()/1e9:.2f}')
check('Flagged vouchers', '23,277', f'{flagged.voucher.nunique():,}')
check('Flagged share of positive vouchers (%)', '5.8', f'{100*flagged.voucher.nunique()/(f.amount>0).sum():.1f}')
check('Flagged amount ($M)', '367.8', f'{M(flagged.amount.sum())}')
check('Tier A duplicate pairs', '2,708', f'{len(pairs):,}')
check('Tier A amount ($M)', '84.2', f'{M(pairs.amount.sum())}')
check('Regents $21,646,221 vouchers posted same day (pairs)', '2', f'{int((regents.groupby("date").size() >= 2).sum())}')
check('Regents same-day dates', '2025-04-02, 2025-05-21', ', '.join(regents.groupby('date').size().loc[lambda s: s >= 2].index))
check('Recurring direct-voucher relationships', '145', f'{len(rec)}')
check('Recurring direct-voucher amount ($M)', '51.6', f'{M(rec.paid.sum())}')
check('Richmond Area Multi-Services months / $M', '12 / 7.3', f"{int(rec.iloc[0].months)} / {M(rec.iloc[0].paid)}" if rec.iloc[0].vendor.startswith('RICHMOND') else 'n/a')
cb = rec[rec.vendor == 'CityBase Inc.'].iloc[0]
check('CityBase months / $M', '12 / 4.2', f'{int(cb.months)} / {M(cb.paid)}')
check('Split clusters', '460', f'{len(splits)}')
check('Split amount ($M)', '17.4', f'{M(splits.combined_amount.sum())}')
sd = splits.groupby('dept').size()
check('Split clusters DPH / MTA / ADM', '133 / 85 / 80', f"{sd['DPH']} / {sd['MTA']} / {sd['ADM']}")
check('T1 batch vouchers / $M', '3,701 / 87.0', f"{int(summ.loc['T1 Duplicate - batch','vouchers']):,} / {M(summ.loc['T1 Duplicate - batch','amount'])}")
check('T2 near-duplicate vouchers / $M', '2,992 / 114.1', f"{int(summ.loc['T2 Near-duplicate','vouchers']):,} / {M(summ.loc['T2 Near-duplicate','amount'])}")
check('T3 split vouchers', '6,280', f"{int(summ.loc['T3 Split purchase','vouchers']):,}")
check('T4 recurring vouchers', '7,735', f"{int(summ.loc['T4 Recurring direct voucher','vouchers']):,}")
check('T5 round-dollar vouchers / $M', '297 / 18.3', f"{int(summ.loc['T5 Round-dollar (non-contract)','vouchers'])} / {M(summ.loc['T5 Round-dollar (non-contract)','amount'])}")
oc = f[f.path == 'On contract'].amount.sum() / f.amount.sum()
check('On-contract share (%)', '90.4', f'{100*oc:.1f}')
check('Off-contract $M / share %', '845 / 9.6', f"{f[f.path!='On contract'].amount.sum()/1e6:.0f} / {100*(1-oc):.1f}")
check('PO no contract / direct voucher ($M)', '459 / 386', f"{f[f.path=='PO, no contract'].amount.sum()/1e6:.0f} / {f[f.path=='Direct voucher (no PO)'].amount.sum()/1e6:.0f}")
check('Concentrated categories / $M', '15 / 956', f'{len(hi)} / {hi.spend.sum()/1e6:.0f}')
check('Siemens share of Automotive (%, $M)', '78, 177', f'{100*siemens.top1_share:.0f}, {siemens.spend/1e6:.0f}')
check('McKesson share of Pharmaceutical (%, $M)', '63, 139', f'{100*mck.top1_share:.0f}, {mck.spend/1e6:.0f}')
check('Benford overall MAD', '0.0025', f"{h['benford_overall_MAD']}")
check('Benford nonconforming departments', '9', f"{(ben.conformity=='Nonconformity').sum()}")
reg = ben[ben.dept == 'REG'].iloc[0]
check('Elections MAD / overused digit', '0.13 / 2', f'{reg.MAD:.2f} / {int(reg.most_overused_digit)}')
check('June vs Jul–May average (%)', '-22', f"{100*(mon['2025-06']/mon.drop('2025-06').mean()-1):.0f}")
p100 = pairs[pairs.amount >= 100_000]
check('Tier A pairs >= $100K / $M', '62 / 64.0', f'{len(p100)} / {M(p100.amount.sum())}')

# Recreation & Park June spike recomputed from the fact table
fi = f[(f.date >= '2024-07-01') & (f.date <= '2025-06-30') & (f.dept == 'REC')]
jun = fi[fi.date.str.startswith('2025-06')].amount.sum(); rest = fi[~fi.date.str.startswith('2025-06')].amount.sum() / 11
check('Recreation & Park June vs average (%)', '+89', f'{100*(jun/rest-1):+.0f}')

# Direct-voucher share claim: 'half of all in-scope direct-voucher spend' (test-4 scope excludes public/financial payees)
dvs = h['direct_voucher_test4_scope_$M']
check('Recurring share of direct-voucher spend (memo: "half")', '50%', f'{100*rec.paid.sum()/1e6/dvs:.0f}%')

table = pd.DataFrame(rows, columns=['Claim in memo', 'Memo value', 'Recomputed', 'Match'])
md = table.to_markdown(index=False)
memo = open('exception_memo.md').read()
start = memo.index('## Validation log')
memo = memo[:start] + '## Validation log\n_Generated by `scripts/validate_memo.py`. Every figure above was recomputed from the source tables._\n\n' + md + '\n'
open('exception_memo.md', 'w').write(memo)
print(table.to_string(index=False))
print('\nALL MATCH' if (table.Match == '✓').all() else '\nMISMATCHES FOUND')
