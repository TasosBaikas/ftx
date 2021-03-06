import time
import urllib.parse
from pprint import pprint
from typing import Optional, Dict, Any, List

from requests import Request, Session, Response
import hmac


# from ciso8601 import parse_datetime


class FtxClient:
    _ENDPOINT = 'https://ftx.com/api/'

    def __init__(self, api_key=None, api_secret=None, subaccount_name=None) -> None:
        self._session = Session()
        self._api_key = api_key
        self._api_secret = api_secret
        self._subaccount_name = subaccount_name

    def _get(self, path: str, params: Optional[Dict[str, Any]] = None) -> Any:
        return self._request('GET', path, params=params)

    def _post(self, path: str, params: Optional[Dict[str, Any]] = None) -> Any:
        return self._request('POST', path, json=params)

    def _delete(self, path: str, params: Optional[Dict[str, Any]] = None) -> Any:
        return self._request('DELETE', path, json=params)

    def _request(self, method: str, path: str, **kwargs) -> Any:
        request = Request(method, self._ENDPOINT + path.replace(" ", "%20"), **kwargs)
        self._sign_request(request)
        response = self._session.send(request.prepare())
        return self._process_response(response)

    def _sign_request(self, request: Request) -> None:
        ts = int(time.time() * 1000)
        prepared = request.prepare()
        signature_payload = f'{ts}{prepared.method}{prepared.path_url}'.encode()
        if prepared.body:
            signature_payload += prepared.body
        signature = hmac.new(self._api_secret.encode(), signature_payload, 'sha256').hexdigest()
        request.headers['FTX-KEY'] = self._api_key
        request.headers['FTX-SIGN'] = signature
        request.headers['FTX-TS'] = str(ts)
        if self._subaccount_name:
            request.headers['FTX-SUBACCOUNT'] = urllib.parse.quote(self._subaccount_name)

    def _process_response(self, response: Response) -> Any:
        try:
            data = response.json()
        except ValueError:
            response.raise_for_status()
            raise
        else:
            if not data['success']:
                raise Exception(data['error'])
            return data['result']

    # Made by tasosbaikas
    def get_all_accounts_that_have_orders(self) -> list:
        data = self.get_subAccounts()
        result = []
        for sub in data:
            ftx = FtxClient(self._api_key, self._api_secret, sub['nickname'])
            pos = ftx.get_open_orders()
            if pos:
                result.append(sub['nickname'])

        return result

    # Made by tasosbaikas
    def transfer_all_funds_to_subaccount(self, subaccount: str) -> None:
        data = self.get_all_balances()
        for sub_account_name in data:  # takes the key
            for sub_account_coin in data[sub_account_name]:  # takes the value
                if sub_account_coin['availableWithoutBorrow'] <= 0:
                    continue

                try:
                    self.transfer_beetween_Accounts(
                        {
                            "coin": sub_account_coin['coin'],
                            "size": sub_account_coin["availableWithoutBorrow"],
                            "source": sub_account_name,
                            "destination": subaccount,
                        }
                    )
                except Exception:
                    pass

    # Made by tasosbaikas
    def cover_all_leveraged_subaccounts(self, take_money_from_subaccount: str) -> None:
        data = self.get_all_balances()
        for sub_account_name in data:  # takes the keys
            for sub_account_coin in data[sub_account_name]:  # takes the values
                if sub_account_coin['total'] >= 0:  # if balance at the specific coin is positive it means that it has no leverage
                    continue

                if sub_account_name == take_money_from_subaccount:  # if the account is the same as the account to transfer
                    continue

                for take_money_from_subaccount_coin in data[take_money_from_subaccount]:
                    if (take_money_from_subaccount_coin['coin'] != sub_account_coin['coin']):
                        continue

                    if take_money_from_subaccount_coin["total"] <= 0:
                        break

                    if take_money_from_subaccount_coin["total"] < -sub_account_coin["total"]:
                        self.transfer_beetween_Accounts(
                            {
                                "coin": sub_account_coin['coin'],
                                "size": take_money_from_subaccount_coin["total"],
                                "source": take_money_from_subaccount,
                                "destination": sub_account_name,
                            }
                        )
                    else:
                        try:
                            self.transfer_beetween_Accounts(
                                {
                                    "coin": sub_account_coin['coin'],
                                    "size": -sub_account_coin["total"],
                                    "source": take_money_from_subaccount,
                                    "destination": sub_account_name,
                                }
                            )
                        except Exception:
                            pass

                        break



    # Made by tasosbaikas
    def transfer_beetween_Accounts(self, params: Optional[Dict[str, Any]] = None) -> dict:
        return self._post('subaccounts/transfer', params)

    # Made by tasosbaikas
    # use datetime.datetime(2022, 3, 28, 0, 0, 0).timestamp() to calculate start_time and end_time
    def find_how_much_the_account_won(self, start_time=None, end_time=None) -> float:
        temp_start = start_time
        temp_end = end_time
        data = self.get_order_history(start_time=temp_start, end_time=temp_end)

        name_of_markets = self._name_of_markets(data)

        total_sum = 0
        for name in name_of_markets:
            buy_sum = 0
            sell_sum = 0
            buy_filledSize_sum = 0
            sell_filledSize_sum = 0
            avgFillPrice_sum = 0
            each_transaction_count = 0
            for each_transaction in data:
                if each_transaction['filledSize'] == 0:
                    continue

                try: # if it is spot
                    index_of_slash = each_transaction['market'].index("/") # if it spot market it will be in format e.g USDT/USD
                    if not each_transaction['market'][0:index_of_slash] == name:
                        continue
                except Exception: # that means that it is perpetual
                    if not each_transaction['market'] == name: # if it perpetual it will be in format e.g USDT-PERP
                        continue

                if each_transaction['side'] == 'buy':
                    buy_sum += each_transaction['filledSize'] * each_transaction['avgFillPrice']
                    buy_filledSize_sum += each_transaction['filledSize']
                elif each_transaction['side'] == 'sell':
                    sell_sum += each_transaction['filledSize'] * each_transaction['avgFillPrice']
                    sell_filledSize_sum += each_transaction['filledSize']

                avgFillPrice_sum += each_transaction['avgFillPrice']
                each_transaction_count += 1

            if (each_transaction_count == 0):
                continue

            coins_that_remain = buy_filledSize_sum - sell_filledSize_sum
            if (coins_that_remain >= 0):#if >= 0 it means that we have the coins and we have not sell them yet!
                total_sum += sell_sum - buy_sum + coins_that_remain * avgFillPrice_sum / each_transaction_count
            else:#if coins_that_remain is negative it means that we are in leverage
                total_sum += sell_sum - buy_sum + coins_that_remain * avgFillPrice_sum / each_transaction_count # in this case coins_that_remain is negative

        return total_sum

    # Made by tasosbaikas
    def _name_of_markets(self,data) -> list:
        newList = []
        for each_transaction in data:
            if each_transaction['filledSize'] == 0:
                continue

            try:# if it is spot
                index_of_slash = each_transaction['market'].index("/")
                if not each_transaction['market'][0:index_of_slash] in newList:
                    newList.append(each_transaction['market'][0:index_of_slash])

            except Exception:# that means that it is perpetual
                if not each_transaction['market'] in newList:
                    newList.append(each_transaction['market'])

        return newList

    # Made by tasosbaikas
    def find_how_much_all_subaccounts_won(self, start_time=None, end_time=None):
        data = self.get_subAccounts()
        result = {}
        for sub in data:
            ftx = FtxClient(self._api_key, self._api_secret, sub['nickname'])
            sub_account_won = ftx.find_how_much_the_account_won(start_time, end_time)
            result[sub['nickname']] = sub_account_won

        return result

    def get_all_futures(self) -> List[dict]:
        return self._get('futures')

    def get_future(self, future_name: str = None) -> dict:
        return self._get(f'futures/{future_name}')

    def get_markets(self) -> List[dict]:
        return self._get('markets')

    def get_orderbook(self, market: str, depth: int = None) -> dict:
        return self._get(f'markets/{market}/orderbook', {'depth': depth})

    def get_trades(self, market: str, start_time: float = None, end_time: float = None) -> dict:
        return self._get(f'markets/{market}/trades', {'start_time': start_time, 'end_time': end_time})

    def get_subAccounts(self):
        return self._get('subaccounts')

    def get_account_info(self) -> dict:
        return self._get(f'account')

    def get_open_orders(self, market: str = None) -> List[dict]:
        return self._get(f'orders', {'market': market})

    def get_order_history(
            self, market: str = None, side: str = None, order_type: str = None,
            start_time: float = None, end_time: float = None
    ) -> List[dict]:
        return self._get(f'orders/history', {
            'market': market,
            'side': side,
            'orderType': order_type,
            'start_time': start_time,
            'end_time': end_time
        })

    def get_conditional_order_history(
            self, market: str = None, side: str = None, type: str = None,
            order_type: str = None, start_time: float = None, end_time: float = None
    ) -> List[dict]:
        return self._get(f'conditional_orders/history', {
            'market': market,
            'side': side,
            'type': type,
            'orderType': order_type,
            'start_time': start_time,
            'end_time': end_time
        })

    def modify_order(
            self, existing_order_id: Optional[str] = None,
            existing_client_order_id: Optional[str] = None, price: Optional[float] = None,
            size: Optional[float] = None, client_order_id: Optional[str] = None,
    ) -> dict:
        assert (existing_order_id is None) ^ (existing_client_order_id is None), \
            'Must supply exactly one ID for the order to modify'
        assert (price is None) or (size is None), 'Must modify price or size of order'
        path = f'orders/{existing_order_id}/modify' if existing_order_id is not None else \
            f'orders/by_client_id/{existing_client_order_id}/modify'
        return self._post(path, {
            **({'size': size} if size is not None else {}),
            **({'price': price} if price is not None else {}),
            **({'clientId': client_order_id} if client_order_id is not None else {}),
        })

    def get_conditional_orders(self, market: str = None) -> List[dict]:
        return self._get(f'conditional_orders', {'market': market})

    def place_order(self, market: str, side: str, price: float, size: float, type: str = 'limit',
                    reduce_only: bool = False, ioc: bool = False, post_only: bool = False,
                    client_id: str = None, reject_after_ts: float = None) -> dict:
        return self._post('orders', {
            'market': market,
            'side': side,
            'price': price,
            'size': size,
            'type': type,
            'reduceOnly': reduce_only,
            'ioc': ioc,
            'postOnly': post_only,
            'clientId': client_id,
            'rejectAfterTs': reject_after_ts
        })

    def place_conditional_order(
            self, market: str, side: str, size: float, type: str = 'stop',
            limit_price: float = None, reduce_only: bool = False, cancel: bool = True,
            trigger_price: float = None, trail_value: float = None
    ) -> dict:
        """
        To send a Stop Market order, set type='stop' and supply a trigger_price
        To send a Stop Limit order, also supply a limit_price
        To send a Take Profit Market order, set type='trailing_stop' and supply a trigger_price
        To send a Trailing Stop order, set type='trailing_stop' and supply a trail_value
        """
        assert type in ('stop', 'take_profit', 'trailing_stop')
        assert type not in ('stop', 'take_profit') or trigger_price is not None, \
            'Need trigger prices for stop losses and take profits'
        assert type not in ('trailing_stop',) or (trigger_price is None and trail_value is not None), \
            'Trailing stops need a trail value and cannot take a trigger price'

        return self._post('conditional_orders', {
            'market': market,
            'side': side,
            'triggerPrice': trigger_price,
            'size': size,
            'reduceOnly': reduce_only,
            'type': 'stop',
            'cancelLimitOnTrigger': cancel,
            'orderPrice': limit_price
        })

    def cancel_order(self, order_id: str) -> dict:
        return self._delete(f'orders/{order_id}')

    def cancel_orders(
            self, market_name: str = None,
            conditional_orders: bool = False, limit_orders: bool = False
    ) -> dict:
        return self._delete(f'orders', {
            'market': market_name,
            'conditionalOrdersOnly': conditional_orders,
            'limitOrdersOnly': limit_orders
        })

    def get_fills(self, market: str = None, start_time: float = None,
                  end_time: float = None, min_id: int = None, order_id: int = None
                  ) -> List[dict]:
        return self._get('fills', {
            'market': market,
            'start_time': start_time,
            'end_time': end_time,
            'minId': min_id,
            'orderId': order_id
        })

    def get_balances(self) -> List[dict]:
        return self._get('wallet/balances')

    def get_total_usd_balance(self) -> int:
        total_usd = 0
        balances = self._get('wallet/balances')
        for balance in balances:
            total_usd += balance['usdValue']
        return total_usd

    def get_all_balances(self) -> List[dict]:
        return self._get('wallet/all_balances')

    def get_total_account_usd_balance(self) -> int:
        total_usd = 0
        all_balances = self._get('wallet/all_balances')
        for wallet in all_balances:
            for balance in all_balances[wallet]:
                total_usd += balance['usdValue']
        return total_usd

    def get_positions(self, show_avg_price: bool = False) -> List[dict]:
        return self._get('positions', {'showAvgPrice': show_avg_price})

    def get_position(self, name: str, show_avg_price: bool = False) -> dict:
        return next(filter(lambda x: x['future'] == name, self.get_positions(show_avg_price)), None)

    # def get_all_trades(self, market: str, start_time: float = None, end_time: float = None) -> List:
    #     ids = set()
    #     limit = 100
    #     results = []
    #     while True:
    #         response = self._get(f'markets/{market}/trades', {
    #             'end_time': end_time,
    #             'start_time': start_time,
    #         })
    #         deduped_trades = [r for r in response if r['id'] not in ids]
    #         results.extend(deduped_trades)
    #         ids |= {r['id'] for r in deduped_trades}
    #         print(f'Adding {len(response)} trades with end time {end_time}')
    #         if len(response) == 0:
    #             break
    #         end_time = min(parse_datetime(t['time']) for t in response).timestamp()
    #         if len(response) < limit:
    #             break
    #     return results

    def get_historical_prices(
            self, market: str, resolution: int = 300, start_time: float = None,
            end_time: float = None
    ) -> List[dict]:
        return self._get(f'markets/{market}/candles', {
            'resolution': resolution,
            'start_time': start_time,
            'end_time': end_time
        })

    def get_last_historical_prices(self, market: str, resolution: int = 300) -> List[dict]:
        return self._get(f'markets/{market}/candles/last', {'resolution': resolution})

    def get_borrow_rates(self) -> List[dict]:
        return self._get('spot_margin/borrow_rates')

    def get_borrow_history(self, start_time: float = None, end_time: float = None) -> List[dict]:
        return self._get('spot_margin/borrow_history', {'start_time': start_time, 'end_time': end_time})

    def get_lending_history(self, start_time: float = None, end_time: float = None) -> List[dict]:
        return self._get('spot_margin/lending_history', {
            'start_time': start_time,
            'end_time': end_time
        })

    def get_expired_futures(self) -> List[dict]:
        return self._get('expired_futures')

    def get_coins(self) -> List[dict]:
        return self._get('wallet/coins')

    def get_future_stats(self, future_name: str) -> dict:
        return self._get(f'futures/{future_name}/stats')

    def get_single_market(self, market: str = None) -> Dict:
        return self._get(f'markets/{market}')

    def get_market_info(self, market: str = None) -> dict:
        return self._get('spot_margin/market_info', {'market': market})

    def get_trigger_order_triggers(self, conditional_order_id: str = None) -> List[dict]:
        return self._get(f'conditional_orders/{conditional_order_id}/triggers')

    def get_trigger_order_history(self, market: str = None) -> List[dict]:
        return self._get('conditional_orders/history', {'market': market})

    def get_staking_balances(self) -> List[dict]:
        return self._get('staking/balances')

    def get_stakes(self) -> List[dict]:
        return self._get('staking/stakes')

    def get_staking_rewards(self, start_time: float = None, end_time: float = None) -> List[dict]:
        return self._get('staking/staking_rewards', {
            'start_time': start_time,
            'end_time': end_time
        })

    def place_staking_request(self, coin: str = 'SRM', size: float = None) -> dict:
        return self._post('srm_stakes/stakes', )

    def get_funding_rates(self, future: str = None, start_time: float = None, end_time: float = None) -> List[dict]:
        return self._get('funding_rates', {
            'future': future,
            'start_time': start_time,
            'end_time': end_time
        })

    def get_all_funding_rates(self) -> List[dict]:
        return self._get('funding_rates')

    def get_funding_payments(self, start_time: float = None, end_time: float = None) -> List[dict]:
        return self._get('funding_payments', {
            'start_time': start_time,
            'end_time': end_time
        })

    def create_subaccount(self, nickname: str) -> dict:
        return self._post('subaccounts', {'nickname': nickname})

    def get_subaccount_balances(self, nickname: str) -> List[dict]:
        return self._get(f'subaccounts/{nickname}/balances')

    def get_deposit_address(self, ticker: str) -> dict:
        return self._get(f'wallet/deposit_address/{ticker}')

    def get_deposit_history(self) -> List[dict]:
        return self._get('wallet/deposits')

    def get_withdrawal_fee(self, coin: str, size: int, address: str, method: str = None, tag: str = None) -> Dict:
        return self._get('wallet/withdrawal_fee', {
            'coin': coin,
            'size': size,
            'address': address,
            'method': method,
            'tag': tag
        })

    def get_withdrawals(self, start_time: float = None, end_time: float = None) -> List[dict]:
        return self._get('wallet/withdrawals', {'start_time': start_time, 'end_time': end_time})

    def get_saved_addresses(self, coin: str = None) -> dict:
        return self._get('wallet/saved_addresses', {'coin': coin})

    def submit_fiat_withdrawal(self, coin: str, size: int, saved_address_id: int, code: int = None) -> Dict:
        return self._post('wallet/fiat_withdrawals', {
            'coin': coin,
            'size': size,
            'savedAddressId': saved_address_id,
            'code': code
        })

    def get_latency_stats(self, days: int = 1, subaccount_nickname: str = None) -> Dict:
        return self._get('stats/latency_stats', {'days': days, 'subaccount_nickname': subaccount_nickname})
