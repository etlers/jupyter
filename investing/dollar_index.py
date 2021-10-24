import requests
import sys
import time, datetime
from bs4 import BeautifulSoup as bs

sys.path.append("C:/Users/etlers/Documents/project/python/common")

import send_slack_message as SSM
import common_util as CU

url_index = "https://kr.investing.com/currencies/us-dollar-index"
url_currency = "https://kr.investing.com/currencies/usd-krw"


def get_soup(url):
    response = requests.get( url, headers={"User-agent": "Mozilla/5.0"} )
    soup = bs(response.text, 'html.parser')

    return soup


def make_usd_index():
    soup = get_soup(url_index)

    historical_usd_idx = soup.find("div",{"class":"clear overviewDataTable overviewDataTableWithTooltip"})
    idx = 0
    dict_usd_idx = {}
    for row in historical_usd_idx:
        row_string = str(row).strip()
        if len(row_string) == 0: continue
        idx += 1
        temp = str(row_string.split('<span class="float_lang_base_1">')[1:]).replace("['","")
        list_temp = temp.replace("</span><span class=","").split('"float_lang_base_2 bold">')
        dict_usd_idx[idx] = [list_temp[0].replace(" ",""), list_temp[1].replace("</span></div>']","")]
    
    return dict_usd_idx


def make_usd_krw():
    soup = get_soup(url_currency)

    list_usd_krw = soup.find("div",{"class":"main-current-data"})
    idx = 0
    dict_usd_krw = {}
    for row in list_usd_krw:
        row_string = str(row).strip()
        if len(row_string) == 0: continue
        idx += 1
        if idx == 1:
            dict_usd_krw[idx] = row_string.split('<div class="')[1].split(" ")[0]
        else:
            list_val = []
            for val in row_string.split("\n"):
                if "span class" not in val: continue
                list_val.append(val.split('">')[1].replace("</span>",""))
            dict_usd_krw[idx] = list_val
            
    list_usd_krw = soup.find("div",{"class":"clear overviewDataTable overviewDataTableWithTooltip"})
    for row in list_usd_krw:
        row_string = str(row).strip()
        if len(row_string) == 0: continue
        idx += 1
        temp = str(row_string.split('<span class="float_lang_base_1">')[1:]).replace("['","")
        list_temp = temp.replace("</span><span class=","").split('"float_lang_base_2 bold">')
        dict_usd_krw[idx] = [list_temp[0].replace(" ",""), list_temp[1].replace("</span></div>']","")]
    
    return dict_usd_krw


def execute(run_dtm):
    # Make Dictionary Data
    dict_usd_idx = make_usd_index()
    dict_usd_krw = make_usd_krw()
    # USD Index 52w Average
    year_avg_idx = (float(dict_usd_idx[10][1].split(" - ")[0].replace(",","")) + float(dict_usd_idx[10][1].split(" - ")[1].replace(",",""))) / 2
    # Now Index
    cur_idx = float(dict_usd_idx[4][1].replace(",",""))
    # USD KRW 52w Average
    year_avg_cur = (float(dict_usd_krw[8][1].split(" - ")[0].replace(",","")) + float(dict_usd_krw[8][1].split(" - ")[1].replace(",",""))) / 2
    # Now Currency
    now_cur = float(dict_usd_krw[2][0].replace(",",""))
    # Dollar Gap Rate
    usd_gap_rate = cur_idx / now_cur * 100
    # Dollar Gap Rate - 52w
    year_avg_usd_gap_rate = year_avg_idx / year_avg_cur * 100
    # Proper USD KRW
    proper_cur = round(cur_idx / year_avg_usd_gap_rate * 100, 2)

    line_len = 75
    print("#" * line_len)
    print("# Dollar index")
    print("#" * line_len)
    for key, val in dict_usd_idx.items():
        print(key, val)

    print("#" * line_len)
    print("# USD - KRW Currency")
    print("#" * line_len)
    for key, val in dict_usd_krw.items():
        print(key, val)

    print("#" * line_len)
    now_rate = round((now_cur / proper_cur) * 100, 2)
    result = f"{proper_cur} - [{now_cur}, {now_rate}%]"
    print(result)
    print("#" * line_len)

    slack_msg = run_dtm + "\n" + result + "\n"
    SSM.send_message_to_slack(slack_msg)


if __name__ == "__main__":
    # now_dtm = datetime.datetime.now()
    # run_dtm = now_dtm.strftime("%Y-%m-%d %H:%M:%S")
    # execute(run_dtm)
    # CU.waiting_seconds(10, "Waiting... Next Calculation")

    while True:
        now_dtm = datetime.datetime.now()
        run_dtm = now_dtm.strftime("%Y-%m-%d %H:%M:%S")
        run_hh = now_dtm.strftime("%H")
        
        if run_hh < "09":
            print("Waiting... Starting Hour")
            time.sleep(1)
            continue
        elif run_hh > "17":
            print("End Calculation for Dealing.")
            break

        execute(run_dtm)
        # every 30 minutes
        CU.waiting_seconds(1800, "Waiting... Next Calculation for Dealing")
        time.sleep(1800)