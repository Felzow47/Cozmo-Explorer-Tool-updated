"""

Viewer / camera feed for Cozmo via PyCozmo.

"""

import json
from io import BytesIO
import logging
from flask import request, make_response, send_file, Blueprint

pil_installed = False
try:
    from PIL import Image, ImageDraw, ImageFont
    pil_installed = True
except ImportError:
    logging.warning("Cannot import from PIL: Do `pip3 install --user Pillow` to install")

viewer = Blueprint('viewer', __name__)

DEBUG_ANNOTATIONS_DISABLED = 0
DEBUG_ANNOTATIONS_ENABLED_VISION = 1
DEBUG_ANNOTATIONS_ENABLED_ALL = 2

robot = None
cozmoEnabled = True
_display_debug_annotations = DEBUG_ANNOTATIONS_DISABLED


def set_robot_session(session):
    global robot, cozmoEnabled
    robot = session
    cozmoEnabled = session is not None


def create_default_image(image_width, image_height, do_gradient=False):
    image_bytes = bytearray([0x70, 0x70, 0x70]) * image_width * image_height
    if do_gradient:
        i = 0
        for y in range(image_height):
            for x in range(image_width):
                image_bytes[i] = int(255.0 * (x / image_width))
                image_bytes[i + 1] = int(255.0 * (y / image_height))
                image_bytes[i + 2] = 0
                i += 3
    return Image.frombytes('RGB', (image_width, image_height), bytes(image_bytes))


if pil_installed:
    _default_camera_image = create_default_image(320, 240)


def annotate_image(image, scale=2):
    if robot is None or image is None:
        return image
    annotated = image.copy()
    if scale != 1:
        annotated = annotated.resize((image.width * scale, image.height * scale), Image.NEAREST)
    draw = ImageDraw.Draw(annotated)
    try:
        font = ImageFont.truetype('static/fonts/LiberationSans-Bold.ttf', 15)
    except OSError:
        font = ImageFont.load_default()
    y = 5

    def print_line(text_line):
        nonlocal y
        draw.text((10, y + 1), text_line, fill='#000000', font=font)
        draw.text((10, y), text_line, fill='#ffffff', font=font)
        y += 15

    pose = robot.pose
    if pose:
        print_line('Pose: Pos = <%.1f, %.1f, %.1f>' % pose.position.x_y_z)
        print_line('Pose: Rot quat = <%.1f, %.1f, %.1f, %.1f>' % pose.rotation.q0_q1_q2_q3)
        print_line('Pose: angle_z = %.1f' % pose.rotation.angle_z.degrees)
        print_line('Pose: origin_id: %s' % pose.origin_id)
    accel = robot.accelerometer.x_y_z
    gyro = robot.gyro.x_y_z
    print_line('Accelmtr: <%.1f, %.1f, %.1f>' % accel)
    print_line('Gyro: <%.1f, %.1f, %.1f>' % gyro)
    return annotated


@viewer.route("/cozmoImage")
def handle_cozmoImage():
    try:
        if cozmoEnabled and pil_installed:
            if robot is None:
                return serve_pil_image(_default_camera_image, serve_as_jpeg=True)
            image = robot.latest_image
            if image:
                if _display_debug_annotations != DEBUG_ANNOTATIONS_DISABLED:
                    image = annotate_image(image, scale=2)
                return serve_pil_image(image, serve_as_jpeg=True)
            return serve_pil_image(_default_camera_image, serve_as_jpeg=True)
    except Exception as exc:
        logging.error("cozmoImage error: %s", exc)
    return serve_pil_image(_default_camera_image, serve_as_jpeg=True)


@viewer.route('/setAreDebugAnnotationsEnabled', methods=['POST'])
def handle_setAreDebugAnnotationsEnabled():
    message = json.loads(request.data.decode("utf-8"))
    global _display_debug_annotations
    _display_debug_annotations = message['areDebugAnnotationsEnabled']
    if robot is not None:
        robot.annotation_enabled = _display_debug_annotations != DEBUG_ANNOTATIONS_DISABLED
    return ""


def make_uncached_response(in_file):
    response = make_response(in_file)
    response.headers['Pragma-Directive'] = 'no-cache'
    response.headers['Cache-Directive'] = 'no-cache'
    response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
    response.headers['Pragma'] = 'no-cache'
    response.headers['Expires'] = '0'
    return response


def serve_pil_image(pil_img, serve_as_jpeg=False, jpeg_quality=70):
    img_io = BytesIO()
    if serve_as_jpeg:
        pil_img.save(img_io, 'JPEG', quality=jpeg_quality)
        img_io.seek(0)
        return make_uncached_response(send_file(img_io, mimetype='image/jpeg'))
    pil_img.save(img_io, 'PNG')
    img_io.seek(0)
    return make_uncached_response(send_file(img_io, mimetype='image/png'))


def activate_viewer_if_enabled(session):
    global robot
    robot = session
    if pil_installed and session is not None:
        session.image_stream_enabled = True
        return True
    return False
