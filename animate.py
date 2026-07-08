import json
from flask import Blueprint, request

animate = Blueprint('animate', __name__)

robot = None
return_to_pose = False
animations = ''
triggers = ''
behaviors = ''
active_behavior_name = None
pose = None


@animate.route('/toggle_pose', methods=['POST'])
def toggle_pose():
    global return_to_pose
    return_to_pose = not return_to_pose
    print('return_to_pose is set to: ' + str(return_to_pose))
    return str(return_to_pose)


@animate.route('/play_animation', methods=['POST'])
def play_animation():
    global pose
    animation = json.loads(request.data.decode('utf-8'))
    pose = robot.pose
    robot.play_anim(animation)
    robot.wait_for_anim_completed()
    print("Animation '{}' finished".format(animation))
    check_pose_return()
    return 'true'


@animate.route('/play_trigger', methods=['POST'])
def play_trigger():
    global pose
    trigger = json.loads(request.data.decode('utf-8'))
    pose = robot.pose
    robot.play_anim_trigger(trigger)
    robot.wait_for_anim_completed()
    print("Trigger '{}' finished".format(trigger))
    check_pose_return()
    return 'true'


@animate.route('/play_behavior', methods=['POST'])
def play_behavior():
    global pose, active_behavior_name
    behavior = json.loads(request.data.decode('utf-8'))
    pose = robot.pose
    robot.start_behavior(behavior)
    active_behavior_name = behavior
    print("Behavior '{}' started".format(behavior))
    return 'true'


@animate.route('/stop', methods=['POST'])
def stop():
    global active_behavior_name
    if active_behavior_name:
        stopped = robot.stop_active_behavior()
        print("behavior '{}' stopped".format(stopped))
        active_behavior_name = None
        check_pose_return()
    else:
        robot.abort_all_actions()
    return 'false'


def check_pose_return():
    if return_to_pose and pose is not None:
        robot.go_to_pose(pose)
        print('Cozmo returning to pose he had before animation started')


def init_animate(session):
    global robot, animations, triggers, behaviors
    robot = session
    lists = session.get_animation_lists()
    animations, triggers, behaviors = lists
    return lists
