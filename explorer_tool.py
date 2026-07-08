#!/usr/bin/env python3

"""
    Cozmo Explorer Tool - web interface to drive Cozmo via PyCozmo (no mobile app).

    Created by: GrinningHermit
    PyCozmo migration: direct Wi-Fi connection to the robot
"""
import datetime
import os
import queue
import random
import logging
import atexit
import time
import threading
from flask import Flask, render_template, request, jsonify, send_from_directory

import flask_socket_helpers
from pycozmo_assets import AssetDownloadError, ensure_assets
from robot_session import RobotSession, connect_robot
import event_monitor
from viewer import viewer, activate_viewer_if_enabled, set_robot_session, pil_installed
from remote_control import remote_control, activate_controls
from animate import animate, init_animate

flask_socketio_installed = False
try:
    from flask_socketio import SocketIO, emit
    flask_socketio_installed = True
except ImportError:
    logging.warning(
        'Cannot import flask_socketio: pip install flask-socketio\n'
        'Program runs without event monitoring in the browser.'
    )

thread = None
robot_session = None
cozmoEnabled = False
active_viewer = False
lists = ['', '', '']
robot_connect_lock = threading.Lock()
RECONNECT_INTERVAL = 7.0
RECONNECT_TIMEOUT = 10.0
async_mode = 'threading'
app = Flask(__name__)
app.config['SECRET_KEY'] = 'secret!'
app.config['TEMPLATES_AUTO_RELOAD'] = True
app.config['SEND_FILE_MAX_AGE_DEFAULT'] = 0
app.register_blueprint(viewer)
app.register_blueprint(remote_control)
app.register_blueprint(animate)

abspath = os.path.abspath(__file__)
dname = os.path.dirname(abspath)
os.chdir(dname)

ENGINE_JS_PATH = os.path.join(dname, 'static', 'js', 'engine.js')
try:
    ASSET_VERSION = str(int(os.path.getmtime(ENGINE_JS_PATH)))
except OSError:
    ASSET_VERSION = str(random.randrange(1000000000, 9999999999))

SERVER_BOOT_ID = str(time.time_ns())

q = queue.Queue()

if flask_socketio_installed:
    socketio = SocketIO(app, async_mode=async_mode, cors_allowed_origins='*')

    def print_queue(qval):
        while qval.qsize() > 0:
            timestamp = '{:%H:%M:%S.%f}'.format(datetime.datetime.now())
            message = qval.get()
            print(timestamp + ' -> ' + message)
            socketio.emit('my_response',
                          {'data': message, 'type': 'event', 'time': timestamp})

    def background_thread(qval):
        while True:
            if not qval.empty():
                print_queue(qval)
            socketio.sleep(.1)

    @socketio.on('connect')
    def test_connect():
        global thread
        if thread is None:
            thread = socketio.start_background_task(background_thread, q)
        emit('my_response', {
            'data': 'SERVER: websocket connection established. Displaying robot events.'
        })


@app.after_request
def set_no_cache_headers(response):
    if request.path == '/' or request.path.startswith('/static/') or request.path.startswith('/app/') or request.path in ('/ui-bootstrap', '/api/ui-bootstrap', '/health'):
        response.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, max-age=0'
        response.headers['Pragma'] = 'no-cache'
        response.headers['Expires'] = '0'
    return response


@app.route('/ui-bootstrap')
@app.route('/api/ui-bootstrap')
def ui_bootstrap():
    global lists
    if cozmoEnabled and robot_session is not None and not lists[0]:
        lists = robot_session.get_animation_lists()
    payload = {
        'anims_raw': lists[0],
        'triggers_raw': lists[1],
        'behaviors_raw': lists[2],
        'robotConnected': cozmoEnabled,
        'hasCamera': active_viewer,
        'hasPillow': pil_installed,
        'hasSocketIO': flask_socketio_installed,
        'engineBuild': ASSET_VERSION,
        'serverBootId': SERVER_BOOT_ID,
    }
    return jsonify(payload)


def _serve_js(filename):
    response = send_from_directory(
        os.path.join(dname, 'static', 'js'),
        filename,
        mimetype='application/javascript',
    )
    response.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, max-age=0'
    response.headers['Pragma'] = 'no-cache'
    response.headers['Expires'] = '0'
    return response


@app.route('/app/engine.js')
@app.route('/static/js/engine.js')
def serve_engine_js():
    return _serve_js('engine.js')


@app.route('/app/event-monitor.js')
@app.route('/static/js/event-monitor.js')
def serve_event_monitor_js():
    return _serve_js('event-monitor.js')


@app.route('/health')
def health():
    return jsonify({
        'ok': True,
        'engineBuild': ASSET_VERSION,
        'serverBootId': SERVER_BOOT_ID,
        'robotConnected': cozmoEnabled,
        'animCount': len(lists[0].split(',')) if lists[0] else 0,
        'hasPillow': pil_installed,
        'hasSocketIO': flask_socketio_installed,
    })


@app.route('/')
def index():
    page_id = ASSET_VERSION
    return render_template(
        'index.html',
        randomID=page_id,
        serverBootId=SERVER_BOOT_ID,
        hasSocketIO=flask_socketio_installed,
        hasPillow=pil_installed,
        hasCamera=active_viewer,
        robotConnected=cozmoEnabled,
    )


def start_server():
    if flask_socketio_installed:
        flask_socket_helpers.run_flask(socketio, app)
    else:
        flask_socket_helpers.run_flask(None, app)


def try_connect_robot(timeout=30.0, quiet=False, late_connect=False):
    global robot_session, lists, active_viewer, cozmoEnabled
    with robot_connect_lock:
        if cozmoEnabled and robot_session is not None:
            return True
        try:
            robot_session = connect_robot(event_queue=q, timeout=timeout)
            set_robot_session(robot_session)
            lists = init_animate(robot_session)
            active_viewer = activate_viewer_if_enabled(robot_session)
            activate_controls(robot_session)
            cozmoEnabled = True
            if late_connect:
                print("Cozmo connected (late connect).")
            else:
                print("Cozmo connected via PyCozmo. Open http://127.0.0.1:5000/")
            print("Lists: {} animations, {} triggers, {} behaviors".format(
                len(lists[0].split(',')) if lists[0] else 0,
                len(lists[1].split(',')) if lists[1] else 0,
                len(lists[2].split(',')) if lists[2] else 0,
            ))
            return True
        except Exception as exc:
            if not quiet:
                logging.error("PyCozmo connection failed: %s", exc)
                print("\nCould not connect to Cozmo: {}".format(exc))
                print("Check that:")
                print("  1. Cozmo is powered on")
                print("  2. The PC is connected to the robot Wi-Fi (often 172.31.1.1)")
                print("  3. Cozmo resources are installed (re-run explorer_tool.py to auto-download)")
            cozmoEnabled = False
            robot_session = None
            set_robot_session(None)
            return False


def reconnect_loop():
    while not cozmoEnabled:
        time.sleep(RECONNECT_INTERVAL)
        if cozmoEnabled:
            break
        try_connect_robot(timeout=RECONNECT_TIMEOUT, quiet=True, late_connect=True)


def start_reconnect_thread():
    reconnect_thread = threading.Thread(
        target=reconnect_loop,
        name='cozmo-reconnect',
        daemon=True,
    )
    reconnect_thread.start()


def cleanup():
    global robot_session, cozmoEnabled
    with robot_connect_lock:
        if robot_session:
            robot_session.shutdown()
            robot_session = None
        cozmoEnabled = False
        set_robot_session(None)


atexit.register(cleanup)


def main():
    try:
        ensure_assets()
    except AssetDownloadError as exc:
        print("\nCould not download PyCozmo resources: {}".format(exc))
        print("You can also run manually: pycozmo_resources.py download (see README)")
        return
    except Exception as exc:
        print("\nUnexpected error while checking PyCozmo resources: {}".format(exc))
        return

    if not try_connect_robot():
        print("\nStarting web UI without robot (demo mode).")
        print("Connect the PC to Cozmo Wi-Fi; connection will be retried automatically.")
        start_reconnect_thread()
    print("UI asset version: {}".format(ASSET_VERSION))
    print("UI server boot id: {}".format(SERVER_BOOT_ID))
    print("Deps: Pillow={}, SocketIO={}".format(pil_installed, flask_socketio_installed))
    with app.test_client() as client:
        health_status = client.get('/health').status_code
        bootstrap_status = client.get('/ui-bootstrap').status_code
    print("Routes: /health={}, /ui-bootstrap={}".format(health_status, bootstrap_status))
    if bootstrap_status != 200:
        print("ERROR: bootstrap route unavailable - make sure only one server is running on port 5000")

    try:
        start_server()
    except KeyboardInterrupt:
        print("\nExit requested by user")
    finally:
        cleanup()


if __name__ == '__main__':
    main()
