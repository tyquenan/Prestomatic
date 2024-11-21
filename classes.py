# This Python file uses the following encoding: utf-8
from PyQt6.QtCore import (
    Qt, QSize, QPoint, QPointF, QRectF,
    QEasingCurve, QPropertyAnimation, QSequentialAnimationGroup,
    pyqtSlot, pyqtProperty)
from PyQt6.QtWidgets import QCheckBox
from PyQt6.QtGui import QColor, QBrush, QPaintEvent, QPen, QPainter
import pyqtgraph as pg
import pandas as pd
import numpy as np

class AnimatedToggle(QCheckBox):

    _transparent_pen = QPen(Qt.GlobalColor.transparent)
    _light_grey_pen = QPen(Qt.GlobalColor.lightGray)

    def __init__(self,
        parent=None,
        bar_color=Qt.GlobalColor.red,
        checked_color="#014703",
        handle_color=Qt.GlobalColor.gray,
        pulse_unchecked_color="#a93435",
        pulse_checked_color="#4400B0EE"
        ):
        super().__init__(parent)

        # Save our properties on the object via self, so we can access them later
        # in the paintEvent.
        self._bar_brush = QBrush(bar_color)
        self._bar_checked_brush = QBrush(QColor(checked_color).lighter())

        self._handle_brush = QBrush(handle_color)
        self._handle_checked_brush = QBrush(QColor(checked_color))

        self._pulse_unchecked_animation = QBrush(QColor(pulse_unchecked_color))
        self._pulse_checked_animation = QBrush(QColor(pulse_checked_color))

        # Setup the rest of the widget.
        self.setContentsMargins(8, 0, 8, 0)
        self._handle_position = 0

        self._pulse_radius = 0

        self.animation = QPropertyAnimation(self, b"handle_position", self)
        self.animation.setEasingCurve(QEasingCurve.Type.InOutCubic)
        self.animation.setDuration(200)  # time in ms

        self.pulse_anim = QPropertyAnimation(self, b"pulse_radius", self)
        self.pulse_anim.setDuration(350)  # time in ms
        self.pulse_anim.setStartValue(10)
        self.pulse_anim.setEndValue(20)

        self.animations_group = QSequentialAnimationGroup()
        self.animations_group.addAnimation(self.animation)
        self.animations_group.addAnimation(self.pulse_anim)

        self.stateChanged.connect(self.setup_animation)

    def sizeHint(self):
        return QSize(58, 45)

    def hitButton(self, pos: QPoint):
        return self.contentsRect().contains(pos)

    @pyqtSlot(int)
    def setup_animation(self, value):
        self.animations_group.stop()
        if value:
            self.animation.setEndValue(1)
        else:
            self.animation.setEndValue(0)
        self.animations_group.start()

    def paintEvent(self, e: QPaintEvent):

        contRect = self.contentsRect()
        handleRadius = round(0.24 * contRect.height())

        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)

        p.setPen(self._transparent_pen)
        barRect = QRectF(
            0, 0,
            contRect.width() - handleRadius, 0.40 * contRect.height()
        )
        barRect.moveCenter(QPointF(contRect.center()))
        rounding = barRect.height() / 2

        # the handle will move along this line
        trailLength = contRect.width() - 2 * handleRadius

        xPos = contRect.x() + handleRadius + trailLength * self._handle_position

        if self.pulse_anim.state() == QPropertyAnimation.State.Running:
            p.setBrush(
                self._pulse_checked_animation if
                self.isChecked() else self._pulse_unchecked_animation)
            p.drawEllipse(QPointF(xPos, barRect.center().y()),
                          self._pulse_radius, self._pulse_radius)

        if self.isChecked():
            p.setBrush(self._bar_checked_brush)
            p.drawRoundedRect(barRect, rounding, rounding)
            p.setBrush(self._handle_checked_brush)

        else:
            p.setBrush(self._bar_brush)
            p.drawRoundedRect(barRect, rounding, rounding)
            p.setPen(self._light_grey_pen)
            p.setBrush(self._handle_brush)

        p.drawEllipse(
            QPointF(xPos, barRect.center().y()),
            handleRadius, handleRadius)

        p.end()

    @pyqtProperty(float)
    def handle_position(self):
        return self._handle_position

    @handle_position.setter
    def handle_position(self, pos):
        """change the property
        we need to trigger QWidget.update() method, either by:
            1- calling it here [ what we doing ].
            2- connecting the QPropertyAnimation.valueChanged() signal to it.
        """
        self._handle_position = pos
        self.update()

    @pyqtProperty(float)
    def pulse_radius(self):
        return self._pulse_radius

    @pulse_radius.setter
    def pulse_radius(self, pos):
        self._pulse_radius = pos
        self.update()
def BeauPlot(plt):
    plt.setBackground("w")
    styles = {"color": "black", "font-size": "10px"}
    plt.setLabel("left", "Pressure (mbar)", **styles)
    plt.setLabel("bottom", "Time (s)", **styles)
    plt.showGrid(x=True, y=True)
    plt.addLegend()
def toFloat(t):
    return t.hour()*60*60 +t.minute()*60 +t.second()+t.msec()/1000
def affiche(plt,fnm,col):
    with open(fnm,"r") as f:
        headd = f.readlines()[0][:6]
    if headd == "# MEAS":
        with open(fnm,"r") as f:
            dat = f.readlines()[1:4]
            times = [int(i) for i in dat[0][3:-2].split(", ")]
            cons = [float(i) for i in dat[1][3:-2].split(", ")]
            inverted = (dat[2] == "# Inverted")
            print(inverted)
        listes = []
        data = pd.read_fwf(fnm,skiprows = 4, index_col=False,header = None)
        time = data.iloc[:,0].values
        #pm = data.iloc[:,1].values
        ph = data.iloc[:,2].values
        for i in range(len(times)-1):
            if (i==0 and not(inverted)) or (cons[i]-cons[i-1]>0 and not inverted) or (cons[i]-cons[i-1]<0 and inverted):
                pens = pg.mkPen(color=col,width = 2)
            else:
                pens = pg.mkPen(color=col,width = 2)
                pens.setDashPattern([3,8])
            listes.append([time[times[i]:times[i+1]]-time[times[i]],(100/0.37317)*(ph[times[i]:times[i+1]]-ph[times[i]])/np.sign(cons[i]-cons[i-1])])
            plt.plot(listes[-1][0],listes[-1][1],pen=pens)
        return 1,listes
    else:
        return 0,0

