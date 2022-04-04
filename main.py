import os
from pprint import pprint
from Ftx.FtxClient import FtxClient
from dotenv import load_dotenv
import datetime


def main():
    load_dotenv()

    ftx = FtxClient(str(os.getenv("API_KEY")), str(os.getenv("API_SECRET")))
    ftx.cover_all_leveraged_subaccounts('Input')



if __name__ == '__main__':
    main()
