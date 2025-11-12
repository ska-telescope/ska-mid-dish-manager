import queue


class MethodCallsStore:
    """Store the calls to this method so it can be awaited."""

    def __init__(self) -> None:
        """Init the class."""
        self._queue: queue.Queue = queue.Queue()

    def __call__(self, *args: tuple, **kwargs: dict) -> None:
        """Store the kwargs used in calls to the MethodCallsStore class.

        :param kwargs: The method parameters
        :type kwargs: dict
        """
        if kwargs:
            self._queue.put(kwargs)
        if args:
            self._queue.put(args)

    def wait_for_kwargs(self, expected_kwargs: dict, timeout: int = 3) -> bool:
        """Wait for a specific dict to arrive.

        :param expected_kwargs: The kwargs we're expecting
        :type expected_kwargs: dict
        :param timeout: How long to wait, defaults to 3
        :type timeout: int, optional
        :raises RuntimeError: When the expected value is not fuond
        :return: Whether it was found or not
        :rtype: bool
        """
        try:
            queue_values = []
            while True:
                queue_kwargs = self._queue.get(timeout=timeout)
                filtered_queue_kwargs = {k: v for k, v in queue_kwargs.items() if v is not None}
                queue_values.append(filtered_queue_kwargs)
                if filtered_queue_kwargs == expected_kwargs:
                    return True
        except queue.Empty as err:
            raise RuntimeError(f"Never got a {expected_kwargs}, but got {queue_values}") from err