# [+] Implement Recording Drastic Difference in Frames
# [+] Implement Google Drive API functionality
# [+] Enable live AudioFeed - ISSUE: Cannot use multiple instances of the mic source - OSError


from flask import Flask, Response, render_template
import cv2 as cv
import time
import pyaudio
import numpy as np

app = Flask(__name__)
video = cv.VideoCapture(0)

global img_diff
FORMAT = pyaudio.paInt16
CHANNELS = 2
RATE = 44100
CHUNK = 1024
RECORD_SECONDS = 5

audio1 = pyaudio.PyAudio()
print(audio1.get_device_count())
print(audio1.get_device_info_by_index(4))

@app.route('/')
def index():
   return render_template('index.html')

def mse(imgA, imgB):
    err = np.sum((imgA.astype("float")-imgB.astype("float"))**2)
    err /= float(imgA.shape[0] * imgA.shape[1])
    return err


def gen(video):
    startTime = time.time()
    frames = []
    currImg = None
    prevImg = None
    frmCount = 0
    global img_diff
    img_diff = 0.0
    while True:
        # Read Frames from video object
        #success - Bool T/F
        # image = video frame
        success, image = video.read()
        if prevImg is not None:
            img_diff = mse(prevImg,currImg)
        else:
            prevImg = image
            currImg = image



        # Encode image to jpeg format
        ret, jpeg = cv.imencode('.jpg', image)
        # Encode into jpeg into bytes to serve over HTTP
        frame = jpeg.tobytes()



        # Serve jpeg over HTTP
        if int(time.time()-startTime) >= 1 and len(frames) != 0:
            for f in frames:
                yield (b'--frame\r\n'b'Content-Type: image/jpeg\r\n\r\n' + f + b'\r\n\r\n')
            frames = []
        else:
            frames.append(frame)



@app.route('/counter_update')
def counter_update():
    global img_diff
    return img_diff

@app.route('/video_feed')
def video_feed():
   global video
   return Response(gen(video),
                   mimetype='multipart/x-mixed-replace; boundary=frame')


@app.route('/front_door_feed')
def front_door_feed():
    return render_template('front_door_feed.html', counter_update='/counter_update', video="/video_feed")

def genHeader(sampleRate, bitsPerSample, channels):
    datasize = 2000*10**6
    o = bytes("RIFF",'ascii')                                               # (4byte) Marks file as RIFF
    o += (datasize + 36).to_bytes(4,'little')                               # (4byte) File size in bytes excluding this and RIFF marker
    o += bytes("WAVE",'ascii')                                              # (4byte) File type
    o += bytes("fmt ",'ascii')                                              # (4byte) Format Chunk Marker
    o += (16).to_bytes(4,'little')                                          # (4byte) Length of above format data
    o += (1).to_bytes(2,'little')                                           # (2byte) Format type (1 - PCM)
    o += (channels).to_bytes(2,'little')                                    # (2byte)
    o += (sampleRate).to_bytes(4,'little')                                  # (4byte)
    o += (sampleRate * channels * bitsPerSample // 8).to_bytes(4,'little')  # (4byte)
    o += (channels * bitsPerSample // 8).to_bytes(2,'little')               # (2byte)
    o += (bitsPerSample).to_bytes(2,'little')                               # (2byte)
    o += bytes("data",'ascii')                                              # (4byte) Data Chunk Marker
    o += (datasize).to_bytes(4,'little')                                    # (4byte) Data size in bytes
    return o

@app.route('/audio')
def audio():
    # start Recording
    def sound():

        CHUNK = 1024
        sampleRate = 44100
        bitsPerSample = 16
        channels = 2
        wav_header = genHeader(sampleRate, bitsPerSample, channels)

        stream = audio1.open(format=FORMAT, channels=CHANNELS,
                        rate=RATE, input=True, input_device_index=5,
                        frames_per_buffer=CHUNK)
        print("recording...")
        #frames = []
        first_run = True
        while True:
           if first_run:
               data = wav_header + stream.read(CHUNK)
               first_run = False
           else:
               data = stream.read(CHUNK)
           yield(data)

    return Response(sound())


if __name__ == '__main__':
   app.run(host='127.0.0.1', port=80, threaded=True)