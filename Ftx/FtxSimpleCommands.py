from pprint import pprint

from Ftx.FtxClient import FtxClient


class FtxSimpleCommands:

    def __init__(self, api_key=None, api_secret=None, subaccount_name=None) -> None:
        self._api_key = api_key
        self._api_secret = api_secret
        self._subaccount_name = subaccount_name

    def getAllAccountsThatHaveOrders(self):
        ftx = FtxClient(self._api_key, self._api_secret)

        data = ftx.get_subAccounts()
        for sub in data:
            ftx = FtxClient(self._api_key, self._api_secret, sub['nickname'])
            pos = ftx.get_open_orders()
            if pos:
                if sub['nickname'] == 'None':
                    pprint("'Main Account'")
                else:
                    pprint(sub['nickname'])

