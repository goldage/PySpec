#! encoding = utf-8

from PyQt4 import QtGui, QtCore
from PyQt4.QtCore import QObject
import pyqtgraph as pg
from gui.SharedWidgets import *
from api import synthesizer as synapi
from api import lockin as apilc
from api import pci as apipci

def msgcolor(status_code):
    ''' Return message color based on status_code.
        0: safe, green
        1: fatal, red
        2: warning, gold
        else: black
    '''

    if not status_code:
        return '#00A352'
    elif status_code == 1:
        return '#D63333'
    elif status_code == 2:
        return '#FF9933'
    else:
        return '#000000'


class SynCtrl(QtGui.QGroupBox):
    '''
        Synthesizer control panel
    '''

    def __init__(self, parent):
        QtGui.QWidget.__init__(self, parent)

        self.setTitle('Synthesizer Control')
        self.setAlignment(1)    # align left
        self.setCheckable(True)

        ## -- Define synthesizer control elements --
        syn = QtGui.QWidget()
        self.synfreq = QtGui.QLabel('30000')
        self.probfreqFill = QtGui.QLineEdit()
        self.probfreqFill.setText('30000')
        self.bandSelect = QtGui.QComboBox()
        bandList = ['1 (x1): 0-50 GHz',
                    '2 (x2): GHz',
                    '3 (x3): 70-110 GHz',
                    '4 (x3): 110-140 GHz',
                    '5 (x6): 140-220 GHz',
                    '6 (x9): 220-330 GHz',
                    '7 (x12): 325-430 GHz',
                    '8a (x18): 430-700 GHz',
                    '8b (x27): 600-850 GHz',
                    '9 (x27): 700-1000 GHz']
        self.bandSelect.addItems(bandList)
        self.modModeSelect = QtGui.QComboBox()
        self.modModeSelect.addItems(['None', 'AM', 'FM'])

        ## -- Set up synthesizer control layout --
        synLayout = QtGui.QFormLayout()
        synLayout.addRow(QtGui.QLabel('Synthesizer Frequency (MHz)'), self.synfreq)
        synLayout.addRow(QtGui.QLabel('Probing Frequency (MHz)'), self.probfreqFill)
        synLayout.addRow(QtGui.QLabel('VDI Band'), self.bandSelect)
        synLayout.addRow(QtGui.QLabel('Modulation'), self.modModeSelect)
        syn.setLayout(synLayout)

        # Set up modulation sublayout
        self.mod = QtGui.QWidget()
        modLayout = QtGui.QGridLayout()
        self.modFreqFill = QtGui.QLineEdit()
        self.modfreqUnit = QtGui.QComboBox()
        self.modDepthFill = QtGui.QLineEdit()
        self.modDepthUnit = QtGui.QLabel('')
        self.modToggle = QtGui.QCheckBox()
        self.modToggle.setCheckState(False)

        modLayout.addWidget(QtGui.QLabel('Mod Frequency'), 0, 0)
        modLayout.addWidget(self.modFreqFill, 0, 1)
        modLayout.addWidget(QtGui.QLabel('kHz'), 0, 2)
        modLayout.addWidget(QtGui.QLabel('Mod Depth'), 1, 0)
        modLayout.addWidget(self.modDepthFill, 1, 1)
        modLayout.addWidget(self.modDepthUnit, 1, 2)
        modLayout.addWidget(QtGui.QLabel('Mod On'), 2, 0, 1, 2)
        modLayout.addWidget(self.modToggle)
        self.mod.setLayout(modLayout)
        self.mod.hide()

        ## -- Define synthesizer power switch
        self.synPowerToggle = QtGui.QCheckBox()
        self.synPowerToggle.setCheckState(False)
        synPowerManualInput = QtGui.QPushButton('Set Power')

        self.synCurrentPower = QtGui.QLabel()
        self.synCurrentPower.setText('{:d} dbm'.format(synapi.read_syn_power()))
        synPowerLayout = QtGui.QHBoxLayout()
        synPowerLayout.addWidget(QtGui.QLabel('Synthesizer On'))
        synPowerLayout.addWidget(self.synPowerToggle)
        synPowerLayout.addWidget(QtGui.QLabel('Current Power'))
        synPowerLayout.addWidget(self.synCurrentPower)
        synPowerLayout.addWidget(synPowerManualInput)
        synPowerCtrl = QtGui.QWidget()
        synPowerCtrl.setLayout(synPowerLayout)

        ## -- Set up main layout
        mainLayout = QtGui.QVBoxLayout()
        mainLayout.addWidget(synPowerCtrl)
        mainLayout.addWidget(syn)
        mainLayout.addWidget(self.mod)
        self.setLayout(mainLayout)

        # Trigger frequency update and communication
        QObject.connect(self.probfreqFill, QtCore.SIGNAL("textChanged(const QString)"), self.freqComm)
        QObject.connect(self.bandSelect, QtCore.SIGNAL("currentIndexChanged(int)"), self.freqComm)

        # Trigger modulation status update and communication
        QObject.connect(self.modModeSelect, QtCore.SIGNAL("currentIndexChanged(int)"), self.modModeComm)
        QObject.connect(self.modFreqFill, QtCore.SIGNAL("textChanged(const QString)"), self.modParComm)
        QObject.connect(self.modDepthFill, QtCore.SIGNAL("textChanged(const QString)"), self.modParComm)
        QObject.connect(self.modToggle, QtCore.SIGNAL("stateChanged(int)"), self.modToggleComm)

        # Trigger synthesizer power toggle and communication
        QObject.connect(synPowerManualInput, QtCore.SIGNAL("clicked()"), self.synPowerComm)
        QObject.connect(self.synPowerToggle, QtCore.SIGNAL("stateChanged(int)"), self.synPowerDialog)

    def freqComm(self):
        '''
            Communicate with the synthesizer and update frequency setting.
        '''

        # return communication status
        syn_stat = synapi.set_syn_freq(self.probfreqFill.text(),
                                       self.bandSelect.currentIndex())
        # update synthesizer frequency
        self.synfreq.setText('{:.12f}'.format(synapi.read_syn_freq()))
        # set sheet border color by syn_stat
        self.probfreqFill.setStyleSheet('border: 1px solid {:s}'.format(msgcolor(syn_stat)))

    def synPowerComm(self):
        '''
            Communicate with the synthesizer and set up RF power
            (automatically turn RF on)
        '''

        # Get current syn power
        current_power = synapi.read_syn_power()
        self.synCurrentPower.setText('{:d} dbm'.format(current_power))
        # Grab manual input power
        set_power, stat = QtGui.QInputDialog.getInt(self, 'Synthesizer RF Power',
                                'Manual Input (-20 to 0)', current_power, -20, 0, 1)
        stat = synapi.set_syn_power(set_power)
        if not stat:    # hopefully no error occurs
            self.synPowerToggle.setCheckState(True)
            # update power reading
            self.synCurrentPower.setText('{:d} dbm'.format(synapi.read_syn_power()))
        else:
            QtGui.QMessageBox.warning(self, 'Dangerous Input!', 'Input power exceed safety range!', QtGui.QMessageBox.Ok)

    def synPowerDialog(self, toggle_stat):
        '''
            Pop-up warning window when user trigger the synthesizer toggle
        '''

        stat = synapi.syn_power_toggle(toggle_stat)
        self.synPowerToggle.setCheckState(stat)
        self.synCurrentPower.setText('{:d} dbm'.format(synapi.read_syn_power()))

    def modModeComm(self):
        '''
            Communicate with the synthesizer and update modulation mode.
        '''

        mod_index = self.modModeSelect.currentIndex()

        if mod_index:
            self.mod.show()     # Modulation selected. Show modulation widget
        else:
            self.mod.hide()     # No modulation. Hide modulation widget

        comm_stat = synapi.set_mod_mode(mod_index)

        if mod_index == 1:
            self.modDepthUnit.setText('%')
        elif mod_index == 2:
            self.modDepthUnit.setText('kHz')

        # update parameters
        freq, depth = synapi.read_mod_par()
        self.modFreqFill.setText(freq)
        self.modDepthFill.setText(depth)

    def modParComm(self):
        '''
            Communicate with the synthesizer and update modulation parameters
        '''

        mod_index = self.modModeSelect.currentIndex()

        if mod_index == 1:      # AM
            freq_stat, depth_stat = synapi.set_am(self.modFreqFill.text(),
                                                  self.modDepthFill.text(),
                                                  self.modToggle.isChecked())
        elif mod_index == 2:    # FM
            freq_stat, depth_stat = synapi.set_fm(self.modFreqFill.text(),
                                                  self.modDepthFill.text(),
                                                  self.modToggle.isChecked())

        # set sheet border color by status
        self.modFreqFill.setStyleSheet('border: 1px solid {:s}'.format(msgcolor(freq_stat)))
        self.modDepthFill.setStyleSheet('border: 1px solid {:s}'.format(msgcolor(depth_stat)))

    def modToggleComm(self):
        '''
            Communicate with the synthesizer and update modulation on/off toggle
        '''

        synapi.mod_toggle(self.modToggle.isChecked())


class LockinCtrl(QtGui.QGroupBox):

    def __init__(self, parent):
        QtGui.QWidget.__init__(self, parent)

        self.setTitle('Lockin Control')
        self.setAlignment(1)        # align left
        self.setCheckable(True)

        ## -- Define layout elements --
        harmSelect = QtGui.QComboBox()
        harmSelect.addItems(['1', '2', '3', '4'])
        self.phaseFill = QtGui.QLineEdit()
        sensSelect = QtGui.QComboBox()
        sensList = ['1 V', '500 mV', '200 mV', '100 mV', '50 mV', '20 mV',
                    '10 mV', '1 mV', '500 uV', '200 uV', '100 uV', '50 uV',
                    '20 uV', '10 uV', '5 uV', '2 uV', '1 uV'
                    ]
        sensSelect.addItems(sensList)
        tcSelect = QtGui.QComboBox()
        tcList = ['30 us', '100 us', '300 us', '1 ms', '3 ms', '10 ms',
                  '30 ms', '100 ms', '300 ms', '1 s', '3 s', '10 s'
                  ]
        tcSelect.addItems(tcList)
        coupleSelect = QtGui.QComboBox()
        coupleSelect.addItems(['AC', 'DC'])
        reserveSelect = QtGui.QComboBox()
        reserveSelect.addItems(['High Reserve', 'Normal', 'Low Noise'])

        ## -- Set up main layout --
        mainLayout = QtGui.QFormLayout()
        mainLayout.addRow(QtGui.QLabel('Harmonics'), harmSelect)
        mainLayout.addRow(QtGui.QLabel('Phase'), self.phaseFill)
        mainLayout.addRow(QtGui.QLabel('Sensitivity'), sensSelect)
        mainLayout.addRow(QtGui.QLabel('Time Constant'), tcSelect)
        mainLayout.addRow(QtGui.QLabel('Couple'), coupleSelect)
        mainLayout.addRow(QtGui.QLabel('Reserve'), reserveSelect)
        self.setLayout(mainLayout)

        ## -- Trigger setting status and communication
        QObject.connect(self.phaseFill, QtCore.SIGNAL("textChanged(const QString)"), self.phaseComm)
        QObject.connect(harmSelect, QtCore.SIGNAL("currentIndexChanged(const QString)"), self.harmComm)
        QObject.connect(tcSelect, QtCore.SIGNAL("currentIndexChanged(int)"), self.tcComm)
        QObject.connect(sensSelect, QtCore.SIGNAL("currentIndexChanged(int)"), self.sensComm)
        QObject.connect(coupleSelect, QtCore.SIGNAL("currentIndexChanged(const QString)"), self.coupleComm)
        QObject.connect(reserveSelect, QtCore.SIGNAL("currentIndexChanged(const QString)"), self.reserveComm)

    def phaseComm(self, phase_text):
        '''
            Communicate with the lockin and set phase
        '''

        stat = apilc.set_phase(phase_text)
        self.phaseFill.setStyleSheet('border: 1px solid {:s}'.format(msgcolor(stat)))

    def harmComm(self, harm_text):
        '''
            Communicate with the lockin and set Harmonics
        '''

        stat = apilc.set_harm(harm_text)

        if stat:
            QtGui.QMessageBox.warning(self, 'Out of Range!', 'Input harmonics exceed legal range!', QtGui.QMessageBox.Ok)
        else:
            pass

    def sensComm(self, sens_index):
        '''
            Communicate with the lockin and set sensitivity
        '''

        stat = apilc.set_sensitivity(sens_index)

        if stat:
            QtGui.QMessageBox.warning(self, 'Out of Range!', 'Input sensitivity exceed legal range!', QtGui.QMessageBox.Ok)
        else:
            pass

    def tcComm(self, tc_index):
        '''
            Communicate with the lockin and set sensitivity
        '''

        stat = apilc.set_tc(tc_index)

        if stat:
            QtGui.QMessageBox.warning(self, 'Out of Range!', 'Input time constant exceed legal range!', QtGui.QMessageBox.Ok)
        else:
            pass

    def coupleComm(self, couple_text):
        '''
            Communicate with the lockin and set couple mode
        '''

        stat = apilc.set_couple(couple_text)

        if stat:
            QtGui.QMessageBox.critical(self, 'Invalid Input!', 'Input couple unrecognized!', QtGui.QMessageBox.Ok)
        else:
            pass

    def reserveComm(self, reserve_text):
        '''
            Communicate with the lockin and set reserve
        '''

        stat = apilc.set_reserve(reserve_text)

        if stat:
            QtGui.QMessageBox.critical(self, 'Invalid Input!', 'Input reserve mode unrecognized!', QtGui.QMessageBox.Ok)
        else:
            pass


class ScopeCtrl(QtGui.QGroupBox):

    def __init__(self, parent):
        QtGui.QWidget.__init__(self, parent)

        self.setTitle('Oscilloscope Control')
        self.setAlignment(1)
        self.setCheckable(True)

        ## -- Define layout elements --
        self.srateFill = QtGui.QLineEdit()
        self.slenFill = QtGui.QLineEdit()
        sensSelect = QtGui.QComboBox()
        sensList = ['20 V', '5 V', '1 V', '0.5 V', '0.2 V']
        sensSelect.addItems(sensList)
        self.avgFill = QtGui.QLineEdit()

        ## -- Set up main layout --
        mainLayout = QtGui.QFormLayout()
        mainLayout.addRow(QtGui.QLabel('Sample Rate (MHz)'), self.srateFill)
        mainLayout.addRow(QtGui.QLabel('Sample Length'), self.slenFill)
        mainLayout.addRow(QtGui.QLabel('Sensitivity'), sensSelect)
        mainLayout.addRow(QtGui.QLabel('Oscilloscope Average'), self.avgFill)
        self.setLayout(mainLayout)

        ## -- Trigger setting status and communication
        QObject.connect(self.srateFill, QtCore.SIGNAL("textChanged(const QString)"), self.rateComm)
        QObject.connect(self.slenFill, QtCore.SIGNAL("textChanged(const QString)"), self.lenComm)
        QObject.connect(sensSelect, QtCore.SIGNAL("currentIndexChanged(int)"), self.sensComm)
        QObject.connect(self.avgFill, QtCore.SIGNAL("textChanged(const QString)"), self.avgComm)


    def rateComm(self, rate_text):

        stat = apipci.set_sampling_rate(rate_text)
        self.srateFill.setStyleSheet('border: 1px solid {:s}'.format(msgcolor(stat)))

    def lenComm(self, len_text):

        stat = apipci.set_sampling_len(len_text)
        self.slenFill.setStyleSheet('border: 1px solid {:s}'.format(msgcolor(stat)))

    def sensComm(self, sens_index):

        stat = apipci.set_sensitivity(sens_index)

    def avgComm(self, avg_text):

        stat = apipci.set_osc_avg(avg_text)
        self.avgFill.setStyleSheet('border: 1px solid {:s}'.format(msgcolor(stat)))



class CavityCtrl(QtGui.QGroupBox):

    def __init__(self, parent):
        QtGui.QWidget.__init__(self, parent)

        self.setTitle('Cavity Control')
        self.setAlignment(1)
        self.setCheckable(True)

        mainLayout = QtGui.QHBoxLayout()
        mainLayout.addWidget(QtGui.QPushButton('Tune Cavity'))
        self.setLayout(mainLayout)


class ScopeMonitor(pg.PlotWidget):

    def __init__(self, parent):
        pg.PlotWidget.__init__(self, parent, title='Oscilloscope Monitor')

        self.getPlotItem()



class LockinMonitor(pg.PlotWidget):

    def __init__(self, parent):
        pg.PlotWidget.__init__(self, parent, title='Lockin Monitor')

        self.getPlotItem()


class SpectrumMonitor(pg.PlotWidget):

    def __init__(self, parent):
        pg.PlotWidget.__init__(self, parent, title='Spectrum Plotter')

        self.getPlotItem()