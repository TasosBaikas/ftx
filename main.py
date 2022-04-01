import os
from pprint import pprint
from Ftx.FtxClient import FtxClient
from dotenv import load_dotenv
import datetime


def main():
    load_dotenv()

    ftx = FtxClient(str(os.getenv("API_KEY")), str(os.getenv("API_SECRET")))

    # ftx.transfer_all_funds_to_subaccount('Input')
    ftx.transfer_beetween_Accounts(
        {
            "coin": 'USD',
            "size": 5,
            "source": 'main',
            "destination": 'Input',
        }
    )
    # data = ftx.find_how_much_all_subaccounts_won(datetime.datetime(2022,3,26).timestamp(),datetime.datetime(2022,3,28).timestamp())
    # sum = 0
    # pprint(data)
    # for i in data.values():
    #     sum += i
    # print(sum)

if __name__ == '__main__':
    main()
