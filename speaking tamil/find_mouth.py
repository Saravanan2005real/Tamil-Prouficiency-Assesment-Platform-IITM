import cv2
import mediapipe as mp

mp_face_mesh = mp.solutions.face_mesh
img = cv2.imread('avatar.png')
h, w = img.shape[:2]

with mp_face_mesh.FaceMesh(static_image_mode=True, max_num_faces=1) as face_mesh:
    results = face_mesh.process(cv2.cvtColor(img, cv2.COLOR_BGR2RGB))
    if results.multi_face_landmarks:
        face = results.multi_face_landmarks[0]
        
        # Get mouth bounds using upper and lower lips
        # 13 is inner upper lip, 14 is inner lower lip
        # 0 is upper lip top edge, 17 is lower lip bottom edge
        # 61 is left mouth corner, 291 is right mouth corner
        
        top_y = face.landmark[0].y
        bottom_y = face.landmark[17].y
        left_x = face.landmark[61].x
        right_x = face.landmark[291].x
        
        print(f"MOUTH_TOP_PCT: {top_y*100:.2f}")
        print(f"MOUTH_BOTTOM_PCT: {bottom_y*100:.2f}")
        print(f"MOUTH_LEFT_PCT: {left_x*100:.2f}")
        print(f"MOUTH_RIGHT_PCT: {right_x*100:.2f}")
        print(f"MOUTH_CENTER_X: {(left_x + right_x)/2 * 100:.2f}")
        print(f"MOUTH_CENTER_Y: {(top_y + bottom_y)/2 * 100:.2f}")
    else:
        print("No face detected")
