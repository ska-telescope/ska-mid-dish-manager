"""Adapted SubmittedSlowCommand so that `do` always returns"""
import functools

from ska_tango_base.commands import ResultCode, SubmittedSlowCommand


#  pylint: disable=too-few-public-methods
class NestedSubmittedSlowCommand(SubmittedSlowCommand):
    """Adapted `do` method"""

    def do(self, *args, **kwargs):
        """
        Updated stateless hook for command functionality.

        Returns ResultCode, command_id

        :param args: positional args to the component manager method
        :param kwargs: keyword args to the component manager method

        :return: A tuple containing (ResultCode, command_id)
        :rtype: (ResultCode, str)
        """
        command_id = self._command_tracker.new_command(
            self._command_name, completed_callback=self._completed
        )
        method = getattr(self._component_manager, self._method_name)
        method(
            *args,
            functools.partial(
                self._command_tracker.update_command_info, command_id
            ),
            **kwargs,
        )

        return ResultCode.OK, command_id
