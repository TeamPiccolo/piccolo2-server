import threading
import time
import signal

try:
    import RPi.GPIO as GPIO
    haveGPIO = True
except:
    haveGPIO = False

class DummyLED(object):
    def turnOn(self):
        pass
    def turnOff(self):
        pass

class StatusLEDThread(threading.Thread):
    """Thread to control LED blinking """
    def __init__(self,led,times=[1],daemon=True):
        threading.Thread.__init__(self)
        self.daemon = daemon
        self._times = times
        self._led = led
        self.running = True

    
    def setBlinkPattern(self,times):
        self._times = times

    def run(self):
        i = 0
        while self.running:
            i +=1
            if i >= len(self._times):
                i = 0

            try:
                if i%2 == 0:
                    self._led.turnOff()
                else:
                    self._led.turnOn()
            except RuntimeError:
                #happens when thread keeps going after gpio cleanup
                pass
            time.sleep(self._times[i])

class PiccoloStatusLED(object):
    def __init__(self,led=None):
        self._led = led
        self._status_thread = StatusLEDThread(led)
        self.stopped = True

    def start(self):
        self.stopped = False
        self._status_thread.start()

    def ok(self):
        self._status_thread.setBlinkPattern([1,1])

    def not_ok(self):
        self._status_thread.setBlinkPattern([.1,.1])
   
    def show_spectrometers(self,spectrometers):
        """blink once for each connected spectrometer, then
        wait 2 seconds"""
        if len(spectrometers) == 0:
            self.not_ok()
        else:
            blink_pattern = []
            for i in range(len(spectrometers)):
                blink_pattern+=[.2,.2]
            blink_pattern[-1] = 2
            self._status_thread.setBlinkPattern(blink_pattern)

    
    def stop(self):
        self.stopped = True
        self._status_thread.running = False
        self._status_thread.join()

        #If called by __del__, GPIO might already be unloaded
        if haveGPIO and GPIO:
            GPIO.cleanup()

    def __del__(self):
        if not self.stopped:
            self.stop()
try:
    from piccolo2.hardware import led
    __test_led = led.Led()
except ImportError:
    __test_led = DummyLED()
StatusLED = PiccoloStatusLED(__test_led)

def main():
    StatusLED.start()
    StatusLED.not_ok()
    time.sleep(5)
    StatusLED.ok()
    time.sleep(5)

if __name__ == '__main__': 
    main()
