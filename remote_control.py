"""

Remote control for Cozmo via PyCozmo.

"""

import json
from flask import Blueprint, request

remote_control = Blueprint('remote_control', __name__)

robot = None
remote_control_cozmo = None

_is_mouse_look_enabled_by_default = False


class RemoteControlCozmo:
    def __init__(self, coz):
        self.cozmo = coz
        self.drive_forwards = 0
        self.drive_back = 0
        self.turn_left = 0
        self.turn_right = 0
        self.lift_up = 0
        self.lift_down = 0
        self.head_up = 0
        self.head_down = 0
        self.go_fast = 0
        self.go_slow = 0
        self.is_mouse_look_enabled = _is_mouse_look_enabled_by_default
        self.mouse_dir = 0
        self.action_queue = []
        self.text_to_say = "Hi I'm Cozmo"

    def handle_key(self, key_code, is_shift_down, is_ctrl_down, is_alt_down, is_key_down):
        was_go_fast = self.go_fast
        was_go_slow = self.go_slow
        self.go_fast = is_shift_down
        self.go_slow = is_alt_down
        speed_changed = (was_go_fast != self.go_fast) or (was_go_slow != self.go_slow)

        update_driving = True
        if key_code == ord('W'):
            self.drive_forwards = is_key_down
        elif key_code == ord('S'):
            self.drive_back = is_key_down
        elif key_code == ord('A'):
            self.turn_left = is_key_down
        elif key_code == ord('D'):
            self.turn_right = is_key_down
        else:
            if not speed_changed:
                update_driving = False

        update_lift = True
        if key_code == ord('R'):
            self.lift_up = is_key_down
        elif key_code == ord('F'):
            self.lift_down = is_key_down
        else:
            if not speed_changed:
                update_lift = False

        update_head = True
        if key_code == ord('Q'):
            self.head_up = is_key_down
        elif key_code == ord('E'):
            self.head_down = is_key_down
        else:
            if not speed_changed:
                update_head = False

        if update_driving:
            self.update_driving()
        if update_head:
            self.update_head()
        if update_lift:
            self.update_lift()

        if not is_key_down and key_code == ord(' '):
            self.say_text(self.text_to_say)

    def func_to_name(self, func):
        if func == self.try_say_text:
            return "say_text"
        return "UNKNOWN"

    def action_to_text(self, action):
        func, args = action
        return self.func_to_name(func) + "( " + str(args) + " )"

    def queue_action(self, new_action):
        if len(self.action_queue) > 10:
            self.action_queue.pop(0)
        self.action_queue.append(new_action)

    def try_say_text(self, text_to_say):
        # PyCozmo does not support official TTS yet.
        print("say_text (not supported by PyCozmo): {}".format(text_to_say))
        return True

    def say_text(self, text_to_say):
        self.queue_action((self.try_say_text, text_to_say))
        self.update()

    def update(self):
        if len(self.action_queue) > 0:
            queued_action, action_args = self.action_queue[0]
            if queued_action(action_args):
                self.action_queue.pop(0)

    def pick_speed(self, fast_speed, mid_speed, slow_speed):
        if self.go_fast and not self.go_slow:
            return fast_speed
        if self.go_slow:
            return slow_speed
        return mid_speed

    def update_lift(self):
        lift_speed = self.pick_speed(8, 4, 2)
        lift_vel = (self.lift_up - self.lift_down) * lift_speed
        self.cozmo.move_lift(lift_vel)

    def update_head(self):
        if not self.is_mouse_look_enabled:
            head_speed = self.pick_speed(2, 1, 0.5)
            head_vel = (self.head_up - self.head_down) * head_speed
            self.cozmo.move_head(head_vel)

    def update_driving(self):
        drive_dir = (self.drive_forwards - self.drive_back)
        if drive_dir > 0.1 and self.cozmo.is_on_charger:
            try:
                self.cozmo.drive_off_charger_contacts()
            except Exception:
                pass

        turn_dir = (self.turn_right - self.turn_left) + self.mouse_dir
        if drive_dir < 0:
            turn_dir = -turn_dir

        forward_speed = self.pick_speed(150, 75, 50)
        turn_speed = self.pick_speed(100, 50, 30)
        l_wheel_speed = (drive_dir * forward_speed) + (turn_speed * turn_dir)
        r_wheel_speed = (drive_dir * forward_speed) - (turn_speed * turn_dir)
        self.cozmo.drive_wheels(l_wheel_speed, r_wheel_speed, l_wheel_speed * 4, r_wheel_speed * 4)


@remote_control.route('/updateCozmo', methods=['POST'])
def handle_updateCozmo():
    if remote_control_cozmo:
        remote_control_cozmo.update()
    return ""


def handle_key_event(key_request, is_key_down):
    message = json.loads(key_request.data.decode("utf-8"))
    if remote_control_cozmo:
        remote_control_cozmo.handle_key(
            key_code=message['keyCode'],
            is_shift_down=message['hasShift'],
            is_ctrl_down=message['hasCtrl'],
            is_alt_down=message['hasAlt'],
            is_key_down=is_key_down,
        )
    return ""


@remote_control.route('/keydown', methods=['POST'])
def handle_keydown():
    return handle_key_event(request, is_key_down=True)


@remote_control.route('/keyup', methods=['POST'])
def handle_keyup():
    return handle_key_event(request, is_key_down=False)


@remote_control.route('/setHeadlightEnabled', methods=['POST'])
def handle_setHeadlightEnabled():
    message = json.loads(request.data.decode("utf-8"))
    if remote_control_cozmo:
        remote_control_cozmo.cozmo.set_head_light(enable=message['isHeadlightEnabled'])
    return ""


@remote_control.route('/setFreeplayEnabled', methods=['POST'])
def handle_setFreeplayEnabled():
    message = json.loads(request.data.decode("utf-8"))
    if remote_control_cozmo:
        if message['isFreeplayEnabled']:
            remote_control_cozmo.cozmo.start_freeplay_behaviors()
        else:
            remote_control_cozmo.cozmo.stop_freeplay_behaviors()
    return ""


@remote_control.route('/getDebugInfo', methods=['POST'])
def handle_getDebugInfo():
    if remote_control_cozmo:
        action_queue_text = ""
        i = 1
        for action in remote_control_cozmo.action_queue:
            action_queue_text += str(i) + ": " + remote_control_cozmo.action_to_text(action) + "<br>"
            i += 1
        return 'Action Queue:<br>' + action_queue_text
    return ""


def activate_controls(session):
    global robot
    global remote_control_cozmo
    robot = session
    remote_control_cozmo = RemoteControlCozmo(session)
