import logging
import math
import random

from itertools import count

logger = logging.getLogger(__name__)


def exp_backoff(step, max):
    """ Exponential backoff time with Full Jitter """
    # this is a numerically stable version of
    # random.uniform(0, min(max, step * 2 ** attempt))
    max_attempts = math.log(max / step, 2)
    for attempt in count(0, 1):
        if attempt <= max_attempts:
            yield random.uniform(0, step * 2 ** attempt)
        else:
            yield random.uniform(0, max)


def linear_backoff(step, max):
    """ Linear backoff time with Full Jitter """
    # this is a numerically stable version of
    # random.uniform(0, min(max, step * 2 ** attempt))
    max_attempts = max / step
    for attempt in count(0, 1):
        if attempt <= max_attempts:
            yield random.uniform(0, step * attempt)
        else:
            yield random.uniform(0, max)
