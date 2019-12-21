#  NanoVNASaver
#  A python program to view and export Touchstone data from a NanoVNA
#  Copyright (C) 2019.  Rune B. Broberg
#
#  This program is free software: you can redistribute it and/or modify
#  it under the terms of the GNU General Public License as published by
#  the Free Software Foundation, either version 3 of the License, or
#  (at your option) any later version.
#
#  This program is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License
#  along with this program.  If not, see <https://www.gnu.org/licenses/>.
import math
import logging
from typing import List, NamedTuple

from PyQt5 import QtGui, QtWidgets, QtCore
from PyQt5.QtCore import pyqtSignal

from NanoVNASaver import RFTools
from NanoVNASaver.Formatting import \
    format_frequency, format_capacitance, format_inductance, \
    format_complex_imp, format_resistance, format_vswr, format_phase, \
    format_q_factor, format_gain, format_group_delay

from NanoVNASaver.Inputs import MarkerFrequencyInputWidget as \
    FrequencyInput


class Field(NamedTuple):
    fieldname: str
    name: str
    description: str
    default_active: bool


LABELS = (
    Field("actualfreq", "Frequency", "Actual frequency", True),
    Field("impedance", "Impedance", "Impedance",  True),
    Field("admittance", "Admittance", "Admittance", False),
    Field("serr", "Series R", "Series R", False),
    Field("serlc", "Series X", "Series equivalent L/C", False),
    Field("serl", "Series L", "Series equivalent L", True),
    Field("serc", "Series C", "Series equivalent C", True),
    Field("parr", "Parallel R", "Parallel R", True),
    Field("parlc", "Parallel X", "Parallel equivalent L/C", True),
    Field("parl", "Parallel L", "Parallel equivalent L", False),
    Field("parc", "Parallel C", "Parallel equivalent C", False),
    Field("vswr", "VSWR", "VSWR", True),
    Field("returnloss", "Return loss", "Return loss", True),
    Field("s11q", "Quality factor", "S11 Quality factor", True),
    Field("s11phase", "S11 Phase", "S11 Phase", True),
    Field("s11groupdelay", "S11 Group Delay", "S11 Group Delay", False),
    Field("s21gain", "S21 Gain", "S21 Gain", True),
    Field("s21phase", "S21 Phase", "S21 Phase", True),
    Field("s21groupdelay", "S21 Group Delay", "S21 Group Delay", False),
)

logger = logging.getLogger(__name__)


def default_field_names():
    return [l.fieldname for l in LABELS if l.default_active]


class MarkerLabel(QtWidgets.QLabel):
    def __init__(self, name):
        super().__init__("")
        self.name = name


class Marker(QtCore.QObject):
    name = "Marker"
    color = QtGui.QColor()
    coloredText = True
    location = -1

    returnloss_is_positive = False

    updated = pyqtSignal(object)

    fieldSelection = []

    def __init__(self, name, initialColor, frequency=""):
        super().__init__()
        self.name = name

        self.frequency = RFTools.RFTools.parseFrequency(frequency)

        self.frequencyInput = FrequencyInput()
        self.frequencyInput.setAlignment(QtCore.Qt.AlignRight)
        self.frequencyInput.textEdited.connect(self.setFrequency)

        ###############################################################
        # Data display label
        ###############################################################
        self.label = {}
        for l in LABELS:
            self.label[l.fieldname] = QtWidgets.QLabel("")
        self.label['actualfreq'].setMinimumWidth(100)
        self.label['returnloss'].setMinimumWidth(80)

        self.fields = {}
        for l in LABELS:
            self.fields[l.fieldname] = (l.name, self.label[l.fieldname])

        ###############################################################
        # Marker control layout
        ###############################################################

        self.btnColorPicker = QtWidgets.QPushButton("█")
        self.btnColorPicker.setFixedWidth(20)
        self.btnColorPicker.clicked.connect(
            lambda: self.setColor(QtWidgets.QColorDialog.getColor(
                self.color, options=QtWidgets.QColorDialog.ShowAlphaChannel))
        )
        self.isMouseControlledRadioButton = QtWidgets.QRadioButton()

        self.layout = QtWidgets.QHBoxLayout()
        self.layout.addWidget(self.frequencyInput)
        self.layout.addWidget(self.btnColorPicker)
        self.layout.addWidget(self.isMouseControlledRadioButton)

        ###############################################################
        # Data display layout
        ###############################################################

        self.group_box = QtWidgets.QGroupBox(self.name)
        self.group_box.setMaximumWidth(340)
        box_layout = QtWidgets.QHBoxLayout(self.group_box)

        self.setColor(initialColor)

        line = QtWidgets.QFrame()
        line.setFrameShape(QtWidgets.QFrame.VLine)

        # line only if more then 3 selected
        self.left_form = QtWidgets.QFormLayout()
        self.right_form = QtWidgets.QFormLayout()
        box_layout.addLayout(self.left_form)
        box_layout.addWidget(line)
        box_layout.addLayout(self.right_form)

        self.buildForm()

    def _size_str(self) -> str:
        return str(self.group_box.font().pointSize())

    def setScale(self, scale):
        self.group_box.setMaximumWidth(int(340 * scale))
        self.label['actualfreq'].setMinimumWidth(int(100 * scale))
        self.label['actualfreq'].setMinimumWidth(int(100 * scale))
        self.label['returnloss'].setMinimumWidth(int(80 * scale))
        if self.coloredText:
            color_string = QtCore.QVariant(self.color)
            color_string.convert(QtCore.QVariant.String)
            self.group_box.setStyleSheet(
                f"QGroupBox {{ color: {color_string.value()}; "
                f"font-size: {self._size_str()}}};"
            )
        else:
            self.group_box.setStyleSheet(
                f"QGroupBox {{ font-size: {self._size_str()}}};"
            )

    def buildForm(self):
        while self.left_form.count() > 0:
            old_row = self.left_form.takeRow(0)
            old_row.fieldItem.widget().hide()
            old_row.labelItem.widget().hide()

        while self.right_form.count() > 0:
            old_row = self.right_form.takeRow(0)
            old_row.fieldItem.widget().hide()
            old_row.labelItem.widget().hide()

        if len(self.fieldSelection) <= 3:
            for field in self.fieldSelection:
                if field in self.fields:
                    label, value = self.fields[field]
                    self.left_form.addRow(label + ":", value)
                    value.show()
        else:
            left_half = math.ceil(len(self.fieldSelection)/2)
            right_half = len(self.fieldSelection)
            for i in range(left_half):
                field = self.fieldSelection[i]
                if field in self.fields:
                    label, value = self.fields[field]
                    self.left_form.addRow(label + ":", value)
                    value.show()
            for i in range(left_half, right_half):
                field = self.fieldSelection[i]
                if field in self.fields:
                    label, value = self.fields[field]
                    self.right_form.addRow(label + ":", value)
                    value.show()

    def setFrequency(self, frequency):
        self.frequency = RFTools.RFTools.parseFrequency(frequency)
        self.updated.emit(self)

    def setFieldSelection(self, fields):
        self.fieldSelection = fields.copy()
        self.buildForm()

    def setColor(self, color):
        if color.isValid():
            self.color = color
            p = self.btnColorPicker.palette()
            p.setColor(QtGui.QPalette.ButtonText, self.color)
            self.btnColorPicker.setPalette(p)
        if self.coloredText:
            color_string = QtCore.QVariant(color)
            color_string.convert(QtCore.QVariant.String)
            self.group_box.setStyleSheet(
                f"QGroupBox {{ color: {color_string.value()}; "
                f"font-size: {self._size_str()}}};"
            )
        else:
            self.group_box.setStyleSheet(
                f"QGroupBox {{ font-size: {self._size_str()}}};"
            )

    def setColoredText(self, colored_text):
        self.coloredText = colored_text
        self.setColor(self.color)

    def getRow(self):
        return QtWidgets.QLabel(self.name), self.layout

    def findLocation(self, data: List[RFTools.Datapoint]):
        self.location = -1
        self.frequencyInput.nextFrequency = -1
        self.frequencyInput.previousFrequency = -1
        if self.frequency == 0:
            # No frequency set for this marker
            return
        datasize = len(data)
        if datasize == 0:
            # Set the frequency before loading any data
            return

        min_freq = data[0].freq
        max_freq = data[-1].freq
        lower_stepsize = data[1].freq - data[0].freq
        upper_stepsize = data[-1].freq - data[-2].freq

        # We are outside the bounds of the data, so we can't put in a marker
        if (self.frequency + lower_stepsize/2 < min_freq or
                self.frequency - upper_stepsize/2 > max_freq):
            return

        min_distance = max_freq
        for i, item in enumerate(data):
            if abs(item.freq - self.frequency) <= min_distance:
                min_distance = abs(item.freq - self.frequency)
            else:
                # We have now started moving away from the nearest point
                self.location = i-1
                if i < datasize:
                    self.frequencyInput.nextFrequency = item.freq
                if (i-2) >= 0:
                    self.frequencyInput.previousFrequency = data[i-2].freq
                return
        # If we still didn't find a best spot, it was the last value
        self.location = datasize - 1
        self.frequencyInput.previousFrequency = data[-2].freq

    def getGroupBox(self) -> QtWidgets.QGroupBox:
        return self.group_box

    def resetLabels(self):
        self.label['actualfreq'].setText("")
        self.label['impedance'].setText("")
        self.label['admittance'].setText("")
        self.label['parr'].setText("")
        self.label['parlc'].setText("")
        self.label['parl'].setText("")
        self.label['parc'].setText("")
        self.label['serlc'].setText("")
        self.label['serr'].setText("")
        self.label['serl'].setText("")
        self.label['serc'].setText("")
        self.label['vswr'].setText("")
        self.label['returnloss'].setText("")
        self.label['s21gain'].setText("")
        self.label['s11phase'].setText("")
        self.label['s21phase'].setText("")
        self.label['s11groupdelay'].setText("")
        self.label['s21groupdelay'].setText("")
        self.label['s11q'].setText("")

    def updateLabels(self,
                     s11data: List[RFTools.Datapoint],
                     s21data: List[RFTools.Datapoint]):
        if self.location == -1:
            return
        s11 = s11data[self.location]

        imp = s11.impedance()
        cap_str = format_capacitance(
            RFTools.impedance_to_capacitance(imp, s11.freq))
        ind_str = format_inductance(
            RFTools.impedance_to_inductance(imp, s11.freq))

        imp_p = RFTools.serial_to_parallel(imp)
        cap_p_str = format_capacitance(
            RFTools.impedance_to_capacitance(imp_p, s11.freq))
        ind_p_str = format_inductance(
            RFTools.impedance_to_inductance(imp_p, s11.freq))

        if imp.imag < 0:
            x_str = cap_str
        else:
            x_str = ind_str

        if imp_p.imag < 0:
            x_p_str = cap_p_str
        else:
            x_p_str = ind_p_str

        self.label['actualfreq'].setText(format_frequency(s11.freq))

        self.label['impedance'].setText(format_complex_imp(imp))
        self.label['serr'].setText(format_resistance(imp.real))
        self.label['serlc'].setText(x_str)
        self.label['serc'].setText(cap_str)
        self.label['serl'].setText(ind_str)

        self.label['admittance'].setText(format_complex_imp(imp_p))
        self.label['parr'].setText(format_resistance(imp_p.real))
        self.label['parlc'].setText(x_p_str)
        self.label['parc'].setText(cap_p_str)
        self.label['parl'].setText(ind_p_str)

        self.label['vswr'].setText(format_vswr(s11.vswr))
        self.label['s11phase'].setText(format_phase(s11.phase))
        self.label['s11q'].setText(
            format_q_factor(s11.qFactor()))

        self.label['returnloss'].setText(
            format_gain(s11.gain, self.returnloss_is_positive))
        self.label['s11groupdelay'].setText(
            format_group_delay(RFTools.groupDelay(s11data, self.location))
        )

        # skip if no valid s21 data
        if len(s21data) != len(s11data):
            return

        s21 = s21data[self.location]

        self.label['s21phase'].setText(format_phase(s21.phase))
        self.label['s21gain'].setText(format_gain(s21.gain))
        self.label['s21groupdelay'].setText(
            format_group_delay(RFTools.groupDelay(s21data, self.location) / 2)
        )
