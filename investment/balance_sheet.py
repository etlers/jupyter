import pandas as pd
import datetime
import time

start = time.time()
df_jongmok = pd.read_csv("./csv/jongmok_list.csv", encoding="euc-kr")[["단축코드", "한글 종목약명"]]
df_jongmok = df_jongmok.rename(columns={"단축코드":"CD", "한글 종목약명":"NM"})

list_columns = [
    "DT", "CD", "NM", "ROE", "PER", "PBR", "PROFIT", "INCOME", "FRGN_RT",
]
list_balance = [
    "CD", "NM", "ROE", "PER", "PBR", "PROFIT", "INCOME"
]
list_poss_frgn = [
    "DT", "CD", "NM", "FRGN_RT",
]

list_result = []
dt = datetime.datetime.now().strftime("%Y-%m-%d")
# ROE 값이 기준값 이상인 것만 고른다
def get_roe_more_than_base(cd, nm):
    roe_base = 15.0
    url = f"https://finance.naver.com/item/main.naver?code={cd}"
    
    list_roe = []
    list_per = []
    list_pbr = []
    list_profit = []
    list_income = []
    
    try:
        list_df = pd.read_html(url, encoding="euc-kr")
        df_bs_sheet = list_df[3]
        
        roe = 0.0
        try:
            roe = float(df_bs_sheet.fillna(0).iloc[5].loc["최근 연간 실적", "2021.12(E)"][0])
            list_ym = ["2018.12","2019.12","2020.12","2021.12(E)"]
        except:
            roe = float(df_bs_sheet.fillna(0).iloc[5].loc["최근 연간 실적", "2021.12"][0])
            list_ym = ["2019.12","2020.12","2021.12"]
    
        if roe >= roe_base:
            for ym in list_ym:
                list_roe.append(float(df_bs_sheet.fillna(0).iloc[5].loc["최근 연간 실적", ym][0]))
                list_per.append(float(df_bs_sheet.fillna(0).iloc[10].loc["최근 연간 실적", ym][0]))
                list_pbr.append(float(df_bs_sheet.fillna(0).iloc[12].loc["최근 연간 실적", ym][0]))
                list_profit.append(int(df_bs_sheet.fillna(0).iloc[1].loc["최근 연간 실적", ym][0].replace(",", "")))
                list_income.append(int(df_bs_sheet.fillna(0).iloc[2].loc["최근 연간 실적", ym][0].replace(",", "")))
            frgn_rt = float(list_df[6][1].iloc[2].replace("%", ""))
            list_result.append([dt, "A" + cd, nm, list_roe, list_per, list_pbr, list_profit, list_income, frgn_rt])
    except:
        pass

for index, row in df_jongmok.iterrows():
    get_roe_more_than_base(str(row.CD), row.NM)

# Today's dataframe
df_now = pd.DataFrame(data=list_result, columns=list_columns)
df_now[list_balance].to_csv("./csv/balance_sheet.csv", encoding="utf-8-sig", index=False)
# Foreigner Possesion
try:
    # Extract from yesterday csv file and make dataframe
    df_pre = pd.read_csv("./csv/poss_forgn.csv", encoding="utf-8-sig")
    df_result = pd.concat([df_now[list_poss_frgn], df_pre]).drop_duplicates()
    # Save result dataframe to csv file 
    df_result.to_csv("./csv/poss_forgn.csv", encoding="utf-8-sig", index=False)
# No yeasterday data
except:
    df_now[list_poss_frgn].to_csv("./csv/poss_forgn.csv", encoding="utf-8-sig", index=False)
    
end = time.time()
print(f"Elapsed Seconds: {end - start}")