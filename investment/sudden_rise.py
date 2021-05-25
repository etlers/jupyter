"""
    급등주 추출 & 슬랙으로 전송
"""
import pymysql
import pandas as pd
import datetime, os, time
from pymysql.connections import DEFAULT_CHARSET
import requests
import threading
import yaml
import send_slack_message as ssm

# current date and time
now_dtm = datetime.datetime.now()
run_dt = now_dtm.strftime("%Y-%m-%d")

def get_qry_data_list(qry):
    # MySQL Connection 연결
    conn = pymysql.connect(
        host='localhost', 
        user='etlers', 
        password='wndyd',
        db='stocks', 
        charset='utf8')

    # Connection 으로부터 Cursor 생성
    curs = conn.cursor()
    # SQL문 실행
    curs.execute(qry)
    # 데이타 Fetch
    fetched_list = curs.fetchall()
    # Connection 닫기
    conn.close()
    
    return fetched_list

# 5일 범위 일자 가져오기
def get_min_max_dt():
    sql = """
        SELECT DATE_FORMAT(deal_dt, '%Y.%m.%d')
             , rank() over(ORDER BY deal_dt DESC) AS rnk
          FROM (SELECT distinct deal_dt
                  FROM jongmok_day_sum
                 ORDER BY deal_dt desc
                 LIMIT 5) T1
    """
    # 1: To, 5: From, 2: Pre
    list_dt_rank = get_qry_data_list(sql)

    return list_dt_rank

list_dt_rank = get_min_max_dt()
from_dt = list_dt_rank[len(list_dt_rank)-1][0]
to_dt = list_dt_rank[0][0]
pre_dt = list_dt_rank[1][0]

list_day_sum_cols = [
    "deal_dt", 
    "jongmok_cd", 
    "jongmok_nm", 
    "end_price", 
    "gap", 
    "preday_rt", 
    "start_price", 
    "high_price", 
    "low_price", 
    "deal_amount", 
    "forgn_poss_rt", 
    "com_deal", 
    "forgn_deal",
]

list_cols_day = [
    "jongmok_cd",
    "jongmok_nm",
    "deal_dt",
    "end_price",
    "vs_preday_rt",
    "deal_amount",
    "forgn_poss_rt",
]


def make_rising_df():
    sql = f"""
SELECT jongmok_nm, end_price, avg_rt, gap, com_deal, forgn_deal, round(deal_rt, 0) as deal_rt
  FROM (SELECT jongmok_nm
             , t2.end_price AS end_price
             , round(AVG(preday_rt), 2) AS avg_rt
             , SUM(gap) AS gap
             , SUM(com_deal) AS com_deal
             , SUM(forgn_deal) AS forgn_deal
             , case when t3.deal_amount = 0 then 0 else round((t2.deal_amount - t3.deal_amount) / t3.deal_amount, 2) * 100 end AS deal_rt
          FROM jongmok_day_sum t1
          left outer join (SELECT jongmok_cd, end_price, deal_amount
                             FROM jongmok_day_sum 
                            WHERE deal_dt = '{to_dt}') t2
            on t1.jongmok_cd = t2.jongmok_cd
          left outer join (SELECT jongmok_cd, deal_amount
                             FROM jongmok_day_sum 
                            WHERE deal_dt = '{pre_dt}') t3
            on t1.jongmok_cd = t3.jongmok_cd
         WHERE deal_dt BETWEEN '{from_dt}' AND '{to_dt}'
         GROUP BY jongmok_nm) TT
 WHERE deal_rt between 100 AND 500
   AND avg_rt > 1.5
   AND com_deal > 50000
   AND forgn_deal > 0
 ORDER BY deal_rt desc
    """
    list_rising = get_qry_data_list(sql)
    list_rising_cols = [
        "종목",
        "종가",
        "증감율",
        "전일증가액",
        "기관",
        "전일거래증가율",        
    ]
    
    msg = f"{to_dt} - 최근 5거래일 기관 순매수 & 평균 증감율 1.5% 이상\n"
    msg += "#" * 40 + "\n"
    for col in list_rising_cols:
        msg += col + " | "
    msg = msg[:len(msg)-2]
    msg += "\n"
    msg += "#" * 40 + "\n"
    for list_row in list_rising:
        for row in list_row:
            if type(row) != str:
                msg += format(row, ",") + " | "
            else:
                msg += row + " | "
        msg = msg[:len(msg)-2]
        msg += "\n"
    ssm.send_message_to_slack(msg)
    #print(msg)

def get_jongmok_day_sum():
    # SQL문 실행
    sql = f"""
        SELECT deal_dt
             , jongmok_cd
             , jongmok_nm
             , end_price
             , gap
             , preday_rt
             , start_price
             , high_price
             , low_price
             , deal_amount
             , forgn_poss_rt
             , com_deal
             , forgn_deal
          FROM jongmok_day_sum
         WHERE deal_dt BETWEEN '{from_dt}' AND '{to_dt}'
         ORDER BY jongmok_cd, deal_dt desc
    """
    list_day_sum = get_qry_data_list(sql)    
    df_day_sum = pd.DataFrame(list_day_sum, columns=list_day_sum_cols)    
    
    return df_day_sum

# 지속적인 매수 주
def continue_buying(df_base):

    def find_target(df_continue):
        read_cnt = 0
        pre_day_forgn = 0
        pre_buy_company = 0
        
        df_target = df_continue.sort_values("deal_dt", axis=0, ascending=False).head(3)
        df_target = df_target.sort_values("deal_dt", axis=0)
        # 3일연속 기관 매수량이 늘고 외국인 보유가 늘어났다면
        for idx, row in df_target.iterrows():
            if read_cnt > 0:
                if row["forgn_poss_rt"] <= pre_day_forgn:
                    return False
                if row["buy_amount"] - row["sell_amount"] <= pre_buy_company:
                    return False
            # print(pre_day_forgn, row["forgn_amount"], inc_forgn_tf)
            pre_day_forgn = row["forgn_poss_rt"]
            pre_buy_company = row["buy_amount"] - row["sell_amount"]
            if (pre_day_forgn < 0 or pre_buy_company < 0): 
                return False
            read_cnt += 1

        return True


    df_jongmok_cd = df_base[["jongmok_cd"]].drop_duplicates()

    list_continue = []
    for idx, row in df_jongmok_cd.iterrows():
        list_temp = []
        df_filtered = df_base.loc[df_base.jongmok_cd == row["jongmok_cd"]]        
        if find_target(df_filtered):
            list_temp.append(row["jongmok_nm"])
        list_continue.append(list_temp)
    
    df_result = pd.DataFrame(list_continue, columns=["jongmok_nm"])

    return df_result


# 당일 투자자별 매수현황
def day_investor_info(now_dt):
    list_day_invest_cols = [
        "개인",
        "외인",
        "기관",
        "금융투자",
        "보험",
        "투신(사모)",
        "은행",
        "기타금융기관",
        "기금",
        "기타법인",
    ]
    result_message = ""

    qry = f"""
        SELECT PRIVATE
             , FORGN
             , COMPANY
             , FINN_INVEST
             , INSURANCE
             , PRI_FUND
             , BANK
             , ETC_FINN
             , KIGEUM
             , ETC_COMP
             , CASE WHEN DIV_CD = '01' THEN '코스피' ELSE '코스닥' END AS DIV_NM
          FROM day_invest
         WHERE DEAL_DT = '{now_dt}'
         ORDER BY DIV_CD
    """
    list_day_investor = get_qry_data_list(qry)
    
    list_idx = [1, 2, 8]    
    for list_row in list_day_investor:
        msg = ""
        buy_sum = 0
        for idx in list_idx:
            # 외국인 기관, 연기금만
            msg += list_day_invest_cols[idx] + " " + format(list_row[idx], ",") + " | "
            buy_sum += list_row[idx]
        # 거래소 구분
        if buy_sum > 0:
            div_msg = "매수 " + format(buy_sum, ",")
        else:
            div_msg = "매도 " + format(buy_sum, ",")
        result_message += list_row[10] + "] " + msg + div_msg + "\n"
    result_message = result_message.rstrip("\n")
    
    return result_message + "\n" + "#" * 40

# 급등 주 추출
def sudden_rising(df_base, check_dt):

    list_result = []
    hing_inc_cols = [
        "jongmok_nm",
        "급등률",
        "종가",
        "거래량",
        "외국인비율",
    ]
    
    # 전일대비 거래량 300% 증가, 상승폭이 10% 이상, 금액이 10,000원 이상
    def find_target(df_base):
        
        deal_amount = 0
        end_price = 0
        calc_rt = 0.0
        for idx, row in df_base.iterrows():
            if deal_amount > 0:
                try:
                    calc_rt = ((deal_amount - row["deal_amount"]) / row["deal_amount"]) * 100
                except:
                    calc_rt = 0.0
                if calc_rt > 300.0:
                    list_temp = []
                    list_temp.append(row["jongmok_nm"])
                    list_temp.append(round(calc_rt, 2))
                    list_temp.append(end_price)
                    list_temp.append(deal_amount)
                    list_temp.append(row["forgn_poss_rt"])
                    list_result.append(list_temp)
            deal_amount = row["deal_amount"]
            end_price = row["end_price"]

    list_sudden_cd = []
    for idx, row in df_base.iterrows():
        if (str(row.deal_dt) == check_dt and row.preday_rt >= 10.0 and row.end_price >= 10000):
            list_sudden_cd.append(row.jongmok_cd)
    
    list_sudden_cd = list(set(list_sudden_cd))
    for row in list_sudden_cd:
        df_filtered = df_base.loc[df_base.jongmok_cd == row]
        find_target(df_filtered)

    df_result = pd.DataFrame(list_result, columns=hing_inc_cols)
    df_result = df_result.sort_values("급등률", axis=0, ascending=False)
    
    return df_result

def execute():
    
    df_base = get_jongmok_day_sum()
    # 급등 종목. 전일 대비 10% 이상, 거래량 300% 이상, 종가 1만원 이상
    df_sudden = df_base[df_base["deal_dt"].astype(str) >= pre_dt.replace(".","-")]
    df_sudden = sudden_rising(df_sudden, to_dt.replace(".","-"))
    # 지속적인 매수 증가. 최근 5일
    # df_continue = df_base.loc[df_base.deal_dt.astype(str) >= from_dt]
    # df_continue = continue_buying(df_continue)
    
    """    
    df_continue = df_continue.fillna(0)
    # 급등하는 종목
    df_sudden = sudden_rising()
    df_sudden = df_sudden.fillna(0)
    # 두 종목 합치기
    df_result = pd.merge(
        df_continue,
        df_sudden,
        on='jongmok_nm', 
        how='outer', 
        indicator=True
    )
    df_result = df_result.sort_values(by=["_merge","forgn_poss_rt"])
    df_result.to_csv("./csv/sudden_rising_" + run_dt.replace("-", "") + ".csv", encoding="utf-8-sig", index=False)
    list_found = []
    list_found_cols = [
        "종목명", "종가", "거래량", "급등률", "외국인비율", "구분"
    ]
    for idx, row in df_result.iterrows():
        list_temp = []
        list_temp.append(row["jongmok_nm"])
        if row["_merge"] == "left_only":
            if (int(row["end_price"]) == 0 or int(row["end_price"]) > 30000): continue
            list_temp.append(int(row["end_price"]))
        else:
            if (int(row["종가"]) == 0  or int(row["종가"]) > 30000): continue
            list_temp.append(int(row["종가"]))
        list_temp.append(row["거래량"])
        list_temp.append(row["급등률"])
        if row["_merge"] == "left_only":
            list_temp.append(row["forgn_poss_rt"])
        else:
            list_temp.append(row["외국인비율"])
        list_temp.append(row["_merge"])
        list_found.append(list_temp)
    # print(list_found)
    df_found = pd.DataFrame(list_found, columns=list_found_cols)
    df_found.to_csv("./csv/found_jongmok_" + run_dt.replace("-", "") + ".csv", encoding="utf-8-sig", index=False)
    """
    # 최종 결과 슬랙으로 전송하기 위한 문자열 생성
    result_message = "종목명 | 급등률 | 종가 | 거래량 | 외인보유" + "\n"
    result_message += "#" * 40 + "\n"
    for idx, row in df_sudden.iterrows():
        result_message += row.jongmok_nm + ". " + format(row.급등률, ",") + "% | " + format(row.종가, ",") + " | " + format(row.거래량, ",") + " | " + format(row.외국인비율, ",") + "%" + "\n"
    
    # 당일 투자자별 매수현황
    result_investor = day_investor_info(to_dt)

    return result_investor + "\n" + result_message
    

if __name__ == "__main__":
    make_rising_df()
    result_message = execute()
    print(result_message)
    # 생성한 문자 슬랙으로 전송
    if len(result_message) > 0:
        # 최종 슬랙으로 뉴스 헤드라인 던지기
        ssm.send_message_to_slack(result_message)