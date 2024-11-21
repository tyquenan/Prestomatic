# This Python file uses the following encoding: utf-8
import sys
from PyQt6 import QtWidgets, uic, QtCore
from PyQt6.QtGui import QCursor,QIcon,QPixmap,QMovie
import pyqtgraph as pg
import numpy as np
import Fluigent.SDK as fgt
import os

import pandas as pd
import classes as classes
import nidaqmx
from nidaqmx import stream_writers
from nidaqmx.constants import AcquisitionType,RegenerationMode,TerminalConfiguration
import scipy
import time
from PyMCP2221A import PyMCP2221A
from pycromanager import Acquisition, multi_d_acquisition_events

def resource_path(relative_path):
    """ Get absolute path to resource, works for dev and for PyInstaller """
    base_path = getattr(sys, '_MEIPASS', os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(base_path, relative_path)

class MainWindow(QtWidgets.QMainWindow):
    """
    Class that regulates the mainwindow. Initiating opens the program
    """
    progressChanged = QtCore.pyqtSignal(int)
    updategraphs = QtCore.pyqtSignal()
    updateSin = QtCore.pyqtSignal()
    def __init__(self):
        super(MainWindow, self).__init__()
        uic.loadUi(resource_path("data/mainwindow.ui"), self)
        self.setWindowTitle("Prestomatic v1.1")
        self.setWindowIcon(QIcon(resource_path("pngs/coll.png")))
        self.loading = QMovie(resource_path("pngs/load.gif"))
        self.signe=1
        self.recording = 0
        self.refresh = 2
        self.t0conf = 0
        self.t0machine = 0
        classes.BeauPlot(self.Plotter)
        classes.BeauPlot(self.Plotter_2)
        classes.BeauPlot(self.Plotter_3)
        classes.BeauPlot(self.Plotter_4)
        classes.BeauPlot(self.Plotter_5)
        classes.BeauPlot(self.Plotter_temp)
        self.wait = QtCore.QTimer(self)
        self.wait.setSingleShot(1)
        self.wait.timeout.connect(self.instr)
        self.timer_sin = QtCore.QTimer(self)
        self.timer_sin.setInterval(100)
        self.timer_sin.timeout.connect(self.sinusoidal)
        self.timer_acq = QtCore.QTimer(self)
        self.timer_acq.timeout.connect(self.acquire)
        self.t0=QtCore.QDateTime.currentDateTime()
        self.time,self.ft, self.ph = [],[],[]
        self.ftcurve = self.Plotter.plot(self.time,self.ft,name="Pm",pen=pg.mkPen(color=(0, 100, 255)))
        self.phcurve = self.Plotter.plot(self.time,self.ph,name="Ph",pen=pg.mkPen(color=(255, 0, 150)))
        self.liste_instr = []
        self.Add.clicked.connect(self.addInstr)
        self.Clear.clicked.connect(self.clearInstr)
        self.remove.clicked.connect(self.removeInstr)
        self.save_pattern.clicked.connect(self.save_patt)
        self.pattern.clicked.connect(self.import_clicked)
        self.addInstr()
        self.dialog =QtWidgets.QFileDialog(self)
        self.plots = []
        self.fold.clicked.connect(self.getsave)
        self.pushButton_7.clicked.connect(self.getsave2)
        self.pushButton_6.clicked.connect(self.clearplot)
        self.pushButton.toggled.connect(self.record)
        self.checkBox.toggled.connect(self.open_valve)
        self.pushButton_19.toggled.connect(self.connect)
        self.pushButton_3.toggled.connect(self.connect_conf)
        self.ch = self.comboBox.currentIndex()
        self.comboBox.currentIndexChanged.connect(self.change_ch)
        self.pushButton_2.clicked.connect(self.setpress)
        self.meas =[]
        self.comtable =[]
        self.pushButton_8.clicked.connect(self.comsolmeas)
        self.pushButton_9.clicked.connect(self.comsolcom)
        self.pushButton_10.clicked.connect(self.comsolclear)
        self.pushButton_4.clicked.connect(self.dosave)
        self.pushButton_11.clicked.connect(self.nextInstr)
        self.curs = 0
        self.last = 0
        self.noerror = 1
        self.pushButton_5.clicked.connect(self.cleardata)
        self.times = []
        self.cons = []
        self.cur_wait = 0
        self.spinBox.valueChanged.connect(self.minvoltage)
        self.timers=[0]
        self.progressChanged.connect(self.progressBar.setValue)
        self.updategraphs.connect(self.update_graph)
        self.spinBox_6.valueChanged.connect(self.updateAcqLength)
        self.spinBox_7.valueChanged.connect(self.updateAcqLength)
        self.memory = np.array([np.array([]),np.array([])])
        with open(resource_path("txts/lastfold.txt"),"r") as f:
            self.dirname = f.readlines()
        with open(resource_path("txts/lastcom.txt"),"r") as f:
            self.dirname2 = f.readlines()
        if len(self.dirname2) == 0:
            self.dirname2=os.getcwd()
        else:
            self.dirname2 = self.dirname[0]
        self.iscomsol = 0
        if len(self.dirname) == 0:
            self.dirname = os.getcwd()
        else:
            self.dirname= self.dirname[0]
        with open(resource_path("txts/lastpatt.txt"),"r") as f:
            self.lastpatt = f.readlines()
        if len(self.lastpatt) ==0:
            self.lastpatt = os.getcwd()
        else:
            self.lastpatt = self.lastpatt[0]
            try:
                self.import_pattern(self.lastpatt)
            except:
                pass
        self.lineEdit.setProperty("text",self.dirname)
    def updateAcqLength(self):
        counts = self.spinBox_6.value()
        interval = self.spinBox_7.value()
        length = counts*interval
        hours = length//(1000*60*60)
        min = (length - hours*1000*60*60)//(60*1000)
        sec  = (length - hours*1000*60*60 - min *60*1000)//1000
        ms  = (length - hours*1000*60*60 - min *60*1000 - sec*1000)
        self.lineEdit_4.setText("{}h {}m {}s {}ms".format(hours,min,sec,ms))
    def comsolmeas(self):
        self.filenamemeas = self.dialog.getOpenFileName(directory=self.dirname,filter = "Text files (*.txt)")[0]
        if self.filenamemeas !="":
            test, self.meas = classes.affiche(self.Plotter_4,self.filenamemeas,(0,0,0))
            if test:
                name = self.filenamemeas.split("/")[-1][:-4]
                self.textBrowser.setText(name)
                self.pushButton_8.setDisabled(1)
                self.pushButton_9.setEnabled(1)
    def comsolcom(self):
        self.filenamecom = self.dialog.getOpenFileName(directory=self.dirname2,filter = "Text files (*.txt)")[0]
        if self.filenamecom != "":
            with open(self.filenamecom,"r") as f:
                headd = f.readlines()[0][:7]
            with open(resource_path("txts/lastcom.txt"),"w") as f:
                f.write(self.filenamecom)
            if headd == "% Model":
                self.dirname2 = "/".join(self.filenamecom.split("/")[:-1])
                with open(resource_path("txts/lastcom.txt"),"w") as f:
                    f.write(self.dirname2)
                self.pushButton_9.setDisabled(1)
                with open(self.filenamecom,"r") as f:
                    names = f.readlines()[4]
                models = pd.read_fwf(self.filenamecom,names = [e+")" for e in names[1:-2].split(")")],skiprows = 5,index_col= False,header = None)
                comm,names,r = self.comsolcompare(models)
                self.textBrowser.append("Comsol file: "+self.filenamecom.split("/")[-1][:-4])
                for i in range(len(comm)):
                    self.Plotter_4.plot(models.iloc[:,0].values,comm[i],name = names[i],pen = pg.mkPen(np.random.randint(200,size =3),width =2))
                    self.textBrowser.append("fit: "+str(names[i])+", r squared: "+str(r[i])[:4])
    def comsolclear(self):
        self.Plotter_4.clear()
        self.pushButton_9.setDisabled(1)
        self.textBrowser.setText("")
        self.pushButton_8.setEnabled(1)
    def comsolcompare(self,models):
        if self.iscomsol:
            self.comsolclear()
            classes.affiche(self.Plotter_4,self.filenamemeas,(0,0,0))
        self.iscomsol = 1
        timecom = models.iloc[:,0].values
        r2max = []
        mod = []
        comm = []
        for measure in self.meas:
            r2 = []
            distances = []
            interp = np.array(np.interp(timecom,measure[0],measure[1]))
            for i in range(len(models.values[0])-1):
                distances.append(scipy.spatial.distance.sqeuclidean(interp,np.array(models.iloc[:,i+1].values)))
                r2.append(np.corrcoef(interp,np.array(models.iloc[:,i+1].values))[0,1])
            ind = distances.index(min(distances))
            r2max.append(r2[ind]**2)
            mod.append(models.columns[ind+1])
            comm.append(models.iloc[:,ind+1])
        return comm,mod,r2max
    def save_patt(self):
        patt =[]
        self.filename2 = self.dialog.getSaveFileName(directory=self.dirname,filter = "Text files (*.txt)")[0]
        if self.filename2 != "":
            for i in range(0,len(self.liste_instr),6):
                line = []
                line.append(int(self.liste_instr[i+1].currentIndex()))
                for j in range(2,6):
                    line.append(self.liste_instr[i+j].value())
                patt.append(line)
            header = "pattern"
            np.savetxt(self.filename2,np.array(patt),header=header)
    def import_pattern(self,fnm):
        if fnm != "":
            patterntxt = pd.read_fwf(fnm)
            if patterntxt.head(0).columns.tolist()[0] == "# pattern":
                patterntxt = patterntxt.to_numpy()
                for i in range(len(patterntxt)):
                    if i !=0:
                        self.addInstr()
                    self.liste_instr[-5].setCurrentIndex(int(patterntxt[i][0]))
                    if self.liste_instr[-5].currentIndex() != 2:
                        self.liste_instr[-4].setValue(int(patterntxt[i][1]))
                        self.liste_instr[-3].setValue(float(patterntxt[i][2]))
                        if self.liste_instr[-5].currentIndex() == 1:
                            self.liste_instr[-2].setValue(int(patterntxt[i][3]))
                            self.liste_instr[-1].setValue(float(patterntxt[i][4]))
    def import_clicked(self):
        self.filename2 = self.dialog.getOpenFileName(directory=self.dirname,filter = "Text files (*.txt)")[0]
        self.import_pattern(self.filename2)
        with open(resource_path("txts/lastpatt.txt"),"w") as f:
            f.write(self.filename2)
    def change_ch(self):
        fgt.fgt_set_pressure(self.ch,0)
        self.ch = self.sender().currentIndex()
    def cleardata(self):
        self.time,self.ft,self.ph = [],[],[]
        self.t0 =QtCore.QDateTime.currentDateTime()
        self.reset_ni()
        self.timers = [0]
        self.Plotter.clear()
        self.Plotter_2.clear()
        self.ftcurve = self.Plotter.plot(self.time,self.ft,name="Pm",pen=pg.mkPen(color=(0, 100, 255)))
        self.phcurve = self.Plotter.plot(self.time,self.ph,name="Ph",pen=pg.mkPen(color=(255, 0, 150)))
    def reset_ni(self):
        self.liste_volt = [.1,.2,.5,1,2,5,10]
        self.task = nidaqmx.Task()
        self.task.ai_channels.add_ai_voltage_chan('Dev1/ai0',terminal_config = TerminalConfiguration.DIFF,min_val=-self.liste_volt[self.spinBox.currentIndex()], max_val=self.liste_volt[self.spinBox.currentIndex()])
        self.task.ai_channels.add_ai_voltage_chan('Dev1/ai1',terminal_config = TerminalConfiguration.DIFF,min_val=-self.liste_volt[self.spinBox.currentIndex()], max_val=self.liste_volt[self.spinBox.currentIndex()])
        self.task.ai_channels.add_ai_voltage_chan('Dev1/ai2',terminal_config = TerminalConfiguration.DIFF,min_val=-self.liste_volt[self.spinBox.currentIndex()], max_val=self.liste_volt[self.spinBox.currentIndex()])
        self.task.timing.cfg_samp_clk_timing(1000*self.spinBox_3.value(), sample_mode=AcquisitionType.CONTINUOUS,samps_per_chan= self.bufsize)
        self.task.register_every_n_samples_acquired_into_buffer_event(self.bufsize, self.update)
        self.task.start()
    def connect(self):
        self.confocal = False
        if self.sender().isChecked():
            try:
                fgt.fgt_init()
                #initiation = fgt.fgt_init()
                #initiation = 0
                system = nidaqmx.system.System.local()
                device = system.devices['Dev1']
            except:
                self.sender().setChecked(0)
                self.sender().setText("Connect")
            else:
                self.bufsize = int(self.spinBox_5.value()*1000)
                self.sender().setChecked(1)
                self.sender().setText("Connected")
                self.t0=QtCore.QDateTime.currentDateTime()
                self.reset_ni()
                self.task_valve = nidaqmx.Task()
                self.task_valve.ao_channels.add_ao_voltage_chan("Dev1/ao0",min_val= -5,max_val = 5)
                self.task_valve.out_stream.regen_mode = RegenerationMode.ALLOW_REGENERATION
                self.writer = stream_writers.AnalogSingleChannelWriter(self.task_valve.out_stream)
        else:
            fgt.fgt_close()
            self.sender().setText("Connect")
            try:
                self.task.close()
                self.task_valve.close()
            except:
                pass
    def connect_conf(self):
        self.confocal = True
        if self.sender().isChecked():
            try:
                #initiation = fgt.fgt_init()
                fgt.fgt_init()
                self.mcp2221 = PyMCP2221A.PyMCP2221A(VID = 0x04D8, PID = 0xec79)
                self.mcp2221.I2C_Init()
            except:
                self.sender().setChecked(0)
                fgt.fgt_close()
                self.sender().setText("Connect")
                self.timer.stop()
            else:
                self.Pmax = 0.15
                self.Pmin = -0.15
                self.MAX = 16384
                self.sender().setChecked(1)
                self.sender().setText("Connected")
                self.timer = QtCore.QTimer(self)
                self.timer.setInterval(100)
                self.timer.timeout.connect(self.update_conf)
                self.timer.start()
                self.acq = Acquisition(directory='./AcquisitionData', name='acquisition_name')
                self.timer_leica = QtCore.QTimer(self)
                self.timer_leica.timeout.connect(self.acquire)
                self.t0=QtCore.QDateTime.currentDateTime()
        else:
            try:
                fgt.fgt_close()
                self.sender().setText("Connect")
                self.timer.stop()
            except:
                self.sender().setText("Connect")
    def setpress(self):
        fgt.fgt_set_pressure(self.ch,self.doubleSpinBox_2.value())
    def open_valve(self):
        if self.checkBox.isChecked():
            self.writer.write_one_sample(5.0)
        else:
            self.writer.write_one_sample(0.0)
    def valve(self):
        warn = QtWidgets.QMessageBox()
        warn.setIcon(QtWidgets.QMessageBox.Icon.Information)
        warn.setWindowTitle("Warning!")
        warn.setText("The valve is opened. Continue?")
        QBtn = QtWidgets.QMessageBox.StandardButton.Ok | QtWidgets.QMessageBox.StandardButton.Cancel
        warn.setStandardButtons(QBtn)
        return warn.exec()
    def record(self):
        if not self.pushButton.isChecked():
            self.pushButton.setProperty("text","Start")
            self.pushButton.setIcon(QIcon(resource_path("pngs/recorder.png")))
            self.recording = 0
            self.progressBar.reset()
            for widget in self.liste_instr:
                widget.setEnabled(1)
            self.curs =0
            self.loading.stop()
        elif not(self.checkBox.isChecked()):
                self.start()
        else:
            if not self.confocal:
                conf =self.valve()
            if self.confocal or conf==1024:
                self.start()
            else:
                self.recording = 0
                self.loading.stop()
                self.progressBar.reset()
                self.pushButton.setChecked(0)
    def start(self):
        self.filename = self.dialog.getSaveFileName(directory=self.dirname,filter = "Text files (*.txt)")[0]
        if self.filename =="":
            self.noerror = 0
        else:
            self.lineEdit.setProperty("text",self.filename)
            self.noerror = 1
            with open(resource_path("txts/lastfold.txt"),"w") as f:
                f.write(self.filename)
        if self.noerror:
            for widget in self.liste_instr:
                widget.setDisabled(1)
            for i in range(0,len(self.liste_instr),6):
                self.liste_instr[i].setPixmap(QPixmap())
            self.pushButton.setProperty("text","Stop")
            self.pushButton.setStyleSheet("QPushButton {color: rgb(170, 0, 0)}")
            self.pushButton.setIcon(QIcon(resource_path("pngs/record.png")))
            self.curs = 0
            self.loading.start()
            self.times=[]
            self.cons =[]
            self.acquireTimeStamps = []
            self.instr()
            self.recording = 1
            if self.confocal:
                self.counts=0
                self.timer_leica.setInterval(self.spinBox_7.value())
                self.timer_leica.start()
        else:
            self.pushButton.setChecked(0)
    def save(self,fnm):
        header = "MEAS time(s) Pm Ph " + self.t0.toString("yyyy-MM-dd HH:mm")
        if self.confocal:
            pass
        header += "\n"+str(self.times) +"\n"+str(self.cons) + "\n" + str(self.acquireTimeStamps)
        if self.checkBox_2.isChecked():
            header+= "\nInverted"
        else:
            header += "\nNormal"
        np.savetxt(fnm,np.column_stack((np.array(self.time),np.array(self.ft),np.array(self.ph))),header=header,delimiter = "\t",newline='\n')
    def sinusoidal(self):
        phase = QtCore.QDateTime.currentDateTime().msecsTo(self.t0_sin)/self.period
        val = self.off + self.amp*np.sin(2*np.pi*phase)
        print(2*np.pi*phase)
        print(val)
        fgt.fgt_set_pressure(self.ch,val)
    def acquire(self):
        events = multi_d_acquisition_events(num_time_points=1)
        self.acq.acquire(events)
        self.counts+=1
        self.acquireTimeStamps.append(len(self.time)-1)
        if self.counts == self.spinBox_6.value():
            self.timer_leica.stop()
    def instr(self):
        if self.timer_sin.isActive():
            self.timer_sin.stop()
        if self.curs<len(self.liste_instr):                                                     #If not last instruction
            if self.curs != 0:
                self.liste_instr[self.curs-6].setMovie(QMovie())
                self.liste_instr[self.curs-6].setPixmap(QPixmap(resource_path("pngs/done.png")).scaled(20,20))
                self.disp()
            self.times.append(len(self.time)-1)                                                 #Add the current time index to the instruction time memory list
            self.cur_wait = self.liste_instr[self.curs+2].value()*1000
            constemp = [self.liste_instr[self.curs +1].currentIndex()]
            for box in self.liste_instr[self.curs +2:self.curs +6]:
                constemp.append(box.value())
            self.cons.append(constemp)
            if self.liste_instr[self.curs+1].currentIndex()==0:                                 #Constant instruction
                fgt.fgt_set_pressure(self.ch,self.liste_instr[self.curs+2].value())
            elif self.liste_instr[self.curs+1].currentIndex()==1:                               #Sinusoidal
                self.off= self.liste_instr[self.curs+3].value()
                self.amp = self.liste_instr[self.curs+5].value()
                self.period = self.liste_instr[self.curs+4].value()
                self.t0_sin = QtCore.QDateTime.currentDateTime()
                self.timer_sin.start()
            self.wait.start(self.cur_wait)
            self.liste_instr[self.curs].setEnabled(1)
            self.liste_instr[self.curs].setMovie(self.loading)
            self.curs += 6
        else:
            self.times.append(len(self.time)-1)
            self.disp()
            self.recording = 0
            self.progressBar.reset()
            self.liste_instr[self.curs-6].setMovie(QMovie())
            self.liste_instr[self.curs-6].setPixmap(QPixmap(resource_path("pngs/done.png")).scaled(20,20))
            self.loading.stop()
            self.pushButton.setProperty("text","Start")
            self.pushButton.setIcon(QIcon(resource_path("pngs/recorder.png")))
            self.pushButton.setChecked(0)
            for widget in self.liste_instr:
                widget.setEnabled(1)
            self.curs =0
            self.save(self.filename)

    def getsave(self):
        self.dirname = self.dialog.getExistingDirectory(directory=self.dirname)
        if self.dirname =="":
            self.noerror = 0
        else:
            self.lineEdit.setProperty("text",self.dirname)
            self.noerror = 1
            with open(resource_path("txts/lastfold.txt"),"w") as f:
                f.write(self.dirname)

    def getsave2(self):
        self.filename4 = self.dialog.getOpenFileName(directory=self.dirname,filter = "Text files (*.txt)")[0]
        if self.filename4 =="":
            self.noerror = 0
        else:
            col = (np.random.randint(200,size=3))
            if classes.affiche(self.Plotter_3,self.filename4,col)[0]:
                name = self.filename4.split("/")[-1][:-4]
                self.noerror = 1
                self.plots.append(QtWidgets.QLabel())
                self.plots[-1].setProperty("text",name)
                self.verticalLayout_2.addWidget(self.plots[-1],QtCore.Qt.AlignmentFlag.AlignTop)
    def clearplot(self):
        self.Plotter_3.clear()
        for widget in self.plots:
            widget.setParent(None)
            widget.deleteLater()
        self.plots = []

    def dosave(self):
        self.filename3 = self.dialog.getSaveFileName(directory=self.dirname,filter = "Text files (*.txt)")[0]
        if self.filename3 != "":
            self.save(self.filename3)
    def update(self,task_handle, every_n_samples_event_type, number_of_samples, callback_data):
        self.timers.append(-QtCore.QDateTime.currentDateTime().msecsTo(self.t0)/1000)
        data = np.array(self.task.read(number_of_samples_per_channel=number_of_samples))
        n = int((self.bufsize/self.spinBox_3.value())/self.spinBox_4.value())
        data0 = np.concatenate((self.memory[0],data[0]))
        data1 = np.concatenate((self.memory[1],data[1]))
        data2 =  np.concatenate((self.memory[2],data[2]))
        self.ft = np.concatenate((self.ft,np.nanmean(data2[:len(data2)-self.bufsize%n].reshape(n,-1),axis=1)))
        self.ph = np.concatenate((self.ph,np.nanmean(data1[:len(data1)-self.bufsize%n].reshape(n,-1),axis=1)))
        self.temp = np.concatenate((self.ph,np.nanmean(data0[:len(data0)-self.bufsize%n].reshape(n,-1),axis=1)))
        time = np.linspace(self.timers[-2],self.timers[-1],n)
        self.time = np.concatenate((self.time,time))
        self.memory = np.array([data0[len(data0)-self.bufsize%n:],data1[len(data1)-self.bufsize%n:],data2[len(data2)-self.bufsize%n:]])
        self.updategraphs.emit()
        if self.recording:
            percentage = int(((self.time[-1]-self.time[self.times[-1]])/(self.cur_wait))*100000)
            self.progressChanged.emit(percentage)
        return 0
    def update_conf(self):
        self.timers.append(-QtCore.QDateTime.currentDateTime().msecsTo(self.t0)/1000)
        n=1
        #data = self.mcp2221.I2C_Read(0x28,2)
        #data[0],data[1] = '{0:08b}'.format(data[0]),'{0:08b}'.format(data[1])
        #data = int((str(data[0])+data[1]),2)
        data = 0
        self.ph.append(((self.Pmax-self.Pmin)*((data-0.1*self.MAX)/(0.8*self.MAX)) + self.Pmin)*68.94757)
        #self.ft.append(fgt.fgt_get_pressure(self.ch))
        self.ft.append(0)
        times = np.linspace(self.timers[-2],self.timers[-1],n)
        self.time = np.concatenate((self.time,times))
        self.updategraphs.emit()
        if self.recording:
            percentage = int(((self.time[-1]-self.time[self.times[-1]])/(self.cur_wait))*100000)
            self.progressChanged.emit(percentage)
        return 0

    def update_graph(self):
        self.ftcurve.setData(self.time,self.ft)
        self.phcurve.setData(self.time,self.ph)
        self.tempcurve.setData(self.time,self.temp)
    def adapt_instr(self):
        """
        Adapting the automatisation pannel to the instruction's index
        """
        comb = self.liste_instr.index(self.sender())
        if self.sender().currentIndex() == 0:
            for i in range(1,3):
                self.liste_instr[comb+i].setEnabled(1)
                self.liste_instr[comb+i].show()
            for i in range(3,5):
                self.liste_instr[comb+i].setDisabled(1)
                self.liste_instr[comb+i].hide()
        elif self.sender().currentIndex() == 1:
            for i in range(1,5):
                self.liste_instr[comb+i].setEnabled(1)
                self.liste_instr[comb+i].show()
        elif self.sender().currentIndex() == 2:
            for i in range(2,5):
                self.liste_instr[comb+i].setDisabled(1)
                self.liste_instr[comb+i].hide()

    def addInstr(self):
        """
        Adding instructions to the automatisation pannel
        Current instructions: index 0 -> constant input
        index 1 -> Periodic input
        index 2 -> Idling
        """
        self.liste_instr.append(QtWidgets.QLabel())                                                         #Loading screen
        self.liste_instr[-1].setProperty("minimumSize","25 x 25")
        self.liste_instr[-1].setProperty("maximumSize","25 x 25")
        self.liste_instr[-1].setProperty("sizePolicy","[Fixed,Fixed,0,0]")
        self.liste_instr.append(QtWidgets.QComboBox())                                                      #Instruction
        self.liste_instr[-1].setProperty("minimumSize","100 x 25")
        self.liste_instr[-1].setProperty("sizePolicy","[Fixed,Maximum,0,0]")
        self.liste_instr[-1].addItem(QIcon(QPixmap(resource_path("pngs/trait.png"))),"")
        self.liste_instr[-1].addItem(QIcon(QPixmap(resource_path("pngs/sin.png"))),"")
        self.liste_instr[-1].addItem(QIcon(QPixmap(resource_path("pngs/wait.png"))),"")
        self.liste_instr[-1].setCursor(QCursor(QtCore.Qt.CursorShape.PointingHandCursor))
        self.liste_instr[-1].currentIndexChanged.connect(self.adapt_instr)
        self.liste_instr.append(QtWidgets.QSpinBox())                                                       #Time
        self.liste_instr[-1].setProperty("MinimumSize","90 x 25")
        self.liste_instr[-1].setProperty("minimum","1")
        self.liste_instr[-1].setProperty("maximum","99999")
        self.liste_instr[-1].setProperty("value","200")
        self.liste_instr[-1].setSuffix(" s")
        self.liste_instr[-1].setCursor(QCursor(QtCore.Qt.CursorShape.PointingHandCursor))                   #Offset
        self.liste_instr.append(QtWidgets.QDoubleSpinBox())
        self.liste_instr[-1].setProperty("minimumSize","90 x 25")
        self.liste_instr[-1].setProperty("minimum","0")
        self.liste_instr[-1].setProperty("maximum","100")
        self.liste_instr[-1].setProperty("value","1")
        self.liste_instr[-1].setSuffix(" mbar")
        self.liste_instr[-1].setCursor(QCursor(QtCore.Qt.CursorShape.PointingHandCursor))
        self.liste_instr.append(QtWidgets.QSpinBox())                                                       #Period
        self.liste_instr[-1].setProperty("MinimumSize","90 x 25")
        self.liste_instr[-1].setProperty("minimum","1")
        self.liste_instr[-1].setProperty("maximum","99999")
        self.liste_instr[-1].setProperty("value","1000")
        self.liste_instr[-1].setSuffix(" ms")
        self.liste_instr[-1].setCursor(QCursor(QtCore.Qt.CursorShape.PointingHandCursor))
        self.liste_instr[-1].setDisabled(1)
        self.liste_instr[-1].hide()
        self.liste_instr.append(QtWidgets.QDoubleSpinBox())                                                       #Amplitude
        self.liste_instr[-1].setProperty("MinimumSize","90 x 25")
        self.liste_instr[-1].setProperty("minimum","0")
        self.liste_instr[-1].setProperty("maximum","100")
        self.liste_instr[-1].setProperty("value","1")
        self.liste_instr[-1].setSuffix(" mbar")
        self.liste_instr[-1].setCursor(QCursor(QtCore.Qt.CursorShape.PointingHandCursor))
        self.liste_instr[-1].setDisabled(1)
        self.liste_instr[-1].hide()
        siz = len(self.liste_instr)
        for i,widg in enumerate(self.liste_instr[-6:]):
            self.gridLayout_2.addWidget(widg,int(siz/6),i+1,QtCore.Qt.AlignmentFlag.AlignTop)
        for i in range(0,len(self.liste_instr),6):
            self.liste_instr[i].clear()
    def nextInstr(self):
        self.wait.stop()
        self.instr()
    def clearInstr(self):
        if len(self.liste_instr)>6:
            for widget in self.liste_instr[6:]:
                widget.setParent(None)
                widget.deleteLater()
            self.liste_instr = self.liste_instr[:6]
            self.liste_instr[-2].setProperty("value","1")
            self.liste_instr[-1].setProperty("value","200")
        for i in range(0,len(self.liste_instr),6):
            self.liste_instr[i].clear()

    def removeInstr(self):
        if len(self.liste_instr)>4:
            for widget in self.liste_instr[-4:]:
                widget.setParent(None)
                widget.deleteLater()
            self.liste_instr = self.liste_instr[:-4]
        for i in range(0,len(self.liste_instr),4):
            self.liste_instr[i].clear()
    def disp(self):
        col = (np.random.randint(200,size=3))
        pens = pg.mkPen(color=col,width = 2)
        self.Plotter_2.plot(np.array(self.time[self.times[-2]:self.times[-1]])-self.time[self.times[-2]],(np.array(self.ph[self.times[-2]:self.times[-1]])-self.ph[self.times[-2]]),pen=pens)


if __name__ == "__main__":
    app = QtWidgets.QApplication(sys.argv)
    splash_pix = QPixmap(resource_path("pngs/capy.png")).scaled(400,200)
    splash = QtWidgets.QSplashScreen(splash_pix,QtCore.Qt.WindowType.WindowStaysOnTopHint)
    # add fade to splashscreen
    opaqueness = 0.0
    step = 0.001
    splash.setWindowOpacity(opaqueness)
    splash.show()
    while opaqueness <= 1:
        splash.setWindowOpacity(opaqueness)
        time.sleep(step) # Gradually appears
        opaqueness+=step
    time.sleep(1.5) # hold image on screen for a while
    splash.close() # close the splash screen
    main = MainWindow()
    main.showMaximized()
    sys.exit(app.exec())
    fgt.fgt_set_pressure(main.ch,0)
    fgt.fgt_close()
    try:
        main.task.stop()
        main.task.close()
        main.task_valve.stop()
        main.task_valve.close()
    except:
        pass
