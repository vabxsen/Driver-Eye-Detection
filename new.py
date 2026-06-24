import argparse
import sys
import time
from collections import deque
from pathlib import Path

import cv2
import mediapipe as mp
import numpy as np
from mediapipe.tasks.python.core.base_options import BaseOptions
from mediapipe.tasks.python.vision.core.vision_task_running_mode import VisionTaskRunningMode
from mediapipe.tasks.python.vision.face_landmarker import FaceLandmarker, FaceLandmarkerOptions


LEFT_EYE = [33, 160, 158, 133, 153, 144]
RIGHT_EYE = [362, 385, 387, 263, 373, 380]
POSE_LANDMARKS = [1, 33, 263, 61, 291, 199]
INNER_MOUTH = [78, 191, 80, 81, 82, 13, 312, 311, 310, 415, 308, 324, 318, 402, 317, 14, 87, 178, 88, 95]
MODEL_POINTS = np.array(
    [
        (0.0, 0.0, 0.0),          # Nose tip
        (-30.0, -30.0, -30.0),    # Left eye outer corner
        (30.0, -30.0, -30.0),     # Right eye outer corner
        (-25.0, 30.0, -20.0),     # Left mouth corner
        (25.0, 30.0, -20.0),      # Right mouth corner
        (0.0, 65.0, -45.0),       # Chin
    ],
    dtype=np.float64,
)


def resource_path(filename):
    base_path = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent))
    return base_path / filename


def create_face_landmarker():
    model_path = resource_path("face_landmarker.task")
    options = FaceLandmarkerOptions(
        base_options=BaseOptions(model_asset_path=str(model_path)),
        running_mode=VisionTaskRunningMode.VIDEO,
        num_faces=1,
        output_face_blendshapes=True,
    )
    return FaceLandmarker.create_from_options(options)


def eye_aspect_ratio(points, indices):
    pts = np.array([(points[i].x, points[i].y) for i in indices], dtype=np.float64)
    vertical_1 = np.linalg.norm(pts[1] - pts[5])
    vertical_2 = np.linalg.norm(pts[2] - pts[4])
    horizontal = np.linalg.norm(pts[0] - pts[3])
    return (vertical_1 + vertical_2) / (2.0 * horizontal)


def mouth_open_ratio(points):
    upper_lip = np.array([points[13].x, points[13].y], dtype=np.float64)
    lower_lip = np.array([points[14].x, points[14].y], dtype=np.float64)
    left_corner = np.array([points[61].x, points[61].y], dtype=np.float64)
    right_corner = np.array([points[291].x, points[291].y], dtype=np.float64)
    return np.linalg.norm(upper_lip - lower_lip) / np.linalg.norm(left_corner - right_corner)


def blendshape_scores(result):
    if not result.face_blendshapes:
        return {}
    return {
        category.category_name.lower(): category.score
        for category in result.face_blendshapes[0]
    }


def score(scores, *names):
    return max((scores.get(name.lower(), 0.0) for name in names), default=0.0)


def is_tongue_out(frame, points, mouth_ratio, min_ratio, color_threshold):
    if mouth_ratio < min_ratio:
        return False

    height, width = frame.shape[:2]
    polygon = np.array(
        [(int(points[i].x * width), int(points[i].y * height)) for i in INNER_MOUTH],
        dtype=np.int32,
    )
    if polygon.size == 0:
        return False

    mask = np.zeros((height, width), dtype=np.uint8)
    cv2.fillPoly(mask, [polygon], 255)
    mouth_pixels = cv2.countNonZero(mask)
    if mouth_pixels < 80:
        return False

    hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
    red_low = cv2.inRange(hsv, (0, 45, 50), (14, 255, 255))
    red_high = cv2.inRange(hsv, (160, 35, 50), (179, 255, 255))
    pink = cv2.inRange(hsv, (145, 25, 80), (179, 180, 255))
    tongue_mask = cv2.bitwise_and(cv2.bitwise_or(cv2.bitwise_or(red_low, red_high), pink), mask)

    return cv2.countNonZero(tongue_mask) / mouth_pixels >= color_threshold


def estimate_pitch(points, width, height):
    image_points = np.array(
        [(points[i].x * width, points[i].y * height) for i in POSE_LANDMARKS],
        dtype=np.float64,
    )
    focal_length = width
    camera_matrix = np.array(
        [[focal_length, 0, width / 2], [0, focal_length, height / 2], [0, 0, 1]],
        dtype=np.float64,
    )
    dist_coeffs = np.zeros((4, 1))
    success, rotation_vector, _ = cv2.solvePnP(
        MODEL_POINTS,
        image_points,
        camera_matrix,
        dist_coeffs,
        flags=cv2.SOLVEPNP_ITERATIVE,
    )
    if not success:
        return 0.0

    rotation_matrix, _ = cv2.Rodrigues(rotation_vector)
    angles, *_ = cv2.RQDecomp3x3(rotation_matrix)
    return float(angles[0])


def draw_status(frame, text, color):
    height, width = frame.shape[:2]
    cv2.rectangle(frame, (0, 0), (width, 96), (20, 20, 20), -1)
    cv2.putText(
        frame,
        text,
        (28, 62),
        cv2.FONT_HERSHEY_SIMPLEX,
        1.35,
        color,
        3,
        cv2.LINE_AA,
    )
    cv2.putText(
        frame,
        "Press Q to quit",
        (width - 210, height - 22),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.65,
        (235, 235, 235),
        2,
        cv2.LINE_AA,
    )


def run(args):
    face_landmarker = create_face_landmarker()
    cap = cv2.VideoCapture(args.camera)
    if not cap.isOpened():
        raise RuntimeError("Could not open webcam. Try --camera 1 if you have more than one camera.")

    ear_history = deque(maxlen=args.smoothing_frames)
    pitch_history = deque(maxlen=args.smoothing_frames)
    closed_since = None

    while True:
        ok, frame = cap.read()
        if not ok:
            break

        frame = cv2.flip(frame, 1)
        height, width = frame.shape[:2]
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        image = mp.Image(image_format=mp.ImageFormat.SRGB, data=np.ascontiguousarray(rgb))
        timestamp_ms = int(time.time() * 1000)
        result = face_landmarker.detect_for_video(image, timestamp_ms)

        status = "No face detected"
        color = (255, 255, 255)

        if result.face_landmarks:
            landmarks = result.face_landmarks[0]
            left_ear = eye_aspect_ratio(landmarks, LEFT_EYE)
            right_ear = eye_aspect_ratio(landmarks, RIGHT_EYE)
            ear = (left_ear + right_ear) / 2.0
            pitch = estimate_pitch(landmarks, width, height)
            mouth_ratio = mouth_open_ratio(landmarks)
            scores = blendshape_scores(result)
            smile_score = max(
                score(scores, "mouthSmileLeft", "mouth_smile_left"),
                score(scores, "mouthSmileRight", "mouth_smile_right"),
            )
            jaw_open_score = score(scores, "jawOpen", "jaw_open")
            pucker_score = score(scores, "mouthPucker", "mouth_pucker")
            tongue_out = is_tongue_out(
                frame,
                landmarks,
                mouth_ratio,
                args.tongue_mouth_open_ratio,
                args.tongue_color_threshold,
            )

            ear_history.append(ear)
            pitch_history.append(pitch)
            smooth_ear = float(np.mean(ear_history))
            smooth_pitch = float(np.mean(pitch_history))

            if smooth_ear < args.eye_closed_threshold:
                if closed_since is None:
                    closed_since = time.time()
                closed_duration = time.time() - closed_since
            else:
                closed_since = None
                closed_duration = 0.0

            if closed_duration >= args.eye_warning_seconds:
                status = "WARNING: EYES CLOSED"
                color = (0, 0, 255)
            elif smooth_pitch > args.look_down_threshold:
                status = "LOOKING DOWN"
                color = (0, 220, 255)
            elif tongue_out:
                status = "TONGUE OUT"
                color = (255, 0, 255)
            elif smile_score >= args.smile_threshold:
                status = "SMILING"
                color = (0, 255, 180)
            elif jaw_open_score >= args.mouth_open_threshold or mouth_ratio >= args.mouth_open_ratio:
                status = "MOUTH OPEN"
                color = (255, 180, 0)
            elif pucker_score >= args.pucker_threshold:
                status = "PUCKERING"
                color = (255, 120, 255)
            else:
                status = "EYE'S OPEN"
                color = (0, 220, 0)

            if args.debug:
                cv2.putText(
                    frame,
                    f"EAR: {smooth_ear:.3f}  Pitch: {smooth_pitch:.1f}",
                    (28, 128),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.7,
                    (255, 255, 255),
                    2,
                    cv2.LINE_AA,
                )
                cv2.putText(
                    frame,
                    f"Smile: {smile_score:.2f}  Jaw: {jaw_open_score:.2f}  Mouth: {mouth_ratio:.2f}  Pucker: {pucker_score:.2f}",
                    (28, 158),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.62,
                    (255, 255, 255),
                    2,
                    cv2.LINE_AA,
                )

        draw_status(frame, status, color)
        cv2.imshow("Driver Monitor", frame)

        if cv2.waitKey(1) & 0xFF == ord("q"):
            break

    cap.release()
    face_landmarker.close()
    cv2.destroyAllWindows()


def parse_args():
    parser = argparse.ArgumentParser(description="Simple webcam driver monitoring prototype.")
    parser.add_argument("--camera", type=int, default=0, help="Webcam index. Default: 0")
    parser.add_argument("--eye-closed-threshold", type=float, default=0.21)
    parser.add_argument("--eye-warning-seconds", type=float, default=0.35)
    parser.add_argument("--look-down-threshold", type=float, default=13.0)
    parser.add_argument("--smile-threshold", type=float, default=0.45)
    parser.add_argument("--mouth-open-threshold", type=float, default=0.45)
    parser.add_argument("--mouth-open-ratio", type=float, default=0.35)
    parser.add_argument("--pucker-threshold", type=float, default=0.45)
    parser.add_argument("--tongue-mouth-open-ratio", type=float, default=0.28)
    parser.add_argument("--tongue-color-threshold", type=float, default=0.22)
    parser.add_argument("--smoothing-frames", type=int, default=5)
    parser.add_argument("--debug", action="store_true", help="Show EAR and pitch values for tuning.")
    return parser.parse_args()


if __name__ == "__main__":
    run(parse_args())