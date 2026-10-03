from collections import deque
from typing import Deque
import random


def create_user_queue(
        exploration_queue: Deque[str],
        exploitation_queue: Deque[str],
        temperature: float,
        output_queue_length: int,
        ) -> Deque[str]:
    """
    Creates a user queue by sampling from exploration and exploitation queues based on a given temperature.
    This function combines items from two queues, `exploration_queue` and `exploitation_queue`, to form a new queue
    of a specified length. The selection of items from each queue is influenced by the `temperature` parameter, 
    which determines the likelihood of choosing from the exploration queue over the exploitation queue.

    Args:
        exploration_queue (Deque[str]): A queue of items to explore.
        exploitation_queue (Deque[str]): A queue of items to exploit.
        temperature (float): A value between 0 and 1 that influences the probability of selecting from the exploration queue.
                             A higher temperature increases the likelihood of exploration.
        output_queue_length (int): The desired length of the output queue. Must not exceed the total number of unique items
                                   available in both input queues.

    Returns:
        Deque[str]: A queue containing a mix of items from the exploration and exploitation queues,
                    with a length equal to `output_queue_length`.

    Raises:
        ValueError: If `temperature` is not between 0 and 1.
        ValueError: If `output_queue_length` exceeds the number of unique items available in both queues.
    """
    
    if not 0 <= temperature <= 1:
        raise ValueError("Temperature must be between 0 and 1")
    
    # Count truly available unique items
    unique_items_count = len(set(list(exploration_queue) + list(exploitation_queue)))
    
    if output_queue_length > unique_items_count:
        raise ValueError(
            f"Requested unique output length {output_queue_length} "
            f"exceeds available unique elements {unique_items_count}"
        )
    
    seen_items = set()
    result = deque()

    while len(result) < output_queue_length:
        # Handle case when one queue is empty
        if not exploration_queue:
            source_queue = exploitation_queue
        elif not exploitation_queue:
            source_queue = exploration_queue
        # Both queues have items, use temperature to decide
        elif random.random() < temperature:
            print("sampling from exploration queue")
            source_queue = exploration_queue
        else:
            print("sampling from exploitation queue")
            source_queue = exploitation_queue
            
        item = source_queue.popleft()
        if item not in seen_items:
            result.append(item)
            seen_items.add(item)

    return result
