"""This module provides an abstract component manager.

Base classes has marked this as deprecated since v.1.7.0.
This copy allows us to maintain the original structure of
the code base until the <x>EmitMixins are adopted.
"""

from __future__ import annotations

import logging
import threading
from collections.abc import Callable
from typing import Any

from ska_control_model import CommunicationStatus

CommunicationStatusCallbackType = Callable[[CommunicationStatus], None]


class BaseComponentManager:
    """An abstract base class for a component manager."""

    def __init__(
        self: BaseComponentManager,
        logger: logging.Logger,
        communication_state_callback: CommunicationStatusCallbackType | None = None,
        component_state_callback: Callable[..., None] | None = None,
        **state: Any,
    ) -> None:
        """Initialise a new ComponentManager instance.

        :param logger: the logger to be used by this manager
        :param communication_state_callback: callback to be called when
            the status of communications between the component manager
            and its component changes.
        :param component_state_callback: callback to be called when the
            monitored state of the component changes
        :param state: key/value pairs
        """
        self.logger = logger

        self._communication_state_lock = threading.Lock()
        self._communication_state = CommunicationStatus.DISABLED
        self._communication_state_callback = communication_state_callback

        self._component_state_lock = threading.Lock()
        self._component_state = dict(state)
        self._component_state_callback = component_state_callback

    def start_communicating(self: BaseComponentManager) -> None:
        """Establish communication with the component, then start monitoring.

        This is the place to do things like:

        * Initiate a connection to the component (if your communication
          is connection-oriented)
        * Subscribe to component events (if using "pull" model)
        * Start a polling loop to monitor the component (if using a
          "push" model)

        :raises NotImplementedError: Not implemented it's an abstract class
        """
        raise NotImplementedError(
            "'start_communicating' method must be implemented by "
            f"'{self.__class__.__name__}'. "
            "The parent 'BaseComponentManager' is an abstract base class."
        )

    def stop_communicating(self: BaseComponentManager) -> None:
        """Cease monitoring the component, and break off all communication with it.

        For example,

        * If you are communicating over a connection, disconnect.
        * If you have subscribed to events, unsubscribe.
        * If you are running a polling loop, stop it.

        :raises NotImplementedError: Not implemented it's an abstract class
        """
        raise NotImplementedError(
            "'stop_communicating' method must be implemented by "
            f"'{self.__class__.__name__}'. "
            "The parent 'BaseComponentManager' is an abstract base class."
        )

    @property
    def communication_state(self: BaseComponentManager) -> CommunicationStatus:
        """Return the communication status of this component manager.

        :return: status of the communication channel with the component.
        """
        return self._communication_state

    def _update_communication_state(
        self: BaseComponentManager,
        communication_state: CommunicationStatus,
    ) -> None:
        """Handle a change in communication status.

        This is a helper method for use by subclasses.

        :param communication_state: the new communication status of the
            component manager.

        :meta public:
        """
        with self._communication_state_lock:
            if self._communication_state != communication_state:
                self._communication_state = communication_state
                self._push_communication_state_update(communication_state)

    def _push_communication_state_update(
        self: BaseComponentManager, communication_state: CommunicationStatus
    ) -> None:
        if self._communication_state_callback is not None:
            self._communication_state_callback(communication_state)

    @property
    def component_state(self: BaseComponentManager) -> dict[str, Any]:
        """Return the state of this component manager's component.

        :return: state of the component.
        """
        return self._component_state

    def _update_component_state(
        self: BaseComponentManager,
        **kwargs: Any,
    ) -> None:
        """Handle a change in component state.

        This is a helper method for use by subclasses.

        :param kwargs: key/values for state

        :meta public:
        """
        callback_kwargs = {}

        with self._component_state_lock:
            for key, value in kwargs.items():
                if self._component_state[key] != value:
                    self._component_state[key] = value
                    callback_kwargs[key] = value
            if callback_kwargs:
                self._push_component_state_update(**callback_kwargs)

    def _push_component_state_update(self: BaseComponentManager, **kwargs: Any) -> None:
        if self._component_state_callback is not None:
            self._component_state_callback(**kwargs)
