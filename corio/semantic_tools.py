import pandas as pd
from sentence_transformers import SentenceTransformer

from corio.logging_tools import logger


class SemanticManager:
    """

    Base semantic similarity manager

    """

    REPO_ID = 'distiluse-base-multilingual-cased-v1'

    def __init__(self, data: pd.Series):
        logger.info(f"Loading model from {self.REPO_ID}")
        self.model = SentenceTransformer(self.REPO_ID)
        self.data = data
        logger.info(f"Vectorising {len(data)} texts using {self.model.device}...")
        self.embs = self.vectorise()
        logger.info(f"Vectorising complete.")

    def vectorise(self):
        """

        Vectorise the corpus

        """
        embs = self.model.encode(self.data.tolist())
        return embs

    def get_sims(self, string: str):
        """

        Get similarities between query string and corpus

        """
        logger.info(f'Getting similarities for search term: "{string}"...')
        embs_query = self.model.encode([string])
        sims = self.model.similarity(self.embs, embs_query).squeeze().numpy()
        return sims

    def get_matches(self, string: str, top_n: int = 20):
        """

        Get the Top N matches between query string and corpus

        """
        sims = self.get_sims(string)
        args = sims.argsort()[::-1]
        matches = self.data.iloc[args][:top_n]
        return matches
