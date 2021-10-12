import os
import sys
sys.path.append(os.path.dirname(os.path.abspath(os.path.dirname(__file__))))
from utility.static import *
from utility.setting import *


class CollectorUpbit:
    def __init__(self, qlist):
        """
                    0        1       2        3       4       5          6        7      8      9     10
        qlist = [windowQ, soundQ, query1Q, query2Q, teleQ, sreceivQ, creceivQ, stockQ, coinQ, sstgQ, cstgQ,
                 tick1Q, tick2Q, tick3Q, tick4Q, tick5Q]
                   11       12      13     14      15
        """
        self.windowQ = qlist[0]
        self.query2Q = qlist[3]
        self.tick5Q = qlist[15]

        self.dict_df = {}                   # 틱데이터 저장용 딕셔너리 key: code, value: datafame
        self.dict_orderbook = {}            # 오더북 저장용 딕셔너리
        self.time_save = timedelta_sec(60)  # 틱데이터 저장주기 확인용
        self.Start()

    def Start(self):
        while True:
            data = self.tick5Q.get()
            if len(data) == 13:
                self.UpdateTickData(data)
            elif len(data) == 23:
                self.UpdateOrderbook(data)

    def UpdateTickData(self, data):
        code = data[-3]
        dt = data[-2]
        receivetime = data[-1]

        if code not in self.dict_orderbook.keys():
            return

        data.remove(code)
        data.remove(dt)
        data.remove(receivetime)
        data += self.dict_orderbook[code]

        if code not in self.dict_df.keys():
            columns = [
                '현재가', '시가', '고가', '저가', '등락율', '당일거래대금', '초당매수수량', '초당매도수량',
                '누적매수량', '누적매도량', '매도총잔량', '매수총잔량',
                '매도호가5', '매도호가4', '매도호가3', '매도호가2', '매도호가1',
                '매수호가1', '매수호가2', '매수호가3', '매수호가4', '매수호가5',
                '매도잔량5', '매도잔량4', '매도잔량3', '매도잔량2', '매도잔량1',
                '매수잔량1', '매수잔량2', '매수잔량3', '매수잔량4', '매수잔량5'
            ]
            self.dict_df[code] = pd.DataFrame([data], columns=columns, index=[dt])
        else:
            self.dict_df[code].at[dt] = data

        if now() > self.time_save:
            gap = (now() - receivetime).total_seconds()
            self.windowQ.put([ui_num['C단순텍스트'], f'콜렉터 수신 기록 알림 - 수신시간과 기록시간의 차이는 [{gap}]초입니다.'])
            self.query2Q.put([2, self.dict_df])
            self.dict_df = {}
            self.time_save = timedelta_sec(60)

    def UpdateOrderbook(self, data):
        code = data[0]
        data.remove(code)
        self.dict_orderbook[code] = data
