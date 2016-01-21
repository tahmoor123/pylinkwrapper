# Pylink wrapper for Psychopy
import pylink
import psychocal
import time
from psychopy.tools.monitorunittools import deg2pix
from psychopy import event

class connect(object):
    """
    Provides functions for interacting with the EyeLink via Pylink.

    :param window: Psychopy window object.
    :param edfname: Desired name of the EDF file.
    """

    def __init__(self, window, edfname):
        # Pull out monitor info
        self.sres = window.size
        self.win = window
        
        # Make filename
        self.edfname = edfname + '.edf'
        
        # Initialize connection with eye-tracker
        try:
            self.tracker = pylink.EyeLink()
            self.realconnect = True
        except:
            self.tracker = pylink.EyeLink(None)
            self.realconnect = False
            
        # Make pylink accessible
        self.pylink = pylink
        
        # Open EDF
        self.tracker.openDataFile(self.edfname)		
        pylink.flushGetkeyQueue() 
        self.tracker.setOfflineMode()

        #Gets the display surface and send msg;
        surf = pygame.display.get_surface()
        getEYELINK().sendCommand("screen_pixel_coords =  0 0 %d %d" %(surf.get_rect().w, surf.get_rect().h))
        getEYELINK().sendMessage("DISPLAY_COORDS  0 0 %d %d" %(surf.get_rect().w, surf.get_rect().h))
        
        tracker_software_ver = 0
        eyelink_ver = getEYELINK().getTrackerVersion()
        if eyelink_ver == 3:
            tvstr = getEYELINK().getTrackerVersion()
            vindex = tvstr.find("EYELINK CL")
	        tracker_software_ver = int(float(tvstr[(vindex + len("EYELINK CL")):].strip()))
	    if eyelink_ver>=2:
	        getEYELINK().sendCommand("select_parser_configuration 0")
	    if eyelink_ver == 2: #turn off scenelink camera stuff
		    getEYELINK().sendCommand("scene_camera_gazemap = NO")
        else:
	        getEYELINK().sendCommand("saccade_velocity_threshold = 35")
	        getEYELINK().sendCommand("saccade_acceleration_threshold = 9500")
	
        # set EDF file contents 
        getEYELINK().sendCommand("file_event_filter = LEFT,RIGHT,FIXATION,SACCADE,BLINK,MESSAGE,BUTTON")
        if tracker_software_ver>=4:
	        getEYELINK().sendCommand("file_sample_data  = LEFT,RIGHT,GAZE,AREA,GAZERES,STATUS,HTARGET")
        else:
	        getEYELINK().sendCommand("file_sample_data  = LEFT,RIGHT,GAZE,AREA,GAZERES,STATUS")

        # set link data (used for gaze cursor) 
        getEYELINK().sendCommand("link_event_filter = LEFT,RIGHT,FIXATION,SACCADE,BLINK,BUTTON")
        if tracker_software_ver>=4:
	        getEYELINK().sendCommand("link_sample_data  = LEFT,RIGHT,GAZE,GAZERES,AREA,STATUS,HTARGET")
        else:
	        getEYELINK().sendCommand("link_sample_data  = LEFT,RIGHT,GAZE,GAZERES,AREA,STATUS")
  
  

        getEYELINK().sendCommand("button_function 5 'accept_target_fixation'");
	    
        

    def calibrate(self, cnum=13, paval=1000):
        """
        Calibrates eye-tracker using psychopy stimuli.

        :param cnum: Number of points to use for calibration. Options are 3, 5,
                     9, 13.
        :type cnum: int
        :param paval: Pacing of calibration, i.e. how long you have to fixate
                      each target.
        :type paval: int
        """
        
        # Generate custom calibration stimuli
        genv = psychocal.psychocal(self.sres[0], self.sres[1],
                                    self.tracker, self.win)
                                    
        if self.realconnect:
            # Set calibration type
            calst = 'HV{}'.format(cnum)
            self.tracker.setCalibrationType(calst)
            
            # Set calibraiton pacing
            self.tracker.setAutoCalibrationPacing(paval)
            
            # Execute custom calibration display
            pylink.openGraphicsEx(genv)
            
            # Calibrate
            self.tracker.doTrackerSetup(self.sres[0], self.sres[1])
        else:
            genv.dummynote()
        
    def setStatus(self, message):
        """
        Sets status message to appear while recording.

        :param message: Text object to send, must be < 80 char
        :type message: str
        """
        msg = "record_status_message '{}'".format(message)
        self.tracker.sendCommand(msg)
        
    def setTrialID(self, idval=1):
        """
        Sends message that indicates start of trial in EDF.

        :param idval: Values to set TRIALID.
        """

        tid = 'TRIALID {}'.format(idval)
        self.tracker.sendMessage(tid)
        
    def recordON(self, sendlink=False):
        """
        Starts recording. Waits 50ms to allow eyelink to prepare.

        :param sendlink: Toggle for sending eye data over the link to the
                         display computer during recording.
        :type sendlink: bool
        """

        self.tracker.sendCommand('set_idle_mode')
        time.sleep(.05)
        if sendlink:
            self.tracker.startRecording(1, 1, 1, 1)
        else:
            self.tracker.startRecording(1, 1, 0, 0)

    def recordOFF(self):
        """
        Stops recording.
        """
        self.tracker.stopRecording()
        
    def drawIA(self, x, y, size, index, color, name):
        """
        Draws square interest area in EDF and a corresponding filled box on
        eye-tracker display.

        :param x: X coordinate in degrees visual angle for center of check area.
        :type x: float or int
        :param y: Y coordinate in degrees visual angle for center of check area.
        :type y: float or int
        :param size: length of one edge of square in degrees visual angle.
        :type size: float or int
        :param index: number to assign interest area in EDF
        :type index: int
        :param color: color of box drawn on eye-tracker display (0 - 15)
        :type color: int
        :param name: Name interest area in EDF
        :type name: str
        """

        # Convert units to eyelink space
        elx = deg2pix(x, self.win.monitor) + (self.sres[0] / 2.0)
        ely = -(deg2pix(y, self.win.monitor) - (self.sres[1] / 2.0))
        elsz = deg2pix(size, self.win.monitor) / 2.0
    
        # Make top left / bottom right coordinates for square
        tplf = map(round, [elx - elsz, ely - elsz])
        btrh = map(round, [elx + elsz, ely + elsz])
    
        # Construct command strings
        flist = [index, name, color] + tplf + btrh
        iamsg = '!V IAREA RECTANGLE {0} {3} {4} {5} {6} {1}'.format(*flist)
        bxmsg = 'draw_filled_box {3} {4} {5} {6} {2}'.format(*flist)

        # Send commands
        self.tracker.sendMessage(iamsg)
        self.tracker.sendCommand(bxmsg)
        
    def sendVar(self, name, value):
        """
        Sends a trial variable to the EDF file.

        :param name: Name of variable.
        :type name: str
        :param value: Value of variable.
        :type value: float, str, or int
        """

        # Make string
        varmsg = '!V TRIAL_VAR {} {}'.format(name, value)

        # Send message
        self.tracker.sendMessage(varmsg)

    def setTrialResult(self, rval=0, scrcol=0):
        """
        Sends trial result to indiciate trial end in EDF and clears screen on
        EyeLink Display.

        :param rval: Value to set for TRIAL_RESULT.
        :type rval: float, str, or int
        :param scrcol: Color to clear screen to. Defaults to black.
        :type scrol: int
        """

        trmsg = 'TRIAL_RESULT {}'.format(rval)
        cscmd = 'clear_screen {}'.format(scrcol)

        self.tracker.sendMessage(trmsg)
        self.tracker.sendCommand(cscmd)

    def endExperiment(self, spath):
        """
        Closes and transfers the EDF file.

        :param spath: File path of where to save EDF file. Include trailing
                      slash.
        :type spath: str
        """

        # File transfer and cleanup!
        self.tracker.setOfflineMode()
        time.sleep(.5)

        # Generate file path
        fpath = spath + self.edfname

        # Close the file and transfer it to Display PC
        self.tracker.closeDataFile()
        time.sleep(1)
        self.tracker.receiveDataFile(self.edfname, fpath)
        self.tracker.close()

    def fixCheck(self, size, ftime, button):
        """
        Checks that fixation is maintained for certain time.

        :param size: Length of one side of box in degrees visual angle.
        :type size: float or int
        :param ftime: Length of time to check for fixation in seconds.
        :type ftime: int
        :param button: Key to press to recalibrate eye-tracker.
        :type button: char
        """

        # Calculate Fix check borders
        cenX = self.sres[0] / 2.0
        cenY = self.sres[1] / 2.0
        size = deg2pix(size, self.win.monitor) / 2.0

        xbdr = [cenX - size, cenX + size]
        ybdr = [cenY - size, cenY + size]

        # Set status message & Draw box
        self.setStatus('Fixation Check')
        bxmsg = 'draw_box {} {} {} {} 1'.format(xbdr[0], ybdr[0], xbdr[1],
                                                ybdr[1])
        self.tracker.sendCommand(bxmsg)
        
        # Begin recording
        self.tracker.startRecording(0, 0, 1, 1)
        
        # Check which eye is being recorded
        eye_used = self.tracker.eyeAvailable()
        RIGHT_EYE = 1
        LEFT_EYE = 0
        
        # Begin polling
        keys = []
        fixtime = time.clock()
        while self.realconnect:  # only start check loop if real connection

            # Check for recalibration button
            keys = event.getKeys(button)
            if keys:
                self.tracker.stopRecording()
                self.calibrate()
                break 
            
            # Grab latest sample
            sample = self.tracker.getNewestSample()
            
            # Extract gaze coordinates
            if eye_used == RIGHT_EYE:
                gaze = sample.getRightEye().getGaze()
            else:
                gaze = sample.getLeftEye().getGaze()
                
            # Are we in the box?
            if xbdr[0] < gaze[0] < xbdr[1] and ybdr[0] < gaze[1] < ybdr[1]:
                # Have we been in the box long enough?
                if (time.clock() - fixtime) > ftime:
                    self.tracker.stopRecording()
                    break
            else:
                # Reset clock if not in box
                fixtime = time.clock()
                
    def sendMessage(self, txt):
        """
        Sends a message to the tracker that is recorded in the EDF.

        :param txt: Message to send.
        :type txt: str
        """

        # Send message
        self.tracker.sendMessage(txt)
        
    def sendCommand(self, cmd):
        """
        Sends a command to the Eyelink.

        :param cmd: Command to send.
        :type cmd: str
        """

        # Send Command
        self.tracker.sendCommand(cmd)
        
    def drawText(self, msg):
        """
        Draws text on eye-tracker screen.

        :param msg: Text to draw.
        :type msg: str
        """

        # Figure out center
        x = self.sres[0] / 2
        
        # Send message
        txt = '"{}"'.format(msg)
        self.tracker.drawText(text, (x, 50))
