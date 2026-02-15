from tokenizers import Tokenizer
from tokenizers import normalizers
from tokenizers import pre_tokenizers
from tokenizers.models import BPE
from tokenizers.models import WordLevel
from tokenizers.processors import TemplateProcessing
from tokenizers.trainers import BpeTrainer
from tokenizers.trainers import WordLevelTrainer
from typing import List

from corio.path_tools import Path


class TokenConfig:
    """

    Default config for special characters etc.

    """
    PAD = '<pad>'
    UNK = '<unk>'
    CLS = '<cls>'
    BOS = '<bos>'
    EOS = '<eos>'
    SEP = '<sep>'
    MASK = '<mask>'

    COW_PREFIX = '...'
    EOW_SUFFIX = '|'

    SPECIALS = [PAD, UNK, CLS, BOS, EOS, SEP, MASK]

    VARIABLE_LENGTH = -1
    VOCAB_SIZE = 10_000


def fix_length(tokenizer: Tokenizer, length: int):
    """

    Fix tokenizer length if input is too long

    """
    if length > TokenConfig.VARIABLE_LENGTH:
        tokenizer.enable_padding(pad_token=TokenConfig.PAD, pad_id=tokenizer.token_to_id(TokenConfig.PAD),
                                 length=length)
        tokenizer.enable_truncation(max_length=length)

    return tokenizer


def get_template(cls=True, sep=True, pair=False):
    """

    Create a tokenizers template

    """

    if pair:
        n = 1
        letter = 'B'
        template = get_template(cls, sep, pair=False)
    else:
        n = 0
        letter = 'A'
        template = []

    if cls and not pair:
        template.append(f'{TokenConfig.CLS}:{n}')

    template.append(f'${letter}:{n}')

    if sep:
        template.append(f'{TokenConfig.SEP}:{n}')

    return template


def add_template(tokenizer: Tokenizer, cls, sep):
    """

    Add a tokenizers template

    """
    tokenizer.post_processor = TemplateProcessing(
        single=get_template(cls=cls, sep=sep, pair=False),
        pair=get_template(cls=cls, sep=sep, pair=True),
        special_tokens=[
            (token_special, tokenizer.token_to_id(token_special))
            for token_special in TokenConfig.SPECIALS
        ],
    )
    return tokenizer


def train_fixed_vocab_tokenizer(tokens: List[str], length: int = TokenConfig.VARIABLE_LENGTH,
                                show_progress: bool = True, cls: bool = True,
                                sep: bool = True) -> Tokenizer:
    """

    "Train" a word level tokenizer from a fixed, unique set of tokens.

    """
    model = WordLevel(unk_token=TokenConfig.UNK)
    tokenizer = Tokenizer(model)
    tokenizer.normalizer = normalizers.Lowercase()
    trainer = WordLevelTrainer(min_frequency=0, special_tokens=TokenConfig.SPECIALS)
    tokenizer.train_from_iterator([sorted(set(tokens))], trainer=trainer, show_progress=show_progress)
    fix_length(tokenizer, length)
    add_template(tokenizer, cls, sep)
    return tokenizer


def train_bpe_tokenizer(data, vocab_size: int = TokenConfig.VOCAB_SIZE, min_frequency: int = 0,
                        length: int = TokenConfig.VARIABLE_LENGTH,
                        show_progress: bool = True, cls: bool = True, sep: bool = True) -> Tokenizer:
    """

    Train byte-pair encoder from given parameters

    """
    model = BPE(unk_token=TokenConfig.UNK)
    tokenizer = Tokenizer(model)

    normalizers_bpe = [normalizers.NFC(), normalizers.Strip(), normalizers.StripAccents(), normalizers.Lowercase()]
    tokenizer.normalizer = normalizers.Sequence(normalizers_bpe)

    pre_tokenizers_bpe = [pre_tokenizers.Whitespace(), pre_tokenizers.Digits(individual_digits=True)]
    tokenizer.pre_tokenizer = pre_tokenizers.Sequence(pre_tokenizers_bpe)

    trainer = BpeTrainer(
        special_tokens=TokenConfig.SPECIALS,
        vocab_size=vocab_size,
        min_frequency=min_frequency,
        end_of_word_suffix=TokenConfig.EOW_SUFFIX,
        continuing_subword_prefix=TokenConfig.COW_PREFIX,
        show_progress=show_progress,
        initial_alphabet=pre_tokenizers.ByteLevel.alphabet()
    )

    is_data_files = isinstance(data, list) and all(isinstance(datum, Path) for datum in data)
    if is_data_files:
        tokenizer.train([str(path) for path in data], trainer)
    else:
        tokenizer.train_from_iterator(data, trainer)

    fix_length(tokenizer, length)
    add_template(tokenizer, cls, sep)

    return tokenizer
