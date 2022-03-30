from pprint import pprint

from Ftx.FtxClient import FtxClient
import json

from Ftx.FtxSimpleCommands import FtxSimpleCommands


def main():
    ftx = FtxSimpleCommands('','')
    pprint(ftx.getAllAccountsThatHaveOrders())
    ftx = FtxClient('', '','xaut-usdT 2')
    data = ftx.get_subAccounts()
    # pprint(ftx.ord)
    # ftx.get_withdrawals()



if __name__ == '__main__':
    main()
