from pprint import pprint

from Ftx.FtxClient import FtxClient
import json

from Ftx.FtxSimpleCommands import FtxSimpleCommands


def main():
    ftx = FtxSimpleCommands('','')
    pprint(ftx.getAllAccountsThatHaveOrders())
    # pprint(ftx.ord)
    # ftx.get_withdrawals()



if __name__ == '__main__':
    main()
