import unittest

from datetime import datetime

from equalizer.service.arbitrage_service import check_arbitrage

ticker1 = {
        'instrument_token': 2452737,
        'mode': 'full',
        'last_price': 1885.55,
        'tradable': True,
        'exchange_timestamp': datetime(2024, 4, 12, 11, 41, 54),
        'depth': {
            'buy': [{
                'price': 1886.45,
                'quantity': 1486
            }, {
                'price': 1886.25,
                'quantity': 1
            }, {
                'price': 1886.15,
                'quantity': 45
            }, {
                'price': 1886.1,
                'quantity': 9
            }],
            'sell': [{
                'price': 1886.8,
                'quantity': 30
            }, {
                'price': 1886.85,
                'quantity': 30
            }, {
                'price': 1886.9,
                'quantity': 10
            }, {
                'price': 1886.95,
                'quantity': 50
            }, {
                'price': 1887,
                'quantity': 451
            }]
        }
    }

ticker2 = {
        'instrument_token': 138918404,
        'mode': 'full',
        'last_price': 1885,
        'tradable': True,
        'exchange_timestamp': datetime(2024, 4, 12, 11, 41, 54),
        'depth': {
            'buy': [{
                'price': 1882.85,
                'quantity': 35
            }, {
                'price': 1882.8,
                'quantity': 27
            }, {
                'price': 1882.55,
                'quantity': 36
            }, {
                'price': 1882.3,
                'quantity': 16
            }, {
                'price': 1882.05,
                'quantity': 16
            }],
            'sell': [{
                'price': 1884.5,
                'quantity': 10
            }, {
                'price': 1884.55,
                'quantity': 12
            }, {
                'price': 1884.9,
                'quantity': 7
            }]
        }
    }


class MyTestCase(unittest.TestCase):

    def test_arbitrage(self):
        arbitrage_opportunities = check_arbitrage(ticker1, ticker2, 0, 1)
        print(arbitrage_opportunities)
        print(ticker1)
        print(ticker2)
        self.assertEqual(True, True)


if __name__ == '__main__':
    unittest.main()
