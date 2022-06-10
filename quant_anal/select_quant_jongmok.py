from cmath import nan
import pandas as pd
import requests
import numpy as np
import os


dict_div_var = {
    "매출액": "sales_amount",
    "영업이익": "earn",
    "당기순이익": "profit",
    "영업이익률": "earn_rt",
    "순이익률": "profit_rt",
    "ROE(지배주주)": "roe",
    "부채비율": "debt_rt",
    "당좌비율": "check_rt",
    "유보율": "retention_rt",
    "EPS(원)": "eps",
    "PER(배)": "per",
    "BPS(원)": "bps",
    "PBR(배)": "pbr",
    "주당배당금(원)": "devidend_per_stock",
    "시가배당률(%)": "devidend_prc_rt",
    "배당성향(%)": "devidend_rt"
}


def check_value_increasing(list_val):
    try:
        list_val = eval(list_val)
        if type(list_val) != list:
            return "F"
        for i, j in zip(list_val, list_val[1:]):
            if i > j:
                return "F"
        return "T"
    except:
        return "F"


def trader_flow_data(cd, pg=1):
    url = f"https://finance.naver.com/item/frgn.naver?code={cd}&page={pg}"
    headers = {
        "referer" : url,    
        "user-agent" : "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/97.0.4692.71 Safari/537.36" 
    }
    res = requests.get(url=url, headers=headers)      
    df_frgn = pd.read_html(res.text, header=[1])[2].dropna()

    df_frgn.rename(columns={"순매매량": "순매매량_기관", "순매매량.1": "순매매량_외국인"}, inplace=True)
    try:
        df_frgn["등락률"] = df_frgn["등락률"].apply(lambda X: float(X.replace("%","").replace("+","")))
        df_frgn["보유율"] = df_frgn["보유율"].apply(lambda X: float(X.replace("%","")))
        list_end_prc = list(df_frgn.sort_values(by=["날짜"])["종가"])
        list_frgn_rt = list(df_frgn.sort_values(by=["날짜"])["보유율"])
        return list_end_prc, list_frgn_rt
    except:
        return [], []


def get_bs_data(cd):
    url = f"https://finance.naver.com/item/main.naver?code={cd}"
    try:
        list_df = pd.read_html(url, encoding="euc-kr")
    except Exception as e:
        return None, None, None, None
    
    try:
        forgn_poss_rt = str(list_df[6].iloc[2][1]).strip()
    except Exception as e:
        forgn_poss_rt = None
        
    try:
        list_high_low_prc = list_df[7].iloc[1][1].split("l")
        year_high_prc = str(list_high_low_prc[0]).strip()
        year_low_prc = str(list_high_low_prc[1]).strip()
    except Exception as e:
        year_high_prc = None
        year_low_prc = None
    
    return list_df[3], year_high_prc, year_low_prc, forgn_poss_rt
    

def get_day_result(cd):
    url = f"https://finance.naver.com/item/sise.naver?code={cd}"
    list_df = pd.read_html(url, encoding="euc-kr")
    end_prc = list_df[1].iloc[0][1]
    end_vol = list_df[1].iloc[3][1]
    
    return end_prc, end_vol


dict_bs = {}

def bs_data_to_dict(cd, nm):
    df_bs_data, year_high_prc, year_low_prc, forgn_poss_rt = get_bs_data(cd)
    if df_bs_data is None:
        return -1
    
    end_prc, end_vol = get_day_result(cd)
    
    key_idx = 0
    list_index = df_bs_data.keys()
    try:
        for key in list_index:
            desc = key[0]
            if desc == "주요재무정보": continue
            if desc == "최근 분기 실적": break
            key_idx += 1
        
        dict_value = {}
        dict_value["코드"] = "A" + cd
        dict_value["종목명"] = nm
        dict_value["종가"] = int(end_prc)
        dict_value["거래량"] = int(end_vol)
        year_high_prc = int(year_high_prc.replace(",",""))
        dict_value["52주신고가"] = year_high_prc
        year_low_prc = int(year_low_prc.replace(",",""))
        dict_value["52주신저가"] = year_low_prc
        num = pd.Series([year_low_prc, year_high_prc])
        dict_value["사분위75%"] = num.quantile(.75)
        dict_value["사분위50%"] = num.quantile(.5)
        dict_value["사분위25%"] = num.quantile(.25)
        dict_value["외국인지분율"] = float(forgn_poss_rt.replace("%",""))
        for key, row in df_bs_data.iterrows():
            list_year = []
            list_quarter = []
            for idx in range(len(row)):
                try:
                    dict_div_var[row[idx]]
                    var_nm_year = row[idx] + "_년도"
                    var_nm_quater = row[idx] + "_분기"
                except:
                    val = row[idx]
                    if type(val) == str:
                        val = val.strip().replace("'","").replace("%","")
                    try:
                        val = int(val)
                    except:
                        val = np.nan
                    if idx <= key_idx:
                        list_year.append(val)
                    else:
                        list_quarter.append(val)
            
            dict_value[var_nm_year] = [x for x in list_year if np.isnan(x) == False]                  
            dict_value[var_nm_quater] = [x for x in list_quarter if np.isnan(x) == False]

        dict_bs[cd] = dict_value
    except Exception as e:
        pass


def execute():
    list_target_columns = [
        '코드', '종목명', '거래량', 
        '종가', '52주신고가', '52주신저가', '사분위75%', '사분위50%', '사분위25%', '신고가대비_종가비율', '신저가대비_종가비율', '사분위75%대비_종가비율', '사분위50%대비_종가비율', '사분위25%대비_종가비율',
        '종가_중간값', '20일중간값_종가비율', '20일사분위25%', '20일사분위25%_종가비율', '종가흐름', 
        '외국인지분율', '외국인지분율조건', '외국인지분율_중간값', '20일중간값_외국인비율', '외국인보유흐름', 
        'ROE조건', 'ROE(지배주주)_년도', 'ROE(지배주주)_분기', 
        '영업이익_증가', '당기순이익_증가',
        'PER_중간값', 'PER(배)_년도', 'PER(배)_분기', 
        'PBR_중간값', 'PBR(배)_년도', 'PBR(배)_분기',
        '매출액_년도', '매출액_분기', '영업이익_년도', '영업이익_분기', '당기순이익_년도', '당기순이익_분기', '영업이익률_년도', '영업이익률_분기', '순이익률_년도', '순이익률_분기',
        '주당배당금(원)_년도', '주당배당금(원)_분기', '시가배당률(%)_년도', '시가배당률(%)_분기', '배당성향(%)_년도', '배당성향(%)_분기', 
        '부채비율_년도', '부채비율_분기', '당좌비율_년도', '당좌비율_분기', '유보율_년도', '유보율_분기', 'EPS(원)_년도', 'EPS(원)_분기', 'BPS(원)_년도', 'BPS(원)_분기', 
    ]
    # Balace Sheet
    df_stock_list = pd.read_csv("stock_list.csv", encoding="utf-8-sig")
    for row in df_stock_list.values:
        bs_data_to_dict(row[1], row[3])
        
    df_result = pd.DataFrame.from_dict(dict_bs, orient='index')
    df_result["ROE조건"] = df_result["ROE(지배주주)_년도"].apply(
        lambda X: np.where(np.mean(X) > 15.0, "T", "F")
    )
    df_result["외국인지분율조건"] = df_result["외국인지분율"].apply(
        lambda X: np.where(float(X) > 5.0, "T", "F")
    )
    df_result["신고가대비_종가비율"] = round(df_result["종가"] / df_result["52주신고가"] * 100, 2)
    df_result["신저가대비_종가비율"] = round(df_result["종가"] / df_result["52주신저가"] * 100, 2)
    df_result["사분위75%대비_종가비율"] = round(df_result["종가"] / df_result["사분위75%"] * 100, 2)
    df_result["사분위50%대비_종가비율"] = round(df_result["종가"] / df_result["사분위50%"] * 100, 2)
    df_result["사분위50%대비_종가비율"] = round(df_result["종가"] / df_result["사분위25%"] * 100, 2)
    df_result["PER_중간값"] = df_result["PER(배)_년도"].apply(lambda X: np.median(X))
    df_result["PBR_중간값"] = df_result["PBR(배)_년도"].apply(lambda X: np.median(X))

    # ROE 평균 15% 이상이면서 외국인 지분율이 5% 이상이고 사분위수 25%의 85% 아래인 종가 5천원 초과 종목
    df_target = df_result[
        (df_result["종가"] > 5000) & 
        (df_result["ROE조건"] == "T") & 
        (df_result["외국인지분율조건"] == "T")
    ]
    # 영업이익_분기, 당기순이익_분기 두 값이 계속 증가를 했는지 여부
    df_target["영업이익_증가"] = df_target["영업이익_분기"].apply(lambda X: check_value_increasing(str(X)))
    df_target["당기순이익_증가"] = df_target["당기순이익_분기"].apply(lambda X: check_value_increasing(str(X)))    
    # Foreigner and closing prices in the last 20 days
    dict_flow = {}
    for cd in df_target["코드"]:
        list_end_prc, list_frgn_rt = trader_flow_data(cd.replace("A", ""))
        dict_flow[cd] = [list_end_prc, list_frgn_rt]

    df_target["종가흐름"] = df_target["코드"].apply(lambda X: dict_flow[X][0])
    df_target["외국인보유흐름"] = df_target["코드"].apply(lambda X: dict_flow[X][1])
    df_target["종가_중간값"] = df_target["종가흐름"].apply(lambda X: int(np.mean(eval(str(X)))))
    df_target["20일중간값_종가비율"] = round(df_target["종가"] / df_target["종가_중간값"] * 100, 2)
    df_target["20일사분위25%"] = df_target["종가흐름"].apply(lambda X: int(pd.Series(eval(str(X))).quantile(.25)))
    df_target["20일사분위25%_종가비율"] = round(df_target["종가"] / df_target["20일사분위25%"] * 100, 2)
    df_target["외국인지분율_중간값"] = df_target["외국인보유흐름"].apply(lambda X: round(np.mean(eval(str(X))), 2))
    df_target["20일중간값_외국인비율"] = round(df_target["외국인지분율"] / df_target["외국인지분율_중간값"] * 100, 2)

    df_target[list_target_columns].to_csv("bs_target.csv", encoding="utf-8-sig", index=False)

    return df_target[list_target_columns]