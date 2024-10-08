#!/usr/bin/env python3
# -*- coding:utf-8 -*-
"""Robot module

Built on a sample program that used a 3D mouse to control XYZ+rotation and reprogrammed to listen to WASD EQ ZXCVFG keys for movement.

# Original sample
# https://github.com/ShoheiKobata/orin_bcap_python_samples/tree/master/3DMouse_Controll

# b-cap Lib URL
# https://github.com/DENSORobot/orin_bcap

"""

import os
import sys

import traceback
from pybcapclient.bcapclient import BCAPClient
from pybcapclient.orinexception import ORiNException

from logging import INFO, basicConfig, getLogger, NullHandler


class Robot():
    """Robot Class for Application

    Robot class for applications. You may develop functions and variables needed for your application.

    Attributes:

    """

    # bcap handle
    bcap = None
    h_ctrl = 0
    h_rob = 0

    # option_str
    ifnotm = '@IfNotMember'

    def __init__(self):
        self.old_target_pos = None
        self._logger = getLogger(__name__)
        self._logger.addHandler(NullHandler())
        self._logger.setLevel(INFO)
        self._logger.propagate = True
        self._logger.info('pyrobot')
    # End def

    def connect(self, ip='192.168.0.1', rc_type='RC8', name='_'): #RC8 for the COBOTTA
        """connect

        Function to start communication with the robot controller

        Args:
            ip (str): IP Address ("XXX.XXX.XXX.XXX") of robot controller
            rc_type (str): Robot cotroller type  RC8 or RC9
            name (str): name, arbitrary string
        """
        ret = False
        try:
            if rc_type == 'RC8':
                provider = 'CaoProv.DENSO.VRC'
            elif rc_type == 'RC9':
                provider = 'CaoProv.DENSO.VRC9'
            else:
                raise ValueError('rc_type value error')
            self.bcap = BCAPClient(host=ip, port=5007, timeout=2000) #port=5007  49152
            self._logger.info('connect robot')
            self.bcap.service_start('')
            self.h_ctrl = self.bcap.controller_connect(name + '_App', provider, 'localhost', self.ifnotm)
            self._logger.info('Connected RC')
            self.h_rob = self.bcap.controller_getrobot(self.h_ctrl, 'arm', self.ifnotm)
            self.h_mode = self.bcap.controller_getvariable(self.h_ctrl, '@Mode', self.ifnotm)
        except Exception as e:
            self._error_handling(e)
            ret = False
        else:
            ret = True
        return ret
    # End def

    def standby_on(self):
        """standby on robot
        standby on robot. execute takearm and Motor On
        Args:
            None
        Returns:
            None
        """
        if self.bcap is None:
            self._logger.error("BCAP client is not initialized.")
            return

        try:
            self.bcap.robot_execute(self.h_rob, 'TakeArm', [0, 0])
            # Set the executable token to Ethernet
            #self.bcap.controller_execute(self.h_ctrl, 'SetExToken', ['Ethernet'])
            self.bcap.robot_execute(self.h_rob, 'Motor', [1, 0])
            self.rob_pos = self.bcap.robot_execute(self.h_rob, 'CurPos')
        except ORiNException as e:
            self._logger.error(f"ORiNException: {e}")
            if e.hresult == 0x83501028:
                # Set executable token to Ethernet
                #self.bcap.controller_execute(self.h_ctrl, 'SetExToken', ['Ethernet'])
                # Retry the Motor command
                self.bcap.robot_execute(self.h_rob, 'Motor', [1, 0])
            self._error_handling(e)
        except Exception as e:
            self._error_handling(e)

        # End try except
    # End def

    def standby_off(self):
        """standby off robot
        standby on robot. execute GiveArm and Motor Off
        Args:
            None
        Returns:
            None
        """
        try:
            self.bcap.robot_execute(self.h_rob, 'GiveArm')
            self.bcap.robot_execute(self.h_rob, 'Motor', [0, 0])
            self.old_target_pos = None
        except Exception as e:
            self._error_handling(e)
        # End try except
    # End def

    def moveto(self, deviation):
        """Move robot to the specified position with deviation
        Args:
            deviation (list): List of deviations for the movement
        Returns:
            None
        """
        if self.old_target_pos is None:
            self.old_target_pos = self.bcap.robot_execute(self.h_rob, 'Curpos')
        # End if
        pn1 = [self.old_target_pos, 'P']
        pn2 = 'P(' + str(deviation)[1:-1] + ')'
        target = self.bcap.robot_execute(self.h_rob, 'Dev', [pn1, pn2])
        pose_data = [target, 'P', '@P']
        self.bcap.robot_move(handle=self.h_rob, comp=1, pose=pose_data, option='Next')
        self.old_target_pos = target

    # End def

    def get_base_info(self):
        """get base information

        get basic information about connectded controller and robot

        Args:
            None
        Returns:
            list: [serial, robot_type, vrc_version]
            serial: str
            robot_type: str
            vrc_version: str
        """
        serial = self.bcap.controller_execute(self.h_ctrl, 'SysInfo', 0)
        robot_type = self.bcap.robot_execute(self.h_rob, 'GetRobotTypeName')
        h_version = self.bcap.controller_getvariable(self.h_ctrl, '@VERSION', self.ifnotm)
        vrc_version = self.bcap.variable_getvalue(h_version)
        return [serial, robot_type, vrc_version]
    # End def

    def moniter_data(self):
        """get data
        get monitoring datas

        Args:
            None
        Returns:
            list: [mode, position]
            mode: str
            position: list [x,y,z,rx,ry,rz,fig]
        """
        self.rob_pos = self.bcap.robot_execute(self.h_rob, 'CurPos')
        mode = self.bcap.variable_getvalue(self.h_mode)
        if mode == 1:
            mode_str = 'manual'
        elif mode == 2:
            mode_str = 'teach check'
        elif mode == 3:
            mode_str = 'auto'
        else:
            mode_str = ''
        # End if
        return [mode_str, self.rob_pos]

    def save_all_pacscript(self, save_dir='', first=True, handle_parent=0):
        """save pacscript files

        Save the program in the robot controller to the PC.

        Args:
            save_dir: str
                Directory where programs is saved
        """
        try:
            os.makedirs(save_dir, exist_ok=True)
            h_files = []
            if first:
                file_names = self.bcap.controller_getfilenames(self.h_ctrl)
                for file_name in file_names:
                    h_files.append(self.bcap.controller_getfile(self.h_ctrl, file_name, self.ifnotm))
            else:
                file_names = self.bcap.file_getfilenames(handle_parent)
                for file_name in file_names:
                    h_files.append(self.bcap.file_getfile(handle_parent, file_name, self.ifnotm))
            # End for
            for h_file in h_files:
                file_name = self.bcap.file_getname(h_file)
                if (file_name.find('.lst') > 0):
                    continue
                if (file_name.find('\\') > 0):
                    print(file_name)
                    child_dir = os.path.join(save_dir, file_name)
                    self.save_all_pacscript(save_dir=child_dir, first=False, handle_parent=h_file)
                else:
                    data = self.bcap.file_getvalue(h_file)
                    f = open(os.path.join(save_dir, file_name), 'w', encoding='shift-jis', newline='')
                    f.write(data)
                    f.close()
                # End if
            # End for
        except Exception as e:
            self._error_handling(e)

    def tester_func(self):
        try:
            h_int = self.bcap.controller_getvariable(self.h_ctrl, 'I3')
            self.bcap.variable_putvalue(h_int, 90)
        except Exception as e:
            self._error_handling(e)
    # End def
    def taskman(self, nimi, numero): # ajetaan mainista kahdesti? Ei välttämättä
        # Controller get pac script names
        # If contains "nimi" excecute
        HTask = 0
        HTask = self.bcap.controller_gettask(self.h_ctrl, nimi, numero)
        #self.bcap.controller_execute(self.h_ctrl, 'SysInfo', 0)
        # Start pro1.pcs in RC8
        # mode  1:One cycle execution, 2:Continuous execution, 3:Step forward
        mode = 1
        #hr = 
        self.bcap.task_start(HTask, mode, "")  
        return  HTask


    # Kysele parin sekunnin välein ollaanko törmätty

    def establish_col_variable(self):
        variable_storage = self.bcap.controller_getvariable(self.h_ctrl, 'I1')
        return variable_storage

    def collision_police(self, variable_storage):
        #variable_storage = self.bcap.controller_getvariable(self.h_ctrl, 'I1')
        h_int = self.bcap.variable_getvalue(variable_storage)
        return h_int 
        #Tässäkin pitäis tietysti olla try catch, logiikan voi kirjoittaa pääohjelmaan, ja loop voisi olla myös timer funktiossa

    def release_variable(self, variable):
        # Disconnect
        if(variable != 0):
            self.bcap.variable_release(variable)
            print("Released variable ",variable)

    def startposition(self):
        self.bcap.robot_execute(self.h_rob, "TakeArm")
        self.bcap.robot_execute(self.h_rob, "ExtSpeed", 75)
        self.bcap.robot_move(self.h_rob, 1, "@P J(0,0,90,0,90,0)") #kolmanneksi viimeinen oli 0 tai 20, nyt 90.
        self.bcap.robot_execute(self.h_rob, "GiveArm", None) #TODO Lisää motor off
        self.bcap.robot_execute(self.h_rob, 'GiveArm')
        self.bcap.robot_execute(self.h_rob, 'Motor', [0, 0])

    # Lopeta taskit

    def stoppingTask(self, nimi):
        mode = 1
        #hr = 
        self.bcap.task_stop(nimi, mode, "")
        print("task stop")

    def disconnect(self):
        """disconnect controller and bcap service
        disconnect controller and bcap server
        Args:
            None
        Returns:
            None
        """
        self.bcap.robot_execute(self.h_rob, 'GiveArm')
        if self.h_rob != 0:
            self.bcap.robot_release(self.h_rob)
            self.h_rob = 0
        if self.h_ctrl != 0:
            self.bcap.controller_disconnect(self.h_ctrl)
            self.h_ctrl = 0
        if self.bcap is not None:
            self.bcap.service_stop()
            print("b-cap service Stop")
            del self.bcap
        # End if
        print("Finish")
    # End if

    def clear_errors(self): #THIS IS COMPLETELY NEW 
        """Clear errors in the robot controller"""
        try:
            self.bcap.controller_execute(self.h_ctrl, "ClearError")
            self._logger.info("Cleared errors in robot controller.")
        except Exception as e:
            self._error_handling(e)

    def _error_handling(self, e):
        """robot error handling
        robot error , pc error handling. write error infomation to logfile
        usage
            try:
                ....
            except Exception as e:
                self._error_handling(e)
            finaly:
                ...

        Args:
            e: exception
        returns:
            None
        """
        type_, value, traceback_ = sys.exc_info()
        err_trace = traceback.format_exception(type_, value, traceback_)
        print(err_trace)
        self._logger.error(err_trace)
        if (type(e) == ORiNException) and (self.h_ctrl != 0):
            print('catch ORiN Exception in Robot Controller')
            errorcode_int = int(str(e))
            if errorcode_int < 0:
                errorcode_hex = format(errorcode_int & 0xffffffff, 'x')
            else:
                errorcode_hex = hex(errorcode_int)
            # End if
            print("Error Code : 0x" + str(errorcode_hex))
            error_description = self.bcap.controller_execute(self.h_ctrl, "GetErrorDescription", errorcode_int)
            print("Error Description : " + error_description)
            self._logger.error('ORiN Error , Error code: 0x' + str(errorcode_hex) + ', Error Description: ' + error_description)
        else:
            self._logger.error(str(type(e)) + ' : ' + str(e))
        # End if
    # End def

    def __del__(self):
        self.disconnect()
    # End def
# End class

    def set_executable_token(self, token='Ethernet'): #ALSO COMPLETELY NEW
        """Set the executable token for the controller
        Args:
            token (str): The token to set (default is 'Ethernet')
        """
        try:
            self.bcap.controller_execute(self.h_ctrl, 'SetExToken', [token])
            self._logger.info(f"Set executable token to {token}.")
        except Exception as e:
            self._error_handling(e)

    def reconnect_robotto(self):
        """Reconnect to the robot controller and execute necessary initializations
        Args:
            None
        Returns:
            None
        """
        if self.bcap is None:
            self._logger.error("BCAP client is not initialized.")
            return

        try:
            self.connect()
            self.execute_calset()
            #self.set_executable_token()
            self.standby_on()
        except ORiNException as e:
            self._logger.error(f"ORiNException: {e}")
            self._error_handling(e)
        except Exception as e:
            self._error_handling(e)

    def execute_calset(self):
        """Execute CALSET on the robot controller
        Args:
            None
        Returns:
            None
        """
        if self.bcap is None:
            self._logger.error("BCAP client is not initialized.")
            return

        try:
            self.bcap.robot_execute(self.h_rob, "AutoCal", "")
            #self.bcap.controller_execute(self.h_ctrl, 'CALSET')
            self._logger.info("Executed CALSET successfully.")
        except ORiNException as e:
            self._logger.error(f"ORiNException: {e}")
            self._error_handling(e)
        except Exception as e:
            self._error_handling(e)


def main():
    logger = getLogger(__name__)
    os.makedirs(os.path.join(os.path.dirname(sys.argv[0]), "log"), exist_ok=True)
    basicConfig(level=INFO, filename=os.path.join(os.path.dirname(sys.argv[0]), "log", "Robot.log"), format="%(asctime)s:%(levelname)s:%(message)s ")
    logger.info('rob lib rogs')
    rob = Robot()
    connected = rob.connect(ip='127.0.0.1', rc_type='RC8', name='sample')
    if connected:
        rob.clear_errors()  # Ensure any existing errors are cleared
        rob.reconnect_robotto()
        #rob.set_executable_token()  # Set the executable token to Ethernet
        rob.standby_on()
        info = rob.get_base_info()
        save_dir = '_'.join(info)
        save_dir = save_dir.replace('.', '_')
        rob.save_all_pacscript(save_dir=save_dir, first=True)
        rob.err_func()
    # End if


if __name__ == '__main__':
    main()
