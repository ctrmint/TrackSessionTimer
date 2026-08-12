import time


class SessionTracker():
    """
    A class to track session details including duration, start, and end times.
    """
    def __init__(self, duration_mins=None, stype=None, debug=False, live=None, clock=None):
        self.duration_mins = duration_mins
        self.duration_secs = None
        self.stype = stype
        # stores actual start and end targets in seconds.
        self.start_time = None
        self.end_time = None       
        # used to denote when expiration points. 
        self.last_5 = None    # %5 before end time
        self.last_15 = None   # %15 before end time
        # misc values
        self.live = live
        self.debug = debug
        self.alarm = None
        self._clock = clock or time.time
        if self.duration_mins is None:
            self.duration_mins = 20
    
    def update_duration(self, mins):
        """
        Update a defined duration
        """
        self.duration_mins = mins
        self.duration_secs = self.duration_mins * 60
        return
    
    def start_session(self, mins=None, debug=None):
        """
        Start a new session
        """
        if debug is None:
            debug = self.debug
        if mins is not None:
            self.duration_mins = mins
        if self.duration_mins is None:
            if debug:
                print("Using default duration")
            self.duration_mins = 1
            
        self.duration_secs = self.duration_mins * 60

        self.start_time = self._clock()
        self.end_time = self.start_time + self.duration_secs
        
        self.last_15 = self.start_time + int(self.duration_secs * 0.85) 
        self.last_5 = self.start_time + int(self.duration_secs * 0.95) 
        
        self.state = False
        self.live = True
        
        if debug:
            print("____Session prepared_____")
            print("Session type: " + str(self.stype))
            print("Duration minutes: " + str(self.duration_mins))
            print("Duration seconds: " + str(self.duration_secs))
            print("Start Time:" + str(self.start_time))
            print("End Time:" + str(self.end_time))
            print("Last 15%: " + str(self.last_15))
            print("Last 5%:" + str(self.last_5))
            print("Status: " + str(self.live))
            print("State: " + str(self.state))
            print("Live: " +str(self.live))
        
        return

    def phase(self, now=None):
        """Return the current display phase for deterministic host-side tests."""
        if self.start_time is None:
            return "ready"
        if now is None:
            now = self._clock()
        if now >= self.end_time:
            return "overrun"
        if now >= self.last_5:
            return "last_5"
        if now >= self.last_15:
            return "last_15"
        return "running"

    def __str__(self):
        """Return a string representation of the session details."""
        return f"SessionTracker(stype={self.stype}, duration_mins={self.duration_mins})"
        

def secs_to_mins_secs(seconds):
    """Format an integer second count as MM:SS."""
    seconds = int(seconds)
    minutes = seconds // 60
    remaining_seconds = seconds % 60
    return f"{minutes:02}:{remaining_seconds:02}"
