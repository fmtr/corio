import deepdiff
import numpy as np
import pandas as pd

from fmtr.tools.iterator_tools import dedupe

Table = DataFrame = pd.DataFrame
Series = pd.Series

nan = np.nan

CONCAT_HORIZONTALLY = 1
CONCAT_VERTICALLY = 0


def normalize_nan(df, value=np.nan):
    return df.replace({pd.NA: value, None: value, np.nan: value})


class Differ:
    """

    Diff two dataframes via DeepDiff, after shape normalization, datatype simplification, etc.

    """

    def __init__(self, left: Table, right: Table):

        self.cols = dedupe(left.columns.tolist() + right.columns.tolist())
        self.rows = dedupe(left.index.values.tolist() + right.index.values.tolist())
        self.left = self.process(left)
        self.right = self.process(right)
        self.dfs = [self.left, self.right]

    def process(self, df: Table) -> Table:
        """

        Ensure same rows/columns, plus simplify datatypes via JSON round-robin.

        """

        df_rows = set(df.index.values.tolist())
        for row in self.rows:
            if row in df_rows:
                continue
            df.loc[len(df)] = None

        df_cols = set(df.columns.tolist())
        for col in self.cols:
            if col in df_cols:
                continue
            df[col] = None

        df = pd.read_json(df.to_json(date_format='iso'))
        df = normalize_nan(df, value=None)

        return df

    def get_diff(self) -> deepdiff.DeepDiff:
        """

        Cast to dicts and get diff

        """

        dicts = [df.to_dict(orient='index') for df in self.dfs]
        diff = deepdiff.DeepDiff(*dicts, ignore_order=True)
        return diff
