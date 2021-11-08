import requests
import sys
import time, datetime
from bs4 import BeautifulSoup as bs

sys.path.append("C:/Users/etlers/Documents/project/python/common")

import send_slack_message as SSM
import common_util as CU

url_index = "https://kr.investing.com/currencies/us-dollar-index"
url_currency = "https://kr.investing.com/currencies/usd-krw"
url_kodex = "https://finance.naver.com/"

line_len = 75

def get_soup(url):
    response = requests.get( url, headers={"User-agent": "Mozilla/5.0"} )
    soup = bs(response.text, 'html.parser')

    return soup


def make_usd_index():
    soup = get_soup(url_index)

    historical_usd_idx = soup.find("div",{"class":"clear overviewDataTable overviewDataTableWithTooltip"})

    if historical_usd_idx is None: return -1

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

    if list_usd_krw is None: return -1

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


def make_kodex_index():
    soup = get_soup(url_kodex)

    kodex_idx = soup.find("div",{"class":"dsc_area dsc_area2"})

    if kodex_idx is None: return -1

    idx = 0
    dict_kodex_idx = {
        "개인": 0,
        "외국인": 0,
        "기관": 0,
    }

    for row in str(kodex_idx).split("\n"):
        row_string = str(row).strip().replace(",","").replace("+","")
        if len(row_string) == 0: continue
        idx += 1
        if idx == 7:
            dict_kodex_idx["개인"] = int(row_string)
        elif idx == 14:
            dict_kodex_idx["외국인"] = int(row_string)
        elif idx == 21:
            dict_kodex_idx["기관"] = int(row_string)

    return dict_kodex_idx


def execute(run_dtm):
    # Make Dictionary Data
    dict_usd_idx = make_usd_index()
    dict_usd_krw = make_usd_krw()

    if dict_usd_idx == -1 or dict_usd_krw == -1: return 1

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
    # Kodex
    dict_kodex_idx = make_kodex_index()
    total_amount = 0
    buy_amount = 0
    for row in dict_kodex_idx.values():
        total_amount += row
        if row > 0:
            buy_amount += row
    forgn_rt = round((dict_kodex_idx["외국인"] / buy_amount) * 100, 2)
    forgn_gap = dict_kodex_idx["외국인"] - dict_kodex_idx["개인"]

    now_rate = round((now_cur / proper_cur) * 100, 2)
    now_cur = '{:.2f}'.format(round(now_cur, 2))
    now_rate = '{:.2f}'.format(round(now_rate, 2))
    forgn_rt = '{:.2f}'.format(round(forgn_rt, 2))
    result = f"{proper_cur} - [{now_cur}, {now_rate}%] [{forgn_rt}%, {forgn_gap}, {buy_amount}, {total_amount}]"
    print(result)    



if __name__ == "__main__":
    
    print("#" * line_len)

    while True:
        now_dtm = datetime.datetime.now()
        run_dtm = now_dtm.strftime("%Y-%m-%d %H:%M:%S")
        run_hh = now_dtm.strftime("%H")
        
        if run_hh > "17":
            print("End Calculation for Dealing.")
            break

        execute(run_dtm)
        time.sleep(5)

    print("#" * line_len)
