from flask import Flask, render_template, Response
import cv2
import numpy
import subprocess as sp
import re

app = Flask(__name__)

IMG_W = 640
IMG_H = 480

NODE_BIN = "node"
node_cmd = [ NODE_BIN,
        'voc-poc/index.js',
        '-o']

FFMPEG_BIN = "ffmpeg"
ffmpeg_cmd = [ FFMPEG_BIN,
        '-i', '-',
        '-r', '53',
        '-s', str(IMG_W)+'x'+str(IMG_H),
        '-vcodec', 'rawvideo',
        '-pix_fmt', 'bgr24',
        '-an','-sn',
        '-f', 'image2pipe', '-']

isStreaming = False
nodepipe = None
pipe = None

def gen_frames():
    global isStreaming
    global nodepipe
    global pipe

    if (isStreaming == False):
        print("Starting the stream...")
        nodepipe = sp.Popen(node_cmd, stdout = sp.PIPE)
        pipe = sp.Popen(ffmpeg_cmd, stdin= nodepipe.stdout, stdout = sp.PIPE, bufsize=10)
        isStreaming = True

    while True:
        try:
            raw_image = pipe.stdout.read(IMG_W*IMG_H*3)
            image =  numpy.fromstring(raw_image, dtype='uint8')
            frame = image.reshape((IMG_H,IMG_W,3))
            success = True
        except ValueError as e:
            print("Error initing the stream, please try again")
            success = False
            isStreaming = False
            nodepipe.kill()
            pipe.kill()

        if not success:
            img = numpy.zeros((IMG_H,IMG_W,3), dtype=numpy.uint8)

            cv2.putText(img, 'Failed to load the stream.', 
                (20, 50), 
                cv2.FONT_HERSHEY_SIMPLEX, 
                1,
                (255,255,255),
                1)
            cv2.putText(img, 'Please reload this page.', 
                (20, 100), 
                cv2.FONT_HERSHEY_SIMPLEX, 
                1,
                (255,255,255),
                1)
            ret, buffer = cv2.imencode('.jpg', img)
            frame = buffer.tobytes()
            yield (b'--frame\r\n'
                   b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')
            break
        else:
            ret, buffer = cv2.imencode('.jpg', frame)
            frame = buffer.tobytes()
            yield (b'--frame\r\n'
                   b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')


@app.route('/video_feed')
def video_feed():
    return Response(gen_frames(), mimetype='multipart/x-mixed-replace; boundary=frame')

@app.route('/usb-status')
def usb_status():
    usb_status = 'err'
    df = sp.check_output('lsusb')
    devices = []
    for i in df.split(b'\n'):
        if i:
            usbIds = re.findall(r'Bus (\d+) Device (\d+): ID ([0-9a-fA-F]+):', str(i))
            if len(usbIds) > 0 and len(usbIds[0]) > 2:
                usb_id = usbIds[0][2]
                if usb_id == '2ca3': # 2ca3 is the goggles usb id
                    usb_status = 'ok'

    return Response(usb_status)

@app.route('/')
def index():
    return render_template('index.html')


if __name__ == '__main__':
    app.run(debug=True,host='0.0.0.0')