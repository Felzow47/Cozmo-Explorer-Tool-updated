"""

Event Monitor for Cozmo via PyCozmo.

"""

import threading
import time

from pycozmo import event

robot = None
q = None
thread_running = False


class CheckState(threading.Thread):
    def __init__(self, thread_id, name, _q):
        threading.Thread.__init__(self)
        self.threadID = thread_id
        self.name = name
        self.q = _q

    def run(self):
        delay = 10
        is_picked_up = False
        is_falling = False
        is_on_charger = False
        while thread_running:
            if robot.is_picked_up:
                delay = 0
                if not is_picked_up:
                    is_picked_up = True
                    self.q.put('pycozmo.robot.Robot.is_picked_up: True')
            elif is_picked_up and delay > 9:
                is_picked_up = False
                self.q.put('pycozmo.robot.Robot.is_picked_up: False')
            elif delay <= 9:
                delay += 1

            if robot.is_falling:
                if not is_falling:
                    is_falling = True
                    self.q.put('pycozmo.robot.Robot.is_falling: True')
            elif is_falling:
                is_falling = False
                self.q.put('pycozmo.robot.Robot.is_falling: False')

            if robot.is_on_charger:
                if not is_on_charger:
                    is_on_charger = True
                    self.q.put('pycozmo.robot.Robot.is_on_charger: True')
            elif is_on_charger:
                is_on_charger = False
                self.q.put('pycozmo.robot.Robot.is_on_charger: False')

            time.sleep(0.1)


def _log(evt_name, detail=''):
    if q is not None:
        msg = evt_name
        if detail:
            msg += ' ' + detail
        q.put(msg)


def _make_handler(evt_name):
    def handler(cli, *args, **kwargs):
        detail = ''
        if args:
            detail = str(args[0])
        if kwargs:
            detail += ' ' + str(set(kwargs.keys()))
        _log(evt_name, detail.strip())
    return handler


def monitor(session, _q, evt_class=None):
    global robot, q, thread_running
    robot = session
    q = _q
    thread_running = True
    cli = session.cli

    handlers = {
        event.EvtAnimationCompleted: _make_handler('EvtAnimationCompleted'),
        event.EvtBehaviorDone: _make_handler('EvtBehaviorDone'),
        event.EvtReactionTrigger: _make_handler('EvtReactionTrigger'),
        event.EvtRobotPickedUpChange: _make_handler('EvtRobotPickedUpChange'),
        event.EvtRobotFallingChange: _make_handler('EvtRobotFallingChange'),
        event.EvtRobotOnChargerChange: _make_handler('EvtRobotOnChargerChange'),
        event.EvtRobotChargingChange: _make_handler('EvtRobotChargingChange'),
        event.EvtCliffDetectedChange: _make_handler('EvtCliffDetectedChange'),
        event.EvtRobotCarryingBlockChange: _make_handler('EvtRobotCarryingBlockChange'),
        event.EvtRobotAnimatingChange: _make_handler('EvtRobotAnimatingChange'),
        event.EvtRobotMovingChange: _make_handler('EvtRobotMovingChange'),
        event.EvtRobotOrientationChange: _make_handler('EvtRobotOrientationChange'),
        event.EvtRobotReady: _make_handler('EvtRobotReady'),
    }

    if evt_class is not None:
        if evt_class in handlers:
            cli.add_handler(evt_class, handlers[evt_class])
        return

    for evt_type, handler in handlers.items():
        cli.add_handler(evt_type, handler)

    thread_is_state_changed = CheckState(1, 'ThreadCheckState', q)
    thread_is_state_changed.start()


def unmonitor(session, evt_class=None):
    global thread_running
    thread_running = False
