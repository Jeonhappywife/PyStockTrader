import os
import sys
import time
import pyupbit
from PyQt5.QtCore import QTimer
from pyupbit import WebSocketManager
sys.path.append(os.path.dirname(os.path.abspath(os.path.dirname(__file__))))
from utility.static import *
from utility.setting import *

MONEYTOP_MINUTE = 10        # 최근거래대금순위을 집계할 시간
MONEYTOP_RANK = 20          # 최근거래대금순위중 관심종목으로 선정할 순위


class WebsTicker:
    def __init__(self, qlist):
        """
                    0        1       2        3       4       5          6        7      8      9     10
        qlist = [windowQ, soundQ, query1Q, query2Q, teleQ, sreceivQ, creceivQ, stockQ, coinQ, sstgQ, cstgQ,
                 tick1Q, tick2Q, tick3Q, tick4Q, tick5Q]
                   11       12      13     14      15
        """
        self.windowQ = qlist[0]
        self.query2Q = qlist[3]
        self.creceivQ = qlist[6]
        self.coinQ = qlist[8]
        self.cstgQ = qlist[10]
        self.tick5Q = qlist[15]

        self.dict_cdjm = {}
        self.dict_time = {
            '거래대금순위기록': now(),
            '거래대금순위저장': now()
        }

        self.list_gsjm = []
        self.list_gsjm2 = []
        self.list_jang = []
        self.pre_top = []

        self.df_mt = pd.DataFrame(columns=['거래대금순위'])
        self.df_mc = pd.DataFrame(columns=['최근거래대금'])

        self.str_jcct = strf_time('%Y%m%d') + '000000'
        self.dt_mtct = None
        self.websQ_ticker = None

        self.qtimer4 = QTimer()
        self.qtimer4.setInterval(10000)
        self.qtimer4.timeout.connect(WebsTicker.ConditionSearch)
        self.qtimer4.start()

        self.Start()

    def __del__(self):
        if self.qtimer4.isActive():
            self.qtimer4.stop()
        if self.websQ_ticker is not None:
            self.websQ_ticker.terminate()

    def Start(self):
        """ get_tickers 리턴 리스트의 갯수가 다른 버그 발견, 1초 간격 3회 조회 후 길이가 긴 리스트를 티커리스트로 정한다 """
        codes = pyupbit.get_tickers(fiat="KRW")
        time.sleep(1)
        codes2 = pyupbit.get_tickers(fiat="KRW")
        codes = codes2 if len(codes2) > len(codes) else codes
        time.sleep(1)
        codes2 = pyupbit.get_tickers(fiat="KRW")
        codes = codes2 if len(codes2) > len(codes) else codes
        dict_tsbc = {}
        self.websQ_ticker = WebSocketManager('ticker', codes)
        while True:
            if not self.creceivQ.empty():
                data = self.creceivQ.get()
                self.UpdateJangolist(data)

            data = self.websQ_ticker.get()
            if data == 'ConnectionClosedError':
                self.windowQ.put([ui_num['C단순텍스트'], '시스템 명령 오류 알림 - WebsTicker 연결 끊김으로 다시 연결합니다.'])
                self.websQ_ticker = WebSocketManager('ticker', codes)
            else:
                code = data['code']
                v = data['trade_volume']
                gubun = data['ask_bid']
                dt = data['trade_date'] + data['trade_time']
                dt = strf_time('%Y%m%d%H%M%S', timedelta_hour(9, strp_time('%Y%m%d%H%M%S', dt)))
                if dt != self.str_jcct:
                    self.str_jcct = dt
                try:
                    pret = dict_tsbc[code][0]
                    bids = dict_tsbc[code][1]
                    asks = dict_tsbc[code][2]
                except KeyError:
                    pret = None
                    bids = 0
                    asks = 0
                if gubun == 'BID':
                    dict_tsbc[code] = [dt, bids + float(v), asks]
                else:
                    dict_tsbc[code] = [dt, bids, asks + float(v)]
                if dt != pret:
                    c = data['trade_price']
                    o = data['opening_price']
                    h = data['high_price']
                    low = data['low_price']
                    per = round(data['signed_change_rate'] * 100, 2)
                    dm = data['acc_trade_price']
                    bids = dict_tsbc[code][1]
                    asks = dict_tsbc[code][2]
                    tbids = data['acc_bid_volume']
                    tasks = data['acc_ask_volume']
                    dict_tsbc[code] = [dt, 0, 0]
                    self.UpdateTickData(c, o, h, low, per, dm, bids, asks, tbids, tasks, code, dt, now())

                if now() > self.dict_time['거래대금순위기록']:
                    if len(self.list_gsjm) > 0:
                        self.UpdateMoneyTop()
                    self.dict_time['거래대금순위기록'] = timedelta_sec(1)

    def UpdateJangolist(self, data):
        code = data[1]
        if '잔고편입' in data and code not in self.list_jang:
            self.list_jang.append(code)
            if code not in self.list_gsjm2:
                self.cstgQ.put(['조건진입', code])
                self.list_gsjm2.append(code)
        elif '잔고청산' in data and code in self.list_jang:
            self.list_jang.remove(code)
            if code not in self.list_gsjm and code in self.list_gsjm2:
                self.cstgQ.put(['조건이탈', code])
                self.list_gsjm2.remove(code)

    def ConditionSearch(self):
        if len(self.df_mc) > 0:
            self.df_mc.sort_values(by=['최근거래대금'], ascending=False, inplace=True)
            list_top = list(self.df_mc.index[:MONEYTOP_RANK])
            insert_list = set(list_top) - set(self.pre_top)
            if len(insert_list) > 0:
                for code in list(insert_list):
                    self.InsertGsjmlist(code)
            delete_list = set(self.pre_top) - set(list_top)
            if len(delete_list) > 0:
                for code in list(delete_list):
                    self.DeleteGsjmlist(code)
            self.pre_top = list_top

    def InsertGsjmlist(self, code):
        if code not in self.list_gsjm:
            self.list_gsjm.append(code)
        if code not in self.list_jang and code not in self.list_gsjm2:
            self.cstgQ.put(['조건진입', code])
            self.list_gsjm2.append(code)

    def DeleteGsjmlist(self, code):
        if code in self.list_gsjm:
            self.list_gsjm.remove(code)
        if code not in self.list_jang and code in self.list_gsjm2:
            self.cstgQ.put(['조건이탈', code])
            self.list_gsjm2.remove(code)

    def UpdateMoneyTop(self):
        timetype = '%Y%m%d%H%M%S'
        list_text = ';'.join(list(self.df_mc.index[:MONEYTOP_RANK]))
        curr_time = self.str_jcct
        curr_datetime = strp_time(timetype, curr_time)
        if self.dt_mtct is not None:
            gap_seconds = (curr_datetime - self.dt_mtct).total_seconds()
            while gap_seconds > 2:
                gap_seconds -= 1
                pre_time = strf_time(timetype, timedelta_sec(-gap_seconds, curr_datetime))
                self.df_mt.at[pre_time] = list_text
        self.df_mt.at[curr_time] = list_text
        self.dt_mtct = curr_datetime

        if now() > self.dict_time['거래대금순위저장']:
            self.query2Q.put([2, self.df_mt, 'moneytop', 'append'])
            self.df_mt = pd.DataFrame(columns=['거래대금순위'])
            self.dict_time['거래대금순위저장'] = timedelta_sec(10)

    def UpdateTickData(self, c, o, h, low, per, dm, bids, asks, tbids, tasks, code, dt, receivetime):
        dt_ = dt[:13]
        if code not in self.dict_cdjm.keys():
            columns = ['10초누적거래대금', '10초전당일거래대금']
            self.dict_cdjm[code] = pd.DataFrame([[0, dm]], columns=columns, index=[dt_])
        elif dt_ != self.dict_cdjm[code].index[-1]:
            직전당일거래대금 = self.dict_cdjm[code]['10초전당일거래대금'][-1]
            self.dict_cdjm[code].at[dt_] = dm - 직전당일거래대금, dm
            if len(self.dict_cdjm[code]) == MONEYTOP_MINUTE * 6:
                if per > 0:
                    self.df_mc.at[code] = self.dict_cdjm[code]['10초누적거래대금'].sum()
                elif code in self.df_mc.index:
                    self.df_mc.drop(index=code, inplace=True)
                self.dict_cdjm[code].drop(index=self.dict_cdjm[code].index[0], inplace=True)

        data = [c, o, h, low, per, dm, bids, asks, tbids, tasks, code, dt, receivetime]
        if DICT_SET['업비트트레이더'] and code in self.list_gsjm2:
            injango = code in self.list_jang
            self.cstgQ.put(data + [injango])
            if injango:
                self.coinQ.put([code, c])

        self.tick5Q.put(data)


class WebsOrderbook:
    def __init__(self, qlist):
        """
                    0        1       2        3       4       5          6        7      8      9     10
        qlist = [windowQ, soundQ, query1Q, query2Q, teleQ, sreceivQ, creceivQ, stockQ, coinQ, sstgQ, cstgQ,
                 tick1Q, tick2Q, tick3Q, tick4Q, tick5Q]
                   11       12      13     14      15
        """
        self.windowQ = qlist[0]
        self.coinQ = qlist[8]
        self.cstgQ = qlist[10]
        self.tick5Q = qlist[15]
        self.websQ_order = None
        self.Start()

    def __del__(self):
        if self.websQ_order is not None:
            self.websQ_order.terminate()

    def Start(self):
        """ get_tickers 리턴 리스트의 갯수가 다른 버그 발견, 1초 간격 3회 조회 후 길이가 긴 리스트를 티커리스트로 정한다 """
        codes = pyupbit.get_tickers(fiat="KRW")
        time.sleep(1)
        codes2 = pyupbit.get_tickers(fiat="KRW")
        codes = codes2 if len(codes2) > len(codes) else codes
        time.sleep(1)
        codes2 = pyupbit.get_tickers(fiat="KRW")
        codes = codes2 if len(codes2) > len(codes) else codes
        self.websQ_order = WebSocketManager('orderbook', codes)
        while True:
            data = self.websQ_order.get()
            if data == 'ConnectionClosedError':
                self.windowQ.put([ui_num['C단순텍스트'], '시스템 명령 오류 알림 - WebsOrderbook 연결 끊김으로 다시 연결합니다.'])
                self.websQ_order = WebSocketManager('orderbook', codes)
            else:
                code = data['code']
                tsjr = data['total_ask_size']
                tbjr = data['total_bid_size']
                s5hg = data['orderbook_units'][4]['ask_price']
                s4hg = data['orderbook_units'][3]['ask_price']
                s3hg = data['orderbook_units'][2]['ask_price']
                s2hg = data['orderbook_units'][1]['ask_price']
                s1hg = data['orderbook_units'][0]['ask_price']
                b1hg = data['orderbook_units'][0]['bid_price']
                b2hg = data['orderbook_units'][1]['bid_price']
                b3hg = data['orderbook_units'][2]['bid_price']
                b4hg = data['orderbook_units'][3]['bid_price']
                b5hg = data['orderbook_units'][4]['bid_price']
                s5jr = data['orderbook_units'][4]['ask_size']
                s4jr = data['orderbook_units'][3]['ask_size']
                s3jr = data['orderbook_units'][2]['ask_size']
                s2jr = data['orderbook_units'][1]['ask_size']
                s1jr = data['orderbook_units'][0]['ask_size']
                b1jr = data['orderbook_units'][0]['bid_size']
                b2jr = data['orderbook_units'][1]['bid_size']
                b3jr = data['orderbook_units'][2]['bid_size']
                b4jr = data['orderbook_units'][3]['bid_size']
                b5jr = data['orderbook_units'][4]['bid_size']
                data = [code, tsjr, tbjr,
                        s5hg, s4hg, s3hg, s2hg, s1hg, b1hg, b2hg, b3hg, b4hg, b5hg,
                        s5jr, s4jr, s3jr, s2jr, s1jr, b1jr, b2jr, b3jr, b4jr, b5jr]
                self.tick5Q.put(data)
                if DICT_SET['업비트트레이더']:
                    self.cstgQ.put(data)
