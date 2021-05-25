
        UPDATE jongmok_day_sum
           SET gap = gap * -1
         WHERE preday_rt < 0
           AND DEAL_DT = '2021.05.25'
        