# This Python file uses the following encoding: utf-8
from PyQt6 import QtWidgets, uic, QtCore
from PyQt6.QtGui import QCursor,QIcon,QPixmap,QMovie
import pyqtgraph as pg
import sys
sys.path.append("data")
import numpy as np
from Fluigent.SDK import*
import os
import pandas as pd
from classes import*
import nidaqmx
from nidaqmx.constants import AcquisitionType,TerminalConfiguration
import scipy
import time
class MainWindow(QtWidgets.QMainWindow):
    def __init__(self):
        super(MainWindow, self).__init__()
        self.setWindowTitle("CollaGui")
        self.setWindowIcon(QIcon("data/coll.png"))
        uic.loadUi('data/mainwindow.ui', self)
        self.loading = QMovie("data/load.gif")
        self.signe=1
        self.recording = 0
        self.refresh = 2
        BeauPlot(self.Plotter)
        BeauPlot(self.Plotter_2)
        BeauPlot(self.Plotter_3)
        BeauPlot(self.Plotter_4)
        BeauPlot(self.Plotter_5)
        self.wait = QtCore.QTimer(self)
        self.wait.setSingleShot(1)
        self.wait.timeout.connect(self.instr)
        self.t0=QtCore.QTime.currentTime()
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
        self.connect()
        self.ch = self.comboBox.currentIndex()
        self.comboBox.currentIndexChanged.connect(self.change_ch)
        self.radioButton.setChecked(1)
        self.pushButton_2.clicked.connect(self.setpress)
        self.meas =[]
        self.comtable =[]
        self.pushButton_8.clicked.connect(self.comsolmeas)
        self.pushButton_9.clicked.connect(self.comsolcom)
        self.pushButton_10.clicked.connect(self.comsolclear)
        self.pushButton_4.clicked.connect(self.dosave)
        self.curs = 0
        self.last = 0
        self.noerror = 1
        self.pushButton_5.clicked.connect(self.cleardata)
        self.times = []
        self.cons = []
        self.cur_wait = 0
        self.spinBox.valueChanged.connect(self.minvoltage)
        self.timers=[0]
        with open("data/lastfold.txt","r") as f:
            self.dirname = f.readlines()
        with open("data/lastcom.txt","r") as f:
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
        with open("data/lastpatt.txt","r") as f:
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
    def minvoltage(self):
        self.spinBox_2.setValue(-self.spinBox.value())
    def comsolmeas(self):
        self.filenamemeas = self.dialog.getOpenFileName(directory=self.dirname,filter = "Text files (*.txt)")[0]
        if self.filenamemeas !="":
            test, self.meas = affiche(self.Plotter_4,self.filenamemeas,(0,0,0))
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
            with open("data/lastcom.txt","w") as f:
                f.write(self.filenamecom)
            if headd == "% Model":
                self.dirname2 = "/".join(self.filenamecom.split("/")[:-1])
                with open("data/lastcom.txt","w") as f:
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
            affiche(self.Plotter_4,self.filenamemeas,(0,0,0))
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
            for i in range(0,len(self.liste_instr),4):
                patt.append([self.liste_instr[i+2].value(),self.liste_instr[i+3].value()])
            header = "pattern"
            np.savetxt(self.filename2,np.array(patt),header=header)
    def import_pattern(self,fnm):
        if fnm != "":
            patterntxt = pd.read_fwf(fnm)
            if patterntxt.head(0).columns.tolist()[0] == "# pattern":
                patterntxt = patterntxt.to_numpy()
                self.clearInstr()
                self.liste_instr[-2].setValue(int(patterntxt[0][0]))
                self.liste_instr[-1].setValue(int(patterntxt[0][1]))
                for i in range(1,len(patterntxt)):
                    self.addInstr()
                    self.liste_instr[-2].setValue(int(patterntxt[i][0]))
                    self.liste_instr[-1].setValue(int(patterntxt[i][1]))
    def import_clicked(self):
        self.filename2 = self.dialog.getOpenFileName(directory=self.dirname,filter = "Text files (*.txt)")[0]
        self.import_pattern(self.filename2)
        with open("data/lastpatt.txt","w") as f:
            f.write(self.filename2)
    def change_ch(self):
        fgt_set_pressure(self.ch,0)
        self.ch = self.comboBox.currentIndex()
    def cleardata(self):
        self.t0=QtCore.QDateTime.currentTime()
        self.time,self.ft,self.ph = [],[],[]
        self.Plotter_2.clear()
        self.task.stop()
        self.task.start()
    def connect(self):
        if self.pushButton_19.isChecked():
            initiation = fgt_init()
            system = nidaqmx.system.System.local()
            device = system.devices['Dev1']
            if initiation != 0 or not(device in system.devices):
                self.pushButton_19.setChecked(0)
                self.pushButton_19.setText("Connect")
            else:
                self.pushButton_19.setChecked(1)
                self.pushButton_19.setText("Connected")
                fgt_set_sessionPressureUnit("Pa")
                self.task = nidaqmx.Task()
                self.task.ai_channels.add_ai_voltage_chan('Dev1/ai0',min_val=self.spinBox_2.value()/1000, max_val=self.spinBox.value()/1000)
                self.task.ai_channels.add_ai_voltage_chan('Dev1/ai1',min_val=self.spinBox_2.value()/1000, max_val=self.spinBox.value()/1000)
                self.task.timing.cfg_samp_clk_timing(1000*self.spinBox_3.value(), sample_mode=AcquisitionType.CONTINUOUS)
                self.task.register_every_n_samples_acquired_into_buffer_event(int(1000*self.spinBox_3.value()/self.refresh), self.update)
                self.t0=QtCore.QTime.currentTime()
                self.task.start()
        else:
            fgt_close()
            self.pushButton_19.setText("Connect")
            try:
                self.task.stop()
                self.task.close()
            except:
                pass
    def setpress(self):
        fgt_set_pressure(self.ch,self.doubleSpinBox_2.value())
    def open_valve(self):
        if self.checkBox.isChecked():
            with nidaqmx.Task() as task:
                task.ao_channels.add_ao_voltage_chan("Dev1/ao0")
                task.write(5, auto_start=True)
        else:
            with nidaqmx.Task() as task:
                task.ao_channels.add_ao_voltage_chan("Dev1/ao0")
                task.write(0, auto_start=True)
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
            self.pushButton.setIcon(QIcon("data/recorder.png"))
            self.recording = 0
            self.progressBar.setValue(0)
            for widget in self.liste_instr:
                widget.setEnabled(1)
            self.curs =0
            self.loading.stop()
        elif not(self.checkBox.isChecked()):
                self.start()
        else:
            conf =self.valve()
            if conf==1024:
                self.start()
            else:
                self.recording = 0
                self.loading.stop()
                self.progressBar.setValue(0)
                self.pushButton.setChecked(0)
    def start(self):
        self.filename = self.dialog.getSaveFileName(directory=self.dirname,filter = "Text files (*.txt)")[0]
        if self.filename =="":
            self.noerror = 0
        else:
            self.lineEdit.setProperty("text",self.filename)
            self.noerror = 1
            with open("data/lastfold.txt","w") as f:
                f.write(self.filename)
        if self.noerror:
            for widget in self.liste_instr:
                widget.setDisabled(1)
            self.pushButton.setProperty("text","Stop")
            self.pushButton.setIcon(QIcon("data/record.png"))
            self.curs = 0
            self.loading.start()
            self.instr()
        else:
            self.pushButton.setChecked(0)
    def save(self,fnm):
        header = "MEAS time(s) Pm Ph " + self.t0.toString("yyyy-MM-dd HH:mm")
        header += "\n"+str(self.times) +"\n"+str(self.cons)
        if self.checkBox_2.isChecked():
            header+= "\nInverted"
        else:
            header += "\nNormal"
        np.savetxt(fnm,np.column_stack((np.array(self.time),np.array(self.ft),np.array(self.ph))),header=header,delimiter = "\t",newline='\n')
    def instr(self):
        if self.curs<len(self.liste_instr):
            self.times.append(len(self.time))
            if self.curs != 0:
                self.liste_instr[self.curs-4].setMovie(QMovie())
                self.liste_instr[self.curs-4].setPixmap(QPixmap("data/done.png").scaled(20,20))
                self.disp()
            self.cons.append(self.liste_instr[self.curs+2].value()*100)
            self.last = self.liste_instr[self.curs+2].value()*100
            self.recording = 1
            self.cur_wait = self.liste_instr[self.curs+3].value()*1000
            self.wait.start(self.cur_wait)
            fgt_set_pressure(self.ch,self.liste_instr[self.curs+2].value()*100)
            self.liste_instr[self.curs].setEnabled(1)
            self.liste_instr[self.curs].setMovie(self.loading)
            self.curs += 4
        else:
            self.times.append(len(self.time))
            self.disp()
            self.recording = 0
            self.progressBar.setValue(0)
            self.liste_instr[self.curs-4].setMovie(QMovie())
            self.liste_instr[self.curs-4].setPixmap(QPixmap("data/done.png").scaled(20,20))
            self.loading.stop()
            self.pushButton.setProperty("text","Start")
            self.pushButton.setIcon(QIcon("data/recorder.png"))
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
            with open("data/lastfold.txt","w") as f:
                f.write(self.dirname)

    def getsave2(self):
        self.filename4 = self.dialog.getOpenFileName(directory=self.dirname,filter = "Text files (*.txt)")[0]
        if self.filename4 =="":
            self.noerror = 0
        else:
            col = (np.random.randint(200,size=3))
            if affiche(self.Plotter_3,self.filename4,col)[0]:
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
        self.timers.append(-QtCore.QTime.currentTime().msecsTo(self.t0)/1000)
        data = np.array(self.task.read(number_of_samples_per_channel=number_of_samples))
        n = int(self.spinBox_3.value()*self.spinBox_4.value())
        points = int(len(data[0])/n)
        self.ft = np.concatenate((self.ft,np.nanmean(data[0].reshape(n,-1),axis=0)))
        self.ph = np.concatenate((self.ph,np.nanmean(data[1].reshape(n,-1),axis=0)))
        time = np.linspace(self.timers[-2],self.timers[-1],points)
        self.time = np.concatenate((self.time,time))
        self.ftcurve.setData(self.time,self.ft)
        self.phcurve.setData(self.time,self.ph)
        if self.recording:
            self.progressBar.setValue(int(((-QtCore.QTime.currentTime().msecsTo(self.t0)-self.time[self.times[-1]]*1000)/(self.cur_wait))*100))
        return 0
    def addInstr(self):
        self.liste_instr.append(QtWidgets.QLabel())
        self.liste_instr[-1].setProperty("minimumSize","25 x 25")
        self.liste_instr[-1].setProperty("maximumSize","25 x 25")
        self.liste_instr[-1].setProperty("sizePolicy","[Fixed,Fixed,0,0]")
        self.liste_instr.append(QtWidgets.QComboBox())
        self.liste_instr[-1].setProperty("minimumSize","100 x 25")
        self.liste_instr[-1].setProperty("sizePolicy","[Expanding,Maximum,0,0]")
        self.liste_instr[-1].addItem("Set pressure")
        self.liste_instr[-1].setCursor(QCursor(QtCore.Qt.CursorShape.PointingHandCursor))
        self.liste_instr.append(QtWidgets.QDoubleSpinBox())
        self.liste_instr[-1].setProperty("minimumSize","90 x 25")
        self.liste_instr[-1].setProperty("minimum","0")
        self.liste_instr[-1].setProperty("maximum","50")
        self.liste_instr[-1].setProperty("value","1")
        self.liste_instr[-1].setCursor(QCursor(QtCore.Qt.CursorShape.PointingHandCursor))
        self.liste_instr.append(QtWidgets.QSpinBox())
        self.liste_instr[-1].setProperty("MinimumSize","90 x 25")
        self.liste_instr[-1].setProperty("minimum","0")
        self.liste_instr[-1].setProperty("maximum","9999")
        self.liste_instr[-1].setProperty("value","200")
        self.liste_instr[-1].setCursor(QCursor(QtCore.Qt.CursorShape.PointingHandCursor))
        siz = len(self.liste_instr)
        self.gridLayout_2.addWidget(self.liste_instr[-4],int(siz/4),1,QtCore.Qt.AlignmentFlag.AlignTop)
        self.gridLayout_2.addWidget(self.liste_instr[-3],int(siz/4),2,QtCore.Qt.AlignmentFlag.AlignTop)
        self.gridLayout_2.addWidget(self.liste_instr[-2],int(siz/4),3,QtCore.Qt.AlignmentFlag.AlignTop)
        self.gridLayout_2.addWidget(self.liste_instr[-1],int(siz/4),4,QtCore.Qt.AlignmentFlag.AlignTop)
        for i in range(0,len(self.liste_instr),4):
            self.liste_instr[i].clear()
    def clearInstr(self):
        if len(self.liste_instr)>4:
            for widget in self.liste_instr[4:]:
                widget.setParent(None)
                widget.deleteLater()
            self.liste_instr = self.liste_instr[:4]
            self.liste_instr[-2].setProperty("value","1")
            self.liste_instr[-1].setProperty("value","300")
        for i in range(0,len(self.liste_instr),4):
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
        if (len(self.cons)==1 and not(self.checkBox_2.isChecked())) or (self.cons[-1]-self.cons[-2]>0 and not(self.checkBox_2.isChecked())) or (self.cons[-1]-self.cons[-2]<0 and self.checkBox_2.isChecked()):
            pens = pg.mkPen(color=col,width = 2)
        else:
            pens = pg.mkPen(color=col,width = 2)
            pens.setDashPattern([3,8])
        self.Plotter_2.plot(np.array(self.time[self.times[-2]:self.times[-1]])-self.time[self.times[-2]],(np.array(self.ph[self.times[-2]:self.times[-1]])-self.ph[self.times[-2]]),pen=pens)


if __name__ == "__main__":
    app = QtWidgets.QApplication(sys.argv)
    splash_pix = QPixmap('data/capy.png')
    splash = QtWidgets.QSplashScreen(splash_pix,QtCore.Qt.WindowType.WindowStaysOnTopHint)
    # add fade to splashscreen
    opaqueness = 0.0
    step = 0.1
    splash.setWindowOpacity(opaqueness)
    splash.show()
    while opaqueness < 1:
        splash.setWindowOpacity(opaqueness)
        time.sleep(step) # Gradually appears
        opaqueness+=step
    time.sleep(1) # hold image on screen for a while
    splash.close() # close the splash screen
    main = MainWindow()
    main.showMaximized()

    #main.label.setProperty("text",str(main.liste_instr[1].value()))
    sys.exit(app.exec())
    fgt_set_pressure(self.ch,0)
    fgt_close()
    try:
        self.task.stop()
        self.task.close()
    except:
        pass
