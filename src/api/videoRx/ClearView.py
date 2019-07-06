
###changelog:
#   4/20/2019
            # - Created by Ryan Friedman
            # - Created ClearView Class and got serial port working
            # - next: use named arguments for all functions and limit check numerics
#   4/21/2019
            # - Continued adding setters and descriptions. Limit checking input but not type. Will throw exception is wrong type used
            # - Added support for passing parameters of rcvr_targets in a list. Thus, multiple receivers can be set at once. To set all, set address, use broadcast.
                #broadcast will be fastest (1 command), but can't check the message was received on receivers
#   7/3/2019
            # - Hardware received. Started testing
#   7/4/2019
            # - Testing finished. All working API functions are working here. Added receiver scanning  "get_connected_receiver_list"
        
#planned features:
    # Try/Except function inputs to prevent exceptions
    # Implement response parser with the intent of checking the setters got through. A "robust" bool in __init__ could enable or disable this
    # Implement broadcast functions for the common functions like reboot, temp OSD message
    # Implement batch getters where a list of receiver addresses can be input and each one's value is returned.
        #ex: get lock status on receivers 1,2,3,5,6 returns (true,true,false,true,false)
    # Quick way to implement todo: https://stackoverflow.com/questions/2654113/how-to-get-the-callers-method-name-in-the-called-method
###



#ClearView class for serial comms
import serial
from time import sleep
import inspect,sys #for printing caller in debug
try:
    import clearview_comspecs
    clearview_specs = clearview_comspecs.clearview_specs
except ImportError:
    print("No clearview_specs")
    baudrate = 19200
    clearview_specs = {
        'message_start_char' : '<',
        'message_end_char' : '>',
        'message_csum' : '#',
        'mess_src'  : 0,
        'baud' : 19200,
    }
    
    


class ClearView:
    def __init__(self,*args,**kwargs): 
        self._serial= serial.Serial(
           port = kwargs.get('port','/dev/ttyS0'), 
           baudrate = 57600,
           parity = serial.PARITY_NONE,
           stopbits = serial.STOPBITS_ONE,
           bytesize = serial.EIGHTBITS,
           timeout = kwargs.get('timeout',0.5) # number of seconds for read timeout
           )
       
        self.msg_start_char = clearview_specs['message_start_char'] #'\n' #TODO replace when ready
        self.msg_end_char = clearview_specs['message_end_char'] #TODO replace when ready
        self.mess_src = clearview_specs['mess_src'] #TODO should computer emulate cell phone still?
        self.csum = clearview_specs['message_csum']
        
        #debug => Used for printing all serial comms and warnings. Critical Error messages are printed no debug_msg state.
        self.debug_msg = kwargs.get('debug',False)
        self._print("CV Debug Messages Enabled...") #self.print only prints data if self.debug_msg is True. 
        
        #robust mode => Slower, but all setters are automatically checked with a get. G
        self.robust = kwargs.get('robust',False)
        self.robust_setter_retries = 1 #number of set retries before giving up. 
        self.robust_getter_retries = 1 #number of get retries before giving up
        
        self._print("Connecting to " , self._serial.port,sep='\t')
        
    # ###########################   
    # ### CV Control Commands ###
    # ########################### 
    def set_receiver_address(self,rcvr_targets,new_target,*args,**kwargs): #ADS => Sets receiver address as new_target
        """set_receiver_address => rcvr_target is the receiver seat number of interest,0-8, 0 for broadcast. new_target is the new seat 1-8"""
        try: #rcvr_targets is a list of sorts
            for rx in rcvr_targets:
                cmd = self._format_write_command(rx,"ADS" + str(new_target))
                self._write_serial(cmd)
        except: #rcvr_targets is an int or string
            cmd = self._format_write_command(int(rcvr_targets),"ADS" + str(new_target))
            self._write_serial(cmd)

    def set_cstm_frequency(self,rcvr_target,frequency,*args,**kwargs): #FR = > Sets frequency of receiver and creates custom frequency if needed
        cmd = self._format_write_command(str(rcvr_target),"FR" + str(frequency,))
        self._write_serial(cmd)
        """
        if self.robust == True:
            sleep(0.1)
            if self.get_frequency(rcvr_target) == int(frequency):
                return True
        return False
        """

    #good
    def set_osd_string(self,rcvr_target,osd_str,*Args,**kwargs): #ID => Sets OSD string
        osd_str_max_sz = 10
        osd_str = osd_str[:osd_str_max_sz]
        cmd = self._format_write_command(str(rcvr_target),"ID" + str(osd_str))
        self._write_serial(cmd)

    #broken
    def set_video_live(self,rcvr_target,*args,**kwargs): #ML => Go to live video
        cmd = self._format_write_command(str(rcvr_target),"MS")
        self._write_serial(cmd)

    #broken
    def reboot(self,rcvr_target,*args,**kwargs): #RBR => Reboot receiver. Issue twice to take effect. 
        cmd = self._format_write_command(str(rcvr_target),"RBR")
        self._write_serial(cmd)
        sleep(0.1)
        self._write_serial(cmd)

    #broken
    def set_temporary_osd_string(self,rcvr_target,osd_str,*Args,**kwargs): #TID => Temporary set OSD string
        cmd = self._format_write_command(str(rcvr_target),"TID" + str(osd_str))
        self._write_serial(cmd)

    #broken
    def set_temporary_video_format(self,rcvr_target,video_format,*args,**kwargs): #TVF => Temporary Set video format. options are 'N' (ntsc),'P' (pal),'A' (auto)
        desired_video_format = video_format.lower()
        if desired_video_format == "n" or desired_video_format == "ntsc":
            cmd = self._format_write_command(str(rcvr_target),"TVFN")
            self._write_serial(cmd)
        elif desired_video_format == "p" or desired_video_format == "pal":
            cmd = self._format_write_command(str(rcvr_target),"TVFP")
            self._write_serial(cmd)
        elif desired_video_format == "a" or desired_video_format == "auto":
            cmd = self._format_write_command(str(rcvr_target),"TVFA")
            self._write_serial(cmd)
        else:
            print("Error. Invalid video format in set_temporary_video_format of ",desired_video_format)

    #broken
    def set_video_format(self,rcvr_target,video_format,*args,**kwargs): #TVF => Temporary Set video format. options are 'N' (ntsc),'P' (pal),'A' (auto)
        desired_video_format = video_format.lower()
        if desired_video_format == "n" or desired_video_format == "ntsc":
            cmd = self._format_write_command(str(rcvr_target),"VFN")
            self._write_serial(cmd)
        elif desired_video_format == "p" or desired_video_format == "pal":
            cmd = self._format_write_command(str(rcvr_target),"VFP")
            self._write_serial(cmd)
        elif desired_video_format == "a" or desired_video_format == "auto":
            cmd = self._format_write_command(str(rcvr_target),"VFA")
            self._write_serial(cmd)
        else:
            print("Error. Invalid video format in set_temporary_video_format of ",desired_video_format)


    ############################
    #       Broadcast Messages #
    ############################
    def set_all_receiver_addresses(self,new_address):
        self.set_receiver_address(0,new_address)

    def set_all_osd_message(self,message):
        self.set_osd_string(0,message)
        
    # ##########################  
    # ### CV Report Commands ### 
    # ##########################     
    def get_frequency(self,rcvr_target,*args,**kwargs): #RP AD => Report Receiver Address
        #note: can use this to see if units are connected by asking for response
        self._clear_serial_in_buffer()
        cmd = self._format_write_command(str(rcvr_target),"RPFR")
        self._write_serial(cmd)
        sleep(0.05)
        fr_report = self._read_until_termchar()
        if fr_report[-2:] != '!\r':
            print("Error: No valid requency report ending")
            return
        elif fr_report.find("FR") != -1:
            fr_report = fr_report[fr_report.find("FR"):]
            frequency = int(fr_report[2:-2])
            return frequency
        else:
            print("Error: Not a valid frequency report")

    #broken because lock status message format is unkown
    def get_lock_status(self,rcvr_target,*args,**kwargs): #RP AD => Report Receiver Address
        self._clear_serial_in_buffer()
        cmd = self._format_write_command(str(rcvr_target),"RPLF")
        self._write_serial(cmd)
        sleep(0.05)
        fr_report = self._read_until_termchar()
        print(fr_report)
        if fr_report[-2:] != '!\r':
            print("Error: No valid lock status report ending")
            return
        elif fr_report.find("LF") != -1:
            fr_report = fr_report[fr_report.find("LF"):]
            frequency = fr_report[1:-2]
            return frequency
        else:
            print("Error: Not a valid lock status report")

    #good
    def get_model(self,rcvr_target,*args,**kwargs): #RP MV => Report model version
        self._clear_serial_in_buffer()
        cmd = self._format_write_command(str(rcvr_target),"RPMV")
        self._write_serial(cmd)
        sleep(0.05)
        model_report = self._read_until_termchar()
        if model_report == False:
            self._print("Error: No response from cv#",rcvr_target," on model report request")
            return False
        elif model_report[-2:] != '!\r':
            self._print("Error: No valid model report ending")
            return False

        elif model_report.find("MV") != -1:
            model_report = model_report[model_report.find("MV"):]
            model_str = model_report[2:-2]
            version_desc = model_str.strip(' ').split('-')
            model_dict = {
                'hw' : version_desc[0],
                'sw' : version_desc[1],
            }
            return model_dict

        else:
            self._print("Error: Not a valid frequency report")

    
    #Use this to see which device ID's are connected
    def get_connected_receiver_list(self):
        connected_receivers = {}
        for i in range(1,9):
            self._clear_serial_in_buffer()

            if self.get_model(i) == False:
                connected_receivers[i] = False
            else:
                connected_receivers[i] = True


            print(i,connected_receivers[i])
        print(connected_receivers)
        return connected_receivers

    # ########################### 
    # ### CV Serial Utilities ### 
    # ###########################

    def _send_custom_command(self,rcvr_target,cstm_cmd):
        cmd = self._format_write_command(str(rcvr_target),cstm_cmd)
        self._write_serial(cmd)

    def _read_serial_blocking(self,line_ending_char): #waits for data to come in as long as it takes
        rv = ""
        line_ending_byte = line_ending_char.encode() #converting string char to byte. Example. '\n' converts to b'\n' , '>' converts to b'>'
        while True: #read all available bytes till the line_ending_byte
            ch = self._serial.read() 
            if ch == line_ending_byte:
                return rv #ignore the line ending byte
            rv += ch.decode() #push the bytes onto a string by decoding and appending

    def _format_write_command(self,rcvr_target,message): #formats sending commands with starting chars, addresses, csum, message and ending char. Arguments may be strings or ints
        return self.msg_start_char + str(rcvr_target) + str(self.mess_src) + str(message) + self.csum + self.msg_end_char

    def _move_cursor(self,rcvr_target,direction):
        cmd = self._format_write_command(str(rcvr_target),"WP"+direction)
        self._write_serial(cmd)
    
    def _print(self,*args,**kwargs):
        if self.debug_msg==True:
            print(*args,sep=kwargs.get('sep','\n'))  

    def _write_serial(self,msg):
        self._print("CV_serial_write: ",sys._getframe().f_back.f_back.f_code.co_name , "=>" ,sys._getframe().f_back.f_code.co_name,msg,**{'sep':' '})
        self._serial.write(msg.encode())

    def _get_serial_in_waiting(self):
        return self._serial.in_waiting

    def _clear_serial_in_buffer(self):
        while self._get_serial_in_waiting() > 0:
            self._serial.read()

    def _read_until_termchar(self):
        str_read = self._serial.read_until(terminator = self.msg_end_char).decode('unicode_escape')
        if str_read == '':
            return False
        else:
            return str_read
        


if __name__ == "__main__": #example usage
    rx_id = 1   #ensure the cv is set to that rx_id
    cv = ClearView(
        port= 'COM5', #port name, COMX on windows
        debug = False,
        robust= True, #checks all data sent was actually received. Slows stuff down.  
        timeout = 0.1, #serial read timeout
        )
   
    pilot_name = "name2"
    osd_str = "{:<8}L{}"


    cv.get_connected_receiver_list()
    #cv.set_all_osd_message("MESS1")
    cv.set_osd_string("1","M1")
    sleep(2)
    #cv.set_all_osd_message("MESS2")
    cv.set_osd_string("1","M2")
    sleep(2)
    #cv.set_all_osd_message("MESS3")
    cv.set_osd_string("1","M3")
    print("Done")

    """
    for i in range(5):
        cv.set_osd_string(rx_id,osd_str.format(pilot_name,str(i)))
        sleep(0.25)
        cv._move_cursor(rx_id,'+')
        sleep(0.25)
        cv._move_cursor(rx_id,'-')
        sleep(2)
    """
    #cv.set_osd_string(rx_id,osd_str)





    #Get all the reports for a single device:
    """
    options = ["RPFR","RPLF","RPID","RPMV","RPRS"] 
    for report_name in options:
        cv._clear_serial_in_buffer()
        cv.send_custom_command(1, report_name)
        
        sleep(0.05)
        fr_report = cv._read_until_termchar()
        print(report_name, " = " ,fr_report)
    """


