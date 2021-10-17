import pyttsx3


class Sound:
    def __init__(self, qlist):
        """
                    0        1       2        3       4       5          6        7      8      9     10
        qlist = [windowQ, soundQ, query1Q, query2Q, teleQ, sreceivQ, creceivQ, stockQ, coinQ, sstgQ, cstgQ,
                 tick1Q, tick2Q, tick3Q, tick4Q, tick5Q, wsk1Q, wsk2Q]
                   11       12      13     14      15     16     17
        """
        self.soundQ = qlist[1]
        self.text2speak = pyttsx3.init()
        self.text2speak.setProperty('rate', 170)
        self.text2speak.setProperty('volume', 1.0)
        self.Start()

    def __del__(self):
        self.text2speak.stop()

    def Start(self):
        while True:
            text = self.soundQ.get()
            self.text2speak.say(text)
            self.text2speak.runAndWait()
