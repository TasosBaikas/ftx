import os
from pprint import pprint
from Ftx.FtxClient import FtxClient
from dotenv import load_dotenv


def main():
    load_dotenv()

    ftx = FtxClient(str(os.getenv("API_KEY")), str(os.getenv("API_SECRET")))



if __name__ == '__main__':
    main()
