import pandas as pd


def get_peloton(data, factor: float) -> pd.Series:
    """

    Get peloton of results

    """
    top1 = data.max()
    data = data.sort_values(ascending=False)
    threshold = top1 * (1 - factor)
    peloton = data >= threshold
    return peloton
