from multiprocessing import Process, Queue
import os, thread
import pandas as pd
from Utility import *
import datetime as dt
from KiteOrderManager import KiteOrderManager
from DatabaseManager import DatabaseManager

def Start():
    kiteInstance = KiteOrderManager.GetInstance()
    dbInstance = DatabaseManager.GetInstance()
    doneStock = []
    while (1):
        now = int(datetime.now().strftime("%H%M%S"))

        # Start trading
        if now >= int(TICKERSTART):
            try:
                shortListedStock = dbInstance.GetOpenGapOpenTask()
                len = shortListedStock.__len__()
                if len == 0:
                    break
                availableMargin = TOTAL_MARGIN / len
                for stock in shortListedStock:
                    try:
                        if stock['status'] == 'b':
                            BuyStock(stock['symbol'], stock['openPrice'], availableMargin, kiteInstance)
                        elif stock['status'] == 's':
                            SellStock(stock['symbol'], stock['openPrice'], availableMargin, kiteInstance)
                    except Exception as e:
                        print "Exception in executing stock " + stock['symbol']
                        print e
            except Exception as e:
                print "Exception in GapOpenTrading::Start()"
                print e
            time.sleep(5)
        time.sleep(1)

def BuyStock(symbol, openPrice, margin, kiteInstance):
    quantity = margin / openPrice
    targetPoint, stopLossPoint = GetTargetSLPoints(openPrice)
    if (targetPoint == 0 or stopLossPoint == 0):
        print "TP/Sl point is 0 for openprice " + str(openPrice)
        return

    paddedPrice = (openPrice * PRICE_PADDING_PERCENTAGE / 100)
    paddedPrice = int((paddedPrice / 0.05).__format__('.0f'))
    paddedPrice = float((paddedPrice * 0.05).__format__('.2f'))
    tradePrice = openPrice - paddedPrice
    kiteInstance.BuyOrder(symbol, tradePrice, targetPoint, stopLossPoint, quantity)

    thread.start_new_thread(MarkGapOpenTaskDone, (symbol))

def SellStock(symbol, openPrice, margin, kiteInstance):
    quantity = margin / openPrice
    targetPoint, stopLossPoint = GetTargetSLPoints(openPrice)
    if (targetPoint == 0 or stopLossPoint == 0):
        print "TP/Sl point is 0 for openprice " + str(openPrice)
        return

    paddedPrice = (openPrice * PRICE_PADDING_PERCENTAGE / 100)
    paddedPrice = int((paddedPrice / 0.05).__format__('.0f'))
    paddedPrice = float((paddedPrice * 0.05).__format__('.2f'))
    tradePrice = openPrice + paddedPrice
    kiteInstance.SellOrder(symbol, tradePrice, targetPoint, stopLossPoint, quantity)

    thread.start_new_thread(MarkGapOpenTaskDone, (symbol))

def MarkGapOpenTaskDone(symbol):
    dbInstance = DatabaseManager.GetInstance()
    dbInstance.MarkGapOpenTaskDone(symbol)

def GetTargetSLPoints(openPrice):
    targetPoint = (lastPrice * PROFIT_PERCENTAGE / 100)
    targetPoint = int((targetPoint / 0.05).__format__('.0f'))
    targetPoint = (targetPoint * 0.05).__format__('.2f')

    stopLossPoint = targetPoint
    if (PROFIT_PERCENTAGE != STOPLOSS_PERCENTAGE):
        stopLossPoint = (lastPrice * STOPLOSS_PERCENTAGE / 100)
        stopLossPoint = int((stopLossPoint / 0.05).__format__('.0f'))
        stopLossPoint = (stopLossPoint * 0.05).__format__('.2f')

    return [targetPoint, stopLossPoint]

class kCommand:

    def __init__(self, *args):
        self.args = args

    def run_job(self, queue, args):
        try:
            Start()
            queue.put(None)
        except Exception as e:
            queue.put(e)

    def do(self):

        queue = Queue()
        process = Process(target=self.run_job, args=(queue, self.args))
        process.start()
        result = queue.get()
        process.join()

        if result is not None:
            raise result

    def get_name(self):
        return "GapOpenTrading command"


