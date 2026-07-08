"""
PyCozmo session - direct robot connection without phone or Anki SDK.
"""

import logging
import threading

import pycozmo
from pycozmo import event, util, robot as pycozmo_robot
from pycozmo.brain import Brain

logger = logging.getLogger(__name__)


class _VectorAdapter:
    def __init__(self, vector):
        self.x_y_z = (vector.x, vector.y, vector.z)


class RobotSession:
    """PyCozmo adapter for the Explorer Tool interface."""

    def __init__(self):
        self.cli = None
        self.brain = None
        self._behaviors = {}
        self._active_behavior = None
        self._freeplay_running = False
        self._lock = threading.Lock()
        self._latest_image = None

    def _on_camera_image(self, cli, image):
        del cli
        self._latest_image = image

    @property
    def conn(self):
        return self

    @property
    def anim_names(self):
        if self.cli is None:
            return set()
        return self.cli.get_anim_names()

    @property
    def pose(self):
        return self.cli.pose if self.cli else None

    @property
    def accelerometer(self):
        return _VectorAdapter(self.cli.accel) if self.cli else _VectorAdapter(util.Vector3(0, 0, 0))

    @property
    def gyro(self):
        return _VectorAdapter(self.cli.gyro) if self.cli else _VectorAdapter(util.Vector3(0, 0, 0))

    @property
    def is_on_charger(self):
        if self.cli is None:
            return False
        return bool(self.cli.robot_status & pycozmo_robot.RobotStatusFlag.IS_ON_CHARGER)

    @property
    def is_picked_up(self):
        return bool(self.cli.robot_picked_up) if self.cli else False

    @property
    def is_falling(self):
        if self.cli is None:
            return False
        return bool(self.cli.robot_status & pycozmo_robot.RobotStatusFlag.IS_FALLING)

    @property
    def latest_image(self):
        return self._latest_image

    @property
    def world(self):
        return self

    @property
    def image_annotator(self):
        return self

    @property
    def camera(self):
        return self

    @property
    def annotation_enabled(self):
        return getattr(self, '_annotation_enabled', False)

    @annotation_enabled.setter
    def annotation_enabled(self, value):
        self._annotation_enabled = bool(value)

    @property
    def image_stream_enabled(self):
        return getattr(self, '_camera_enabled', False)

    @image_stream_enabled.setter
    def image_stream_enabled(self, value):
        self._camera_enabled = bool(value)
        if self.cli and value:
            self.cli.enable_camera(enable=True)

    def add_annotator(self, name, annotator):
        self._annotator = annotator

    def connect(self, timeout=30.0):
        pycozmo.util.check_assets()
        self.cli = pycozmo.Client()
        self.cli.start()
        self.cli.connect()
        self.cli.wait_for_robot(timeout=timeout)
        self.cli.load_anims()
        self.cli.add_handler(event.EvtNewRawCameraImage, self._on_camera_image)
        self.brain = Brain(self.cli)
        self._behaviors = self.brain.behaviors
        self.cli.enable_camera(enable=True)
        anim_count = len(self.cli.get_anim_names())
        trigger_count = len(self.cli.animation_groups)
        behavior_count = len(self._behaviors)
        print("Resources loaded: {} animations, {} triggers, {} behaviors".format(
            anim_count, trigger_count, behavior_count))
        logger.info("Connected to Cozmo via PyCozmo (no mobile app).")

    def shutdown(self):
        if self.brain:
            try:
                self.stop_freeplay_behaviors()
            except Exception:
                pass
        if self.cli:
            try:
                self.cli.disconnect()
            except Exception:
                pass
            try:
                self.cli.stop()
            except Exception:
                pass
        self.cli = None
        self.brain = None

    def get_animation_lists(self):
        animations = sorted(self.cli.get_anim_names())
        triggers = sorted(self.cli.animation_groups.keys())
        behaviors = sorted(self._behaviors.keys())
        return [
            ','.join(animations),
            ','.join(triggers),
            ','.join(behaviors),
        ]

    def drive_wheels(self, lwheel_speed, rwheel_speed, lwheel_acc=0.0, rwheel_acc=0.0):
        with self._lock:
            self.cli.drive_wheels(lwheel_speed, rwheel_speed, lwheel_acc, rwheel_acc)

    def move_head(self, speed):
        with self._lock:
            self.cli.move_head(speed)

    def move_lift(self, speed):
        with self._lock:
            self.cli.move_lift(speed)

    def set_head_light(self, enable=True):
        with self._lock:
            self.cli.set_head_light(enable)

    def drive_off_charger_contacts(self):
        with self._lock:
            self.cli.drive_wheels(100.0, 100.0, 500.0, 500.0, duration=1.5)

    def start_freeplay_behaviors(self):
        if self.brain and not self._freeplay_running:
            self.brain.start()
            self._freeplay_running = True

    def stop_freeplay_behaviors(self):
        if self.brain and self._freeplay_running:
            self.brain.stop()
            self.brain.deactivate_behavior()
            self._freeplay_running = False

    def play_anim(self, name):
        with self._lock:
            self.cli.play_anim(name)

    def wait_for_anim_completed(self, timeout=120.0):
        self.cli.wait_for(event.EvtAnimationCompleted, timeout=timeout)

    def play_anim_trigger(self, trigger_name):
        with self._lock:
            self.cli.play_anim_group(trigger_name)

    def start_behavior(self, behavior_id):
        behavior = self._behaviors.get(behavior_id)
        if behavior is None:
            raise ValueError("Unknown behavior: {}".format(behavior_id))
        with self._lock:
            if self._active_behavior:
                self.cli.deactivate_behavior(self._active_behavior)
            self._active_behavior = behavior
            self.cli.activate_behavior(behavior)
        return behavior

    def stop_active_behavior(self):
        with self._lock:
            if self._active_behavior:
                self.cli.deactivate_behavior(self._active_behavior)
                behavior_id = self._active_behavior.get_id()
                self._active_behavior = None
                return behavior_id
        return None

    def abort_all_actions(self):
        with self._lock:
            self.cli.cancel_anim()
        self.stop_active_behavior()

    def go_to_pose(self, pose):
        if pose is not None:
            with self._lock:
                self.cli.go_to_pose(pose)


def connect_robot(event_queue=None, timeout=30.0):
    session = RobotSession()
    try:
        session.connect(timeout=timeout)
        if event_queue is not None:
            from event_monitor import monitor
            monitor(session, event_queue)
        return session
    except Exception:
        session.shutdown()
        raise
