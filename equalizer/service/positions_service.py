from kiteconnect.global_stuff import get_kite_client_from_cache


def get_positions_resp():
    kite = get_kite_client_from_cache()
    return kite.positions()


def get_instrument_wise_positions() -> dict:
    """
        Extracts a dictionary with 'exchange:tradingsymbol' as the key and quantity as the value from the 'net' field.

        :return: Dictionary with 'exchange:tradingsymbol' as key and quantity as value.
        """
    data = get_positions_resp()

    if not isinstance(data, dict) or 'net' not in data:
        return None

    return {
        f"{item['exchange']}_{item['tradingsymbol']}": item['quantity']
        for item in data.get('net', [])
    }