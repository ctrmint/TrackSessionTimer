import time

class SessionTracker():
    """
    A class to track session details including duration, start, and end times.
    """
    #def __init__(self):
    def __init__(self, duration_mins = None, stype: Optional[str] = None, debug: bool = False, live: Optional[bool] = None):
        self.duration_mins: Optional[int] = duration_mins
        self.duration_secs: Optional[int] = None
        self.stype: Optional[str] = stype
        # stores actual start and end targets in seconds.
        self.start_time = None
        self.end_time = None       
        # used to denote when expiration points. 
        self.last_5 = None    # %5 before end time
        self.last_15 = None   # %15 before end time
        # misc values
        self.live: Optional[bool] = live
        self.debug: bool = debug
        self.alarm: Optional[str] = None
        if self.duration_mins is None:
            self.duration_mins = 20
    
    def update_duration(self, mins):
        """
        Update a defined duration
        """
        self.duration_mins = mins
        self.duration_secs = self.duration_mins * 60
        return
    
    def start_session(self, mins=None, debug=True):
        """
        Start a new session
        """
        if mins:
            self.duration_mins = mins
        if self.duration_mins is None:
            if debug:
                print("Using default duration")
            self.duration_mins = 1
            
        self.duration_secs = self.duration_mins * 60

        self.start_time = time.time()
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

    def __str__(self) -> str:
        """
        Return a string representation of the session details.
        """
        #print("____Session prepared_____")
        #print("Session type: " + str(self.stype))
        #print("Duration minutes: " + str(self.duration_mins))
        #print("Duration seconds: " + str(self.duration_secs))
        #print("Start Time:" + str(self.start_time))
        #print("End Time:" + str(self.end_time))
        #    print("Last 15%: " + str(self.last_15))
        #    print("Last 5%:" + str(self.last_5))
        return (f"SessionTracker(stype={self.stype}, duration_mins={self.duration_mins}")
        
    
