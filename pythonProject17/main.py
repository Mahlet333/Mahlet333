from flask import Flask, render_template, Response
from flask_socketio import SocketIO, emit
import cv2

app = Flask(__name__)
socketio = SocketIO(app)

face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')
eye_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_eye.xml')

cap = cv2.VideoCapture(0)

def detect_attention(frame):
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    faces = face_cascade.detectMultiScale(gray, 1.3, 5)
    for (x, y, w, h) in faces:
        cv2.rectangle(frame, (x, y), (x + w, y + h), (255, 0, 0), 2)
        roi_gray = gray[y:y + h, x:x + w]
        roi_color = frame[y:y + h, x:x + w]
        eyes = eye_cascade.detectMultiScale(roi_gray)
        if len(eyes) == 2:
            attention_level = "Fully attentive"
        elif len(eyes) == 1:
            attention_level = "Partially attentive"
        else:
            attention_level = "Not attentive"
        cv2.putText(frame, attention_level, (x, y - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.9, (0, 255, 0), 2)
        # Emit attention level via WebSocket
        socketio.emit('attention_update', {'level': attention_level})
    return frame

def gen_frames():
    while True:
        success, frame = cap.read()
        if not success:
            break
        else:
            frame = detect_attention(frame)
            ret, buffer = cv2.imencode('.jpg', frame)
            frame = buffer.tobytes()
            yield (b'--frame\r\n'
                   b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/video_feed')
def video_feed():
    return Response(gen_frames(), mimetype='multipart/x-mixed-replace; boundary=frame')

@socketio.on('attention_update')
def handle_attention_update(data):
    if data['level'] == 'Fully attentive':
        print('User is fully attentive')
    else:
        print('User is not fully attentive')

if __name__ == '__main__':
    socketio.run(app, debug=True, allow_unsafe_werkzeug=True)

