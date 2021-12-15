# library for ApRES HTTP control
import apreshttp
from apreshttp.base import NotFoundException
# library for processing ApRES data
import apyres
import datetime
import matplotlib.pyplot as plt 
from matplotlib.figure import Figure
from matplotlib.backends.backend_tkagg import (FigureCanvasTkAgg, NavigationToolbar2Tk)
import numpy as np
import os
import pathlib
import tkinter as tk
import tkinter.filedialog as tkfiledlg
import tkinter.messagebox as tkmsg
import tkinter.simpledialog as tkdlg
from tkinter import ttk

class ApplicationReference:
    """
    Interface class to store reference to top level application instance.
    """

    def __init__(self, app=None): 
        """
        Constructor for ApplicationReference

        :param app: Instance of top level application, defaults to None
        :type app: apressurvey.ApRESSurveyApplication, optional
        """
        self.application = app
    
    def setApplication(self, ref):
        """
        Sets reference to top-level application

        :param ref: New top-level application reference
        :type ref: apressurvey.ApRESSurveyApplication
        """
        self.application = ref

    def getApplication(self):
        """
        Returns reference to top-level application

        :return: Reference to top-level application, if set.
        :rtype: apressurvey.ApRESSurveyApplication or None
        """
        return self.application

    def getAPI(self):
        """
        Returns reference to API instance of top-level application

        Helpful shorthand instead of calling application.api

        :return: Reference to API for top-level application, if set.
        :rtype: apreshttp.base.API or None
        """
        return self.application.api

class DatetimeVar(tk.StringVar):
    """
    Originally a class to replace StringVar for storing datetime values
    in string fields
    
    Also contains reference the datetime format used throughout the application.
    """

    DATETIME_FORMAT = "%Y-%m-%d %H:%M:%S"

    def __init__(self, value=None, *args, **kwargs):
        if "value" != None:
            if isinstance(kwargs, datetime.datetime):
                self.datetime = kwargs["value"]
                kwargs["value"] = kwargs["value"].strftime(self.DATETIME_FORMAT)
            elif isinstance(kwargs, str):
                self.datetime = datetime.datetime.strptime(kwargs["value"], self.DATETIME_FORMAT)
            else:
                ValueError("value should be set to a datetime object or string.")
        else:
            self.datetime = datetime.datetime.now()
            kwargs["value"] = self.datetime.strftime(self.DATETIME_FORMAT)

        super().__init__(*args, **kwargs)

    def get(self):
        """Returns datetime value as string

        :return: current datetime as string
        :rtype: str
        """
        if self.datetime == None:
            return datetime.datetime.now().strftime(self.DATETIME_FORMAT)
        else:
            return self.datetime.strftime(self.DATETIME_FORMAT)

    def set(self, value):
        """Update value from string or datetime object

        :param value: datetime to update
        :type value: str, datetime
        :raises ValueError: value argument is not str or datetime.datetime
        """
        if isinstance(value, datetime.datetime):
            self.datetime = datetime
            super().set(value.strftime(self.DATETIME_FORMAT))
        elif isinstance(value, str):
            self.datetime = datetime.datetime.strptime(value, self.DATETIME_FORMAT)
            super().set(value)
        else:
            raise ValueError("Input to set should be a datetime object.")

class StatusFrame(tk.LabelFrame, ApplicationReference):
    """
    Subclass of LabelFrame to display ApRES status

    LabelFrame displays various housekeeping values of the ApRES, including
    battery voltage, VAB time and - if available - GPS time, latitude and
    longitude.

    It also displays a rolling graph of battery voltage to monitor change
    over time for use in Survey mode.  Constants BATTERY_LOG_SIZE and 
    BATTERY_LOG_INTERVAL adjust graph behaviour.

    Inherits tk.LabelFrame and ApplicationReference.
    """

    BATTERY_LOG_SIZE = 256
    BATTERY_LOG_INTERVAL = 5000
    
    def __init__(self, parent, app=None, *args, **kwargs):
        """Creates instance of the StatusFrame class.

        :param parent: reference to containing frame
        :type parent: tk.Frame or tk.Tk
        :param app: reference to top-level documentation, defaults to None
        :type app: apresurvey.ApRESSurveyApplication, optional
        """
        
        ApplicationReference.__init__(self, app=app)
        tk.LabelFrame.__init__(self, parent, text="Status", *args, **kwargs)

        # Create test treeview component
        self.statusTree = ttk.Treeview(self, columns=('field','value'), show='headings')
        self.statusTree.heading('field', text='Field')
        self.statusTree.heading('value', text='Value')

        # Create empty array to store battery values
        self.batteryLog = np.zeros(self.BATTERY_LOG_SIZE)

        # Get current datetime for default status method
        now = datetime.datetime.now().strftime(DatetimeVar.DATETIME_FORMAT)

        # Create an empty status method
        if "status" in kwargs and kwargs["status"] != None:
            self.status = kwargs["status"]
        else:
            self.status = apreshttp.System.Housekeeping.Status(
                0,      # Battery voltage
                "",     # Time GPS
                now,    # Time VAB
                0,      # Latitude
                0,      # Longitude
            )

        # Assign battery figure and setup
        self.batteryFigure = Figure(figsize=(4,1))
        self.batteryFigureAx = self.batteryFigure.add_subplot(111)
        self.batteryFigureCanvas = FigureCanvasTkAgg(self.batteryFigure, master=self)
        self.batteryFigureCanvas.draw()
        self.batteryFigureCanvas.get_tk_widget().grid(padx=8, pady=8, row=3, column=0, sticky=(tk.E + tk.N + tk.W + tk.S))
        self.batteryFigure.patch.set_facecolor("#F0F0F0")

        # Create status label
        self.statusLabel = tk.StringVar(value="Not updated.")
        statusUpdateLabel = ttk.Label(self, textvariable=self.statusLabel, wraplength=300)

        # Create tree to store status information
        self.statusTree.grid(padx=8, pady=8, row=0, column=0, sticky=(tk.E + tk.N + tk.S + tk.W))
        statusUpdateLabel.grid(row=2, column=0, sticky=(tk.E + tk.S + tk.W))
        
        self.rowconfigure(0, weight=1)
        self.rowconfigure(1, weight=0)
        self.columnconfigure(0, weight=1)

        # Start status update
        self.update()
        # Start battery log update
        self.batteryLogUpdate()

    def batteryLogUpdate(self):
        """
        Replot battery log graph using most recent data.
        """

        print("Doing battery log update {:f}".format(self.status.batteryVoltage))
        # Shift array back 1
        self.batteryLog = np.roll(self.batteryLog, -1)
        self.batteryLog[-1] = self.status.batteryVoltage
        
        # Clear axis and plot
        self.batteryFigureAx.clear()
        self.batteryFigureAx.plot(
            np.linspace(
                -self.BATTERY_LOG_INTERVAL*self.BATTERY_LOG_SIZE/1e3,
                0,
                self.BATTERY_LOG_SIZE
            ),
            self.batteryLog
        )
        self.batteryFigureAx.set_ylim(0, 15)
        self.batteryFigureAx.set_ylabel('Voltage (V)')
        self.batteryFigureCanvas.draw()
        # Repeat again after logging interval
        self.after(self.BATTERY_LOG_INTERVAL, self.batteryLogUpdate)


    def update(self):
        """
        Update tree-view of housekeeping parameters with latest data
        """
        
        # Delete any existing children
        for child in self.statusTree.get_children():
            self.statusTree.delete(child)

        timeVAB = "[Not available]"
        if self.status.timeVAB != None:
            timeVAB =  self.status.timeVAB.strftime(DatetimeVar.DATETIME_FORMAT)
        
        timeGPS = "[Not available]"
        if self.status.timeGPS != None:
            timeGPS = self.status.timeGPS.strftime(DatetimeVar.DATETIME_FORMAT)
        
        self.statusTree.insert("", tk.END, values=("Time VAB", timeVAB))
        self.statusTree.insert("", tk.END, values=("Time GPS", timeGPS))
        self.statusTree.insert("", tk.END, values=("Battery Voltage", self.status.batteryVoltage))
        self.statusTree.insert("", tk.END, values=("Latitude", self.status.latitude))
        self.statusTree.insert("", tk.END, values=("Longitude", self.status.longitude))

        self.statusLabel.set("Not connected.")

class ConfigFrame(tk.LabelFrame, ApplicationReference):
    """Stores buttons for update, download and reset of config values
    """

    def __init__(self, parent, app=None, *args, **kwargs):
        """Create instance of ConfigFrame

        :param parent: parent tkinter.Frame
        :type parent: tkinter.Frame
        :param app: reference to top level application, defaults to None
        :type app: ApRESSurveyApplication, optional
        """

        ApplicationReference.__init__(self, app=app)
        tk.LabelFrame.__init__(self, parent, text="Config", *args, **kwargs)

        # Create buttons
        downloadConfigBttn = ttk.Button(self, text="Download...", command=self.downloadConfig)
        uploadConfigBttn = ttk.Button(self, text="Upload...", command=self.uploadConfig)
        resetBttn = ttk.Button(self, text="Reset", command=self.reset)
        # Assign to grid
        downloadConfigBttn.grid(padx=8, pady=8, ipadx=4, ipady=4, column=0, row=0, sticky=(tk.E + tk.N + tk.S + tk.W))
        uploadConfigBttn.grid(padx=8, pady=8, ipadx=4, ipady=4, column=1, row=0, sticky=(tk.E + tk.N + tk.S + tk.W))
        resetBttn.grid(padx=8, pady=8, ipadx=4, ipady=4, column=2, row=0, sticky=(tk.E + tk.N + tk.S + tk.W))
        # Configure grid
        self.columnconfigure(0, weight=1)
        self.columnconfigure(1, weight=1)
        self.columnconfigure(2, weight=1)

    def downloadConfig(self, *args):
        """Download configuration file to local disk
        """
        
        if self.getAPI() != None:
            filename = tkfiledlg.asksaveasfilename(
                initialfile="config.ini", 
                title="Save ApRES config.ini", 
                defaultextension="ini", #
                filetypes=[
                    ("Config files (*.ini)", ".ini"), 
                    ("Any file type (.*)", ".*")
                ]
            )
            if len(filename) > 0:

                overwrite = False
                if os.path.exists(filename):
                    overwrite = tkmsg.askyesno(title="File Exists", message="File already exists.  Overwrite?")

                try:
                    self.getAPI().system.housekeeping.config.download(filename, overwrite)
                    self.application.systemFrame.setStatusLabel(
                        "Successfully downloaded config to {:s}.".format(filename)
                    )
                except Exception as e:
                    tkmsg.showerror(title=type(e).__name__, message=str(e))

            else:
                tkmsg.showwarning(title="Empty Filename", message="No filename provided, not downloading config.ini.")
        else:
            self.application.systemFrame.setStatusLabel(
                "Error connecting to radar."
            )
            self.application.systemFrame.configure(bg="red")


    def uploadConfig(self, *args):
        if self.getAPI() != None:
            filename = tkfiledlg.askopenfilename(
                initialfile="config.ini", 
                title="Save ApRES config.ini", 
                defaultextension="ini", #
                filetypes=[
                    ("Config files (*.ini)", ".ini")
                ]
            )
            if len(filename) > 0:
                try:
                    self.getAPI().system.housekeeping.config.upload(filename)
                    self.application.systemFrame.setStatusLabel(
                        "Successfully upload config to radar from {:s}.".format(filename)
                    )
                    tkmsg.showinfo(title="Uploaded Config.ini", message="You must reset the ApRES for the new config.ini to be applied.")
                except Exception as e:
                    tkmsg.showerror(title=type(e).__name__, message=str(e))

            else:
                tkmsg.showwarning(title="Empty Filename", message="No filename provided, not uploading config.ini.")
        else:
            self.application.systemFrame.setStatusLabel(
                "Error connecting to radar."
            )
            self.application.systemFrame.configure(bg="red")

    def reset(self, *args):
        api = self.getAPI()
        if api != None:
            try:
                resetMessage = api.system.reset()
                if resetMessage != None:
                    self.application.systemFrame.setStatusLabel(
                        "Attempting reset at {:s} [{:s}]".format(
                            resetMessage.time.strftime(DatetimeVar.DATETIME_FORMAT),
                            resetMessage.message
                        )
                    )
            except Exception as e: 
                tkmsg.showerror(title=type(e).__name__, message=str(e))
        else:
            self.application.systemFrame.setStatusLabel(
                "Error connecting to radar."
            )
            self.application.systemFrame.configure(bg="red")

class BurstConfigFrame(tk.LabelFrame, ApplicationReference):

    def __init__(self, parent, app=None, *args, **kwargs):
        ApplicationReference.__init__(self, app=app)
        tk.LabelFrame.__init__(self, parent, text="Radar Config", *args, **kwargs)

        self.averageVariableFrame = self.ConfigVariableFrame(
            self,
            row=0,
            text="# Averages",
            varClass=tk.IntVar,
            varDefault=1,
            entryClass=ttk.Spinbox,
            entryClassArgs={
                'width' : 10,
                'from_' : 1,
                'to'    : 100
            }
        )

        self.subburstVariableFrame = self.ConfigVariableFrame(
            self,
            row=1,
            text="# Subbursts",
            varClass=tk.IntVar,
            varDefault=1,
            entryClass=ttk.Spinbox,
            entryClassArgs={
                'width' : 10,
                'from_' : 1,
                'to'    : 100
            }
        )

        self.attenuatorsVariableFrame = self.ConfigVariableFrame(
            self,
            row=2,
            text="# Attenuators",
            varClass=tk.IntVar,
            varDefault=1,
            entryClass=ttk.Spinbox,
            entryClassArgs={
                'width' : 10,
                'command' : self.updateAttenuators,
                'from_' : 1,
                'to'    : 4,
                'wrap'  : True
            }
        )
    
        self.rfAttnVariableFrame = self.ConfigVariableFrame(
            self,
            row=3,
            text="RF Attenuation",
            N=4,
            varClass=tk.DoubleVar,
            varDefault=30,
            entryClass=ttk.Spinbox,
            entryClassArgs={
                'width' : 5,
                'from_' : 0,
                'to'    : 31.75
            }
        )

        self.afGainVariableFrame = self.ConfigVariableFrame(
            self,
            row=4,
            text="AF Gain",
            N=4,
            varClass=tk.IntVar,
            varDefault=-14,
            entryClass=ttk.Spinbox,
            entryClassArgs={
                'values' : (-14, -4, 6),
                'width' : 5
            }
        )

        self.config = None

        self.updateAttenuators()

        self.txAntennaFrame = self.AntennaCheckbuttonFrame(self, label="TX Antenna")
        self.txAntennaFrame.grid(column=0, row=5, columnspan=5, sticky=tk.W)
        self.txAntennaFrame.setValues([1,0,0,0,0,0,0,0])

        self.rxAntennaFrame = self.AntennaCheckbuttonFrame(self, label="RX Antenna")
        self.rxAntennaFrame.grid(column=0, row=6, columnspan=5, sticky=tk.W)
        self.rxAntennaFrame.setValues([1,0,0,0,0,0,0,0])

        ttk.Separator(self, orient="horizontal").grid(column=0, row=7, columnspan=3, padx=8, pady=8, sticky=(tk.E + tk.W))

        self.refreshButton = ttk.Button(self, text="Refresh", command=self.refreshConfig)
        self.refreshButton.grid(column=0, row=8, columnspan=3, padx=8, ipadx=8, ipady=8, sticky=(tk.N + tk.E + tk.S + tk.W))

        self.updateButton = ttk.Button(self, text="Update", command=self.updateConfig)
        self.updateButton.grid(column=0, row=9, columnspan=3, padx=8, pady=8, ipadx=8, ipady=8, sticky=(tk.N + tk.E + tk.S + tk.W))

        self.columnconfigure(0,weight=0)
        self.columnconfigure(1,weight=0)
        self.columnconfigure(2,weight=1)

    def updateAttenuators(self, *args):

        self.rfAttnVariableFrame.updateVisible(int(self.attenuatorsVariableFrame.getNthValue(0)))
        self.afGainVariableFrame.updateVisible(int(self.attenuatorsVariableFrame.getNthValue(0)))

        if self.config != None:
            for k in range(self.config.nAttenuators):
                self.rfAttnVariableFrame.setNthValue(k, self.config.rfAttn[k])
                self.afGainVariableFrame.setNthValue(k, self.config.afGain[k])

    def updateConfig(self):
        
        if self.getAPI() == None:
            tkmsg.showwarning(title="Not connected.", message="Config not updated.")
        else:
            try:

                nAttens = self.attenuatorsVariableFrame.getNthValue(0)

                self.config = self.getAPI().radar.config.set(
                    nAtts=nAttens,
                    nAverages=self.averageVariableFrame.getNthValue(0),
                    nBursts=self.subburstVariableFrame.getNthValue(0),
                    rfAttnSet=[
                        self.rfAttnVariableFrame.getNthValue(n) for n in range(nAttens)
                    ],
                    afGainSet=[
                        self.afGainVariableFrame.getNthValue(n) for n in range(nAttens)
                    ],
                    txAnt=self.txAntennaFrame.getValues(),
                    rxAnt=self.rxAntennaFrame.getValues()
                )

            except Exception as e:
                self.application.systemFrame.setStatusLabel("Error updating burst configuration from radar.")
                tkmsg.showerror(title=type(e).__name__, message=str(e))
    
            self.refreshConfig()

    def refreshConfig(self):

        if self.getAPI() == None:
            tkmsg.showwarning(title="Not connected.", message="Config not refreshed.")
            self.getApplication().systemFrame.configure(bg="red")
        else:
            try:

                self.config = self.getAPI().radar.config.get()

                # self.averageVariableFrame.status.set("[{:d}]".format(self.config.nAverages))
                self.averageVariableFrame.setNthValue(0, self.config.nAverages)

                # self.subburstVariableFrame.status.set("[{:d}]".format(self.config.nSubBursts))
                self.subburstVariableFrame.setNthValue(0, self.config.nSubBursts)

                # self.attenuatorsVariableFrame.status.set("[{:d}]".format(self.config.nAttenuators))
                self.attenuatorsVariableFrame.setNthValue(0, self.config.nAttenuators)

                # rfStr = "".join([str(rf)+"," for rf in self.config.rfAttn])
                # self.rfAttnVariableFrame.status.set("[{:s}]".format(rfStr[:-1]))

                # afStr = "".join([str(af)+"," for af in self.config.afGain])
                # self.afGainVariableFrame.status.set("[{:s}]".format(afStr[:-1]))

                self.txAntennaFrame.setValues(self.config.txAntenna)
                self.rxAntennaFrame.setValues(self.config.rxAntenna)

                self.updateAttenuators()
                
            except Exception as e:
                self.application.systemFrame.setStatusLabel("Error retrieving burst configuration from radar.")
                tkmsg.showerror(title=type(e).__name__, message=str(e))
    
    class ConfigVariableFrame:

        def __init__(self, parent, row=0, text="Variable", N=1, varDefault = None, varClass=tk.StringVar, entryClass=ttk.Entry, entryClassArgs={}, *args, **kwargs):
    
            self.N = N

            self.label = ttk.Label(parent, text=text)
            self.label.grid(row=row, column=0, padx=8, pady=4, sticky=tk.W)
            
            # self.status = tk.StringVar()
            # self.status.set("[N/A]")
            # self.statusLabel = ttk.Label(parent, textvariable=self.status)
            # self.statusLabel.grid(row=row, padx=8, pady=4, column=1, sticky=tk.W)

            self.entryFrame = ttk.Frame(parent)
            self.entryFrame.grid(row=row, column=1, padx=8, pady=4, sticky=(tk.W+tk.E))
            
            self.entry = []
            self.values = []
            for k in range(N):
                print("adding {:d} element".format(k))
                cValue = varClass()
                cValue.set(varDefault)
                cElement = entryClass(self.entryFrame, textvariable=cValue, **entryClassArgs)
                self.entry.append(cElement)
                self.values.append(cValue)

            self.updateVisible(N)
                
        def updateVisible(self, N):

            print("Updating visible with {:d}".format(N))
            # Hide all elements
            for k in range(self.N):
                self.entry[k].grid_remove()

            if N > self.N:
                N = self.N
            
            if N < 1:
                N = 1

            for k in range(N):
                print("Showing {:d}th element".format(k))
                self.entry[k].grid(row=0, column=k, sticky=(tk.E + tk.W))

        def getNthValue(self, n):
            return self.values[n].get()

        def setNthValue(self, n, val):
            self.values[n].set(val)

    class AntennaCheckbuttonFrame(tk.Frame):

        def __init__(self, parent, label="Antenna", N=8, *args, **kwargs):
            tk.Frame.__init__(self, parent, *args, **kwargs)

            self.N = N

            label = tk.Label(self, text=label)
            label.grid(row=0, column=0, padx=8, pady=8, sticky=(tk.W + tk.N + tk.S))

            self.checkboxes = []
            self.checkbox_values = []

            for k in range(N):
                chkbx_var = tk.IntVar()
                checkbox = ttk.Checkbutton(self, variable=chkbx_var, command=self.checkAtLeastOne)
                chkbx_var.set(0)
                checkbox.grid(row=0, column=k+1)
                self.checkboxes.append(checkbox)
                self.checkbox_values.append(chkbx_var)

        def setValues(self, values):
            if len(values) != self.N:
                raise ValueError("values must be an array of length {:d}".format(self.N))
            else:
                for k in range(self.N):
                    self.checkbox_values[k].set(values[k])

        def getValues(self):
            values = []
            for chkbox_val in self.checkbox_values:
                values.append(chkbox_val.get())
            return tuple(values)

        def checkAtLeastOne(self):
            if sum([chkbox_val.get() for chkbox_val in self.checkbox_values]) == 0:
                self.checkbox_values[0].set(1)

    # class MultipleFieldInput(tk.Frame):
        
    #     def __init__(self, parent, text="Label", entryClass=ttk.Entry, N=1, entryKWArgs={}, *args, **kwargs):#
    #         tk.Frame.__init__(self, parent, *args, **kwargs)

    #         self.label = ttk.Label(self, text=text)
    #         self.label.grid(column=0, row=0, padx=8, pady=8, sticky=(tk.W))

    #         self.entryElements = []
    #         for k in range(N):
    #             cElement = entryClass(self, **entryKWArgs)
    #             cElement.grid(column=k+1, row=0, padx=8, pady=8, sticky=tk.E)
    #             self.entryElements.append(cElement)

    #         # self.columnconfigure(0, weight=1)
    #         # self.columnconfigure(1, weight=1)


        
class ApRESSystemFrame(tk.Frame, ApplicationReference):

    def __init__(self, parent, app=None, *args, **kwargs):
        ApplicationReference.__init__(self, app=app)
        tk.Frame.__init__(self, parent, *args, **kwargs)

        self.radarAddress = tk.StringVar()
        radarAddressCombo = ttk.Combobox(
            self,
            textvariable=self.radarAddress, 
            values=('http://radar.localnet/','http://192.168.1.1')
        )
        self.radarAddress.set("http://localhost:8000/")

        self.radarConnectBttn = ttk.Button(self, text="Connect", command=self.connectToRadar)

        radarAddressCombo.grid(padx=8, pady=8, row=0, column=0, sticky=(tk.E + tk.N + tk.W + tk.S))
        self.radarConnectBttn.grid(padx=8, pady=8, ipadx=4, ipady=4, row=0, column=1, sticky=tk.W)

        self.configFrame = ConfigFrame(self, app=app)
        self.configFrame.grid(padx=8, pady=8, row=1, column=0, columnspan=2, sticky=(tk.N + tk.E + tk.S + tk.W))

        self.radarConfigFrame = BurstConfigFrame(self, app=app)
        self.radarConfigFrame.grid(padx=8, pady=8, row=2, column=0, columnspan=2, sticky=(tk.N + tk.E + tk.S + tk.W))

        self.statusFrame = StatusFrame(self, app=app)
        self.statusFrame.grid(padx=8, pady=8, row=3, column=0, columnspan=2, sticky=(tk.N + tk.E + tk.S + tk.W))

        self.columnconfigure(0,weight=3)
        self.columnconfigure(1,weight=0)
        self.rowconfigure(0,weight=0)
        self.rowconfigure(1,weight=0)
        self.rowconfigure(2,weight=0)
        self.rowconfigure(3,weight=1)

    def connectToRadar(self, *args):
        try:
            self.application.api = apreshttp.API(self.radarAddress.get())
            self.application.api.setKey("18052021")
            self.updateStatus()
            self.application.systemFrame.radarConfigFrame.refreshConfig()
            self.configure(bg = 'green')
        except Exception as e:
            self.configure(bg="red")
            self.statusFrame.statusLabel.set("Error connecting to radar.")
            self.application.api = None
            tkmsg.showerror(title=type(e).__name__, message=str(e))

    def setStatusLabel(self, text):
        self.statusFrame.statusLabel.set(text)

    def updateStatus(self, *args):
        try:
            if self.getAPI() != None:
                self.statusFrame.status = self.getAPI().system.housekeeping.status()
                self.statusFrame.update()
                self.setStatusLabel("Updated from {:s} at {:s}.".format(
                    self.radarAddress.get(),
                    datetime.datetime.now().strftime(DatetimeVar.DATETIME_FORMAT)
                ))
                self.statusFrame.after(5000, self.updateStatus)
            else:
                self.setStatusLabel("Cannot connect to radar at {:s}.".format(
                    self.radarAddress.get()
                ))
        except Exception as e:
            self.statusFrame.statusLabel.set("Error connecting to radar.")
            self.application.systemFrame.configure(bg="red")
            tkmsg.showerror(title=type(e).__name__, message=str(e))

class ApRESTrialBurstFrame(tk.Frame, ApplicationReference):

    def __init__(self, parent, app=None, *args, **kwargs):
        tk.Frame.__init__(self, parent, *args, **kwargs)
        ApplicationReference.__init__(self, app=app, *args, **kwargs)

        self.button = ttk.Button(self,text="Do Trial Burst", command=self.doTrialBurst)
        self.button.grid(row=0, column=0, padx=8, pady=8, ipadx=8, ipady=8, columnspan=5, sticky=(tk.N + tk.E + tk.S + tk.W))

        ttk.Separator(self, orient="horizontal").grid(column=0, row=1, columnspan=5, padx=8, pady=8, sticky=(tk.E + tk.W))
        
        # self.freqMin = tk.IntVar(value=0)
        # self.freqMax = tk.IntVar(value=40000)
        # self.freqMinEntry = ttk.Spinbox(self, textvariable=self.freqMin, from_=0, to=40000)
        # self.freqMaxEntry = ttk.Spinbox(self, textvariable=self.freqMax, from_=0, to=40000)

        # ttk.Label(self, text="Min. Frequency:").grid(column=0, row=2, padx=8, pady=8, sticky=tk.E)
        # self.freqMinEntry.grid(column=1, row=2, padx=8, pady=8, sticky=(tk.E+tk.W))
        # ttk.Label(self, text="Max Frequency:").grid(column=2, row=2, padx=8, pady=8, sticky=tk.E)
        # self.freqMaxEntry.grid(column=3, row=2, padx=8, pady=8, sticky=(tk.E+tk.W))
        # ttk.Button(self, text="Update").grid(column=4, row=2, padx=8, pady=8, sticky=(tk.E + tk.W))
        
        self.chirpDataControls = ChirpDataControlFrame(self, app=app)
        self.chirpDataControls.grid(row=2, column=0, columnspan=5, sticky=(tk.N + tk.E + tk.S + tk.W))

        ttk.Separator(self, orient="horizontal").grid(column=0, row=3, columnspan=5, padx=8, pady=8, sticky=(tk.E + tk.W))
        
        self.trialFigure = Figure(figsize=(4,1.5))
        self.trialFigure.subplots_adjust(
            left=0.05,
            bottom=0.05, 
            right=0.95, 
            top=0.95, 
            wspace=0.4, 
            hspace=0.4
        )
        
        self.trialFigureChirpAx = self.trialFigure.add_subplot(311)
        self.trialFigureChirpAx.set_title('Raw Chirp Data')
        self.trialFigureFFTAx = self.trialFigure.add_subplot(312)
        self.trialFigureFFTAx.set_title('FFT Chirp Data')
        self.trialFigureHistoAx = self.trialFigure.add_subplot(313)
        self.trialFigureHistoAx.set_title('Histograms')
        self.trialFigureCanvas = FigureCanvasTkAgg(self.trialFigure, master=self)
        self.trialFigureCanvas.draw()
        self.trialFigureCanvas.get_tk_widget().grid(padx=8, pady=8, row=4, column=0, columnspan=5, sticky=(tk.E + tk.N + tk.W + tk.S))
        self.trialFigure.patch.set_facecolor("#F0F0F0")
        
        self.columnconfigure(0, weight=0)
        self.columnconfigure(1, weight=1)
        self.columnconfigure(2, weight=0)
        self.columnconfigure(3, weight=1)
        self.columnconfigure(4, weight=1)
        self.rowconfigure(0, weight=0)
        self.rowconfigure(1, weight=0)
        self.rowconfigure(2, weight=0)
        self.rowconfigure(3, weight=0)
        self.rowconfigure(4, weight=1);

    def doTrialBurst(self):

        if self.getAPI() == None:
            tkmsg.showwarning(title="Not connected", message="Cannot start trial burst.")
        else:
            try:
                self.getAPI().radar.trialBurst(callback=self.updateBurstGraphs, wait=False)
                self.button['state'] = "disabled"
            except Exception as e:
                tkmsg.showerror(title=type(e).__name__, message=str(e))
                self.button['state'] = "normal"

    def updateBurstGraphs(self, results):

        self.trialFigureChirpAx.clear()
        self.trialFigureFFTAx.clear()
        self.trialFigureHistoAx.clear()

        fmcw_param = apyres.FMCWParameters(
            fc = (results.stopFrequency + results.startFrequency) / 2,
            B = (results.stopFrequency - results.startFrequency),
            T = results.period
        )

        for k in range(results.nAttenuators):

            # Create RangeProfile object for results
            rp = apyres.RangeProfile.calculate_from_chirp([], np.array(results.chirp[k]), fmcw_param)

            dR = 3e8/(2*fmcw_param.B*2*np.sqrt(self.chirpDataControls.erIceValue.get()))

            self.trialFigureChirpAx.plot(results.chirp[k])
            self.trialFigureFFTAx.plot(
                np.arange(0, dR*(rp.shape[1]), dR), 
                20*np.log10(np.abs(rp[0,:])).transpose()
            )
            self.trialFigureHistoAx.plot(
                results.histogramVoltage,
                results.histogram[k],
                label="AF={:d},RF={:2.2f}".format(results.afGain[k],results.rfAttn[k])
            )
            
        self.trialFigureChirpAx.set_title('Raw Chirp Data')
        self.trialFigureFFTAx.set_title('Range Data')
        self.trialFigureHistoAx.set_title('Histograms')
        self.trialFigureHistoAx.legend()

        # Set limits
        self.trialFigureChirpAx.set_title('Raw Chirp Data')
        self.trialFigureChirpAx.set_xlim([
            self.chirpDataControls.timeMin.get(),
            self.chirpDataControls.timeMax.get()
        ])
        self.trialFigureChirpAx.set_xlabel("Time (s)")
        self.trialFigureChirpAx.set_ylabel("Voltage (V)")

        self.trialFigureFFTAx.set_title('Chirp Range Data')
        self.trialFigureFFTAx.set_xlim([
            self.chirpDataControls.rangeMin.get(),
            self.chirpDataControls.rangeMax.get()
        ])
        self.trialFigureFFTAx.set_xlabel("Range (m)")
        self.trialFigureFFTAx.set_ylabel("Voltage (dBV)")

        self.trialFigureHistoAx.set_xlabel("Voltage (V)")
        self.trialFigureHistoAx.set_ylabel("Count")

        self.trialFigureCanvas.draw()
        self.button['state'] = "normal"

class ChirpDataControlFrame(tk.Frame):

    def __init__(self, parent, app=None, *args, **kwargs):
        tk.Frame.__init__(self, parent, *args, **kwargs)

        timeLabel = tk.Label(self, text="Time")
        timeLabel.grid(row=0, padx=8, pady=2, column=0)
        
        ttk.Separator(self, orient="horizontal").grid(
            column=0, row=1, columnspan=2, padx=8, pady=2, sticky=(tk.E + tk.W))

        # Minimum time 
        timeMinLabel = tk.Label(self, text="Min:")
        timeMinLabel.grid(row=2, column=0, padx=8, pady=2, sticky=tk.W)
        
        self.timeMin = tk.DoubleVar(value=0);
        self.timeMinEntry = ttk.Spinbox(self, textvariable=self.timeMin, from_=0, to=1)
        self.timeMinEntry.grid(row=2, column=1, padx=8, pady=2, sticky=tk.W)

        timeMaxLabel = tk.Label(self, text="Max:")
        timeMaxLabel.grid(row=3, column=0, padx=8, pady=2, sticky=tk.W)
        
        self.timeMax = tk.DoubleVar(value=1);
        self.timeMaxEntry = ttk.Spinbox(self, textvariable=self.timeMax, from_=0, to=1)
        self.timeMaxEntry.grid(row=3,column=1, padx=8, pady=2, sticky=tk.W)
        
        rangeLabel = tk.Label(self, text="Range")
        rangeLabel.grid(row=0, column=2, padx=8, pady=2, sticky=tk.W)

        ttk.Separator(self, orient="horizontal").grid(
            column=2, row=1, columnspan=4, padx=8, pady=2, sticky=(tk.E + tk.W))
        
        rangeMinLabel = tk.Label(self, text="Min:")
        rangeMinLabel.grid(row=2, column=2, padx=8, pady=2, sticky=tk.W)
        
        self.rangeMin = tk.DoubleVar(value=0);
        self.rangeMinEntry = ttk.Spinbox(self, textvariable=self.rangeMin, from_=0, to=5000)
        self.rangeMinEntry.grid(row=2, column=3, padx=8, pady=2, sticky=tk.W)
        
        rangeMaxLabel = tk.Label(self, text="Max:")
        rangeMaxLabel.grid(row=3, column=2, padx=8, pady=2, sticky=tk.W)
        
        self.rangeMax = tk.DoubleVar(value=5000);
        self.rangeMaxEntry = ttk.Spinbox(self, textvariable=self.rangeMax, from_=0, to=5000)
        self.rangeMaxEntry.grid(row=3,column=3, padx=8, pady=2, sticky=tk.W)
        
        erLabel = tk.Label(self, text="er_ice:")
        erLabel.grid(row=2, column=4, padx=8, pady=2, sticky=tk.W)
        
        self.erIceValue = tk.DoubleVar(value=3.18);
        self.erIceEntry = ttk.Spinbox(self, textvariable=self.erIceValue, from_=1, to=80)
        self.erIceEntry.grid(row=2,column=5, padx=8, pady=2, sticky=tk.W)

        self.columnconfigure(0, weight=0)
        self.columnconfigure(1, weight=1)
        self.columnconfigure(2, weight=0)
        self.columnconfigure(3, weight=0)
        self.columnconfigure(4, weight=0)
        self.columnconfigure(5, weight=1)

class ApRESSingleBurstFrame(tk.Frame, ApplicationReference):

    def __init__(self, parent, app=None, *args, **kwargs):
        tk.Frame.__init__(self, parent, *args, **kwargs)
        ApplicationReference.__init__(self, app=app, *args, **kwargs)

        self.pathLabel = ttk.Label(self, text="Survey Path:")
        self.pathLabel.grid(row=0, column=0, padx=8, pady=8, sticky=(tk.N + tk.S + tk.W))

        self.pathVar = tk.StringVar(value=self.get_default_survey_path())
        self.pathEntry = ttk.Entry(self, textvariable=self.pathVar)
        self.pathEntry.grid(row=0, column=1, padx=8, pady=8, sticky=(tk.N + tk.E + tk.W + tk.S))

        self.pathButton = ttk.Button(self, text="...", command=self.update_survey_path)
        self.pathButton.grid(row=0, column=2, padx=8, pady=8, sticky=(tk.N + tk.E + tk.S))

        # self.statusLabel = tk.StringVar(value="")
        # statusUpdateLabel = ttk.Label(self, textvariable=self.statusLabel, wraplength=300)

        self.button = ttk.Button(self,text="Do Single Burst", command=self.do_burst)
        self.button.grid(row=1, column=0, columnspan=3, padx=8, pady=8, ipadx=8, ipady=8, sticky=(tk.N + tk.E + tk.S + tk.W))

        self.dataFigure = Figure(figsize=(4,0.5))
        self.dataFigure.subplots_adjust(
            left=0.05,
            bottom=0.1, 
            right=0.95, 
            # top=0.95, 
            # wspace=0.4, 
            # hspace=0.4
        )
        
        self.chirpDataControls = ChirpDataControlFrame(self)
        self.chirpDataControls.grid(row=3, column=0, columnspan=3, padx=8, pady=8, sticky=(tk.N + tk.E + tk.W + tk.S))

        self.dataFigureChirpAx = self.dataFigure.add_subplot(121)
        self.dataFigureChirpAx.set_title('Raw Chirp Data')
        self.dataFigureFFTAx = self.dataFigure.add_subplot(122)
        self.dataFigureFFTAx.set_title('Chirp Range Data')
        self.dataFigureCanvas = FigureCanvasTkAgg(self.dataFigure, master=self)
        self.dataFigureCanvas.draw()
        self.dataFigureCanvas.get_tk_widget().grid(row=2, column=0, columnspan=3, padx=8, pady=8, sticky=(tk.E + tk.N + tk.W + tk.S))
        self.dataFigure.patch.set_facecolor("#F0F0F0")

        self.fileView = ttk.Treeview(self, columns=('filename','lastmodified','size'), show='headings')
        self.fileView.heading('filename', text='Filename')
        self.fileView.heading('lastmodified', text='Last Modified')
        self.fileView.heading('size', text='Size')
        self.fileView.grid(row=4, column=0, columnspan=3, padx=8, pady=8, sticky=(tk.N + tk.E + tk.S + tk.W))

        self.fileView.bind("<Double-1>", self.load_from_fieldview)

        vsb = tk.Scrollbar(self.fileView, orient="vertical", command=self.fileView.yview)
        vsb.place(relx=0.978, rely=0, relheight=1, relwidth=0.020)

        self.columnconfigure(0, weight=0)
        self.columnconfigure(1, weight=1)
        self.columnconfigure(2, weight=0)

        self.rowconfigure(2,weight=1)
        self.rowconfigure(4,weight=1)
        
        # Update treeview contents
        self.update_file_tree()

    def get_default_survey_path(self):
        """Return default survey path

        :return: path in user home directory
        :rtype: str
        """
        path_name = pathlib.Path.home() / "ApRES" \
            / "Survey_{:s}".format( datetime.datetime.now().strftime("%Y-%m-%d"))
        if not path_name.exists():
            path_name.mkdir(parents=True)
        return str(path_name)

    def update_survey_path(self):
        """Updates the survey path entry field from a file dialog
        """
        path = tk.filedialog.askdirectory(initialdir=self.pathVar.get())

        if len(path) > 0:
            self.pathVar.set(str(pathlib.Path(path)))

        self.update_file_tree()

    def update_file_tree(self):
        
        for child in self.fileView.get_children():
            self.fileView.delete(child)

        path = pathlib.Path(self.pathVar.get())

        filenames = []
        file_dates = []
        
        if path.is_dir():
            print("Getting files from {:s}".format(str(path)))
            for f in os.listdir(path):
                f_path = pathlib.Path(path / f)
                if f_path.is_file() \
                and os.path.splitext(f)[1].lower() == ".dat":
                    print("Adding {:s}".format(f))
                    file_dates.append(f_path.stat().st_mtime)
                    filenames.append(f_path)
                    # self.fileView.insert("", tk.END, values=(
                    #     f, 
                    #     datetime.datetime.fromtimestamp(f_path.stat().st_mtime)))

        # Sort array
        sort_idx = np.argsort(file_dates)

        for k in reversed(sort_idx):
            self.fileView.insert("", tk.END, values=(
                filenames[k].name, 
                datetime.datetime.fromtimestamp(file_dates[k]),
                filenames[k].stat().st_size
            ))

    def do_burst(self):
        """Do burst using current settings
        """
        if self.getAPI() == None:
            tkmsg.showwarning(title="Not connected", message="Cannot start burst.")
        else:
            try:
                self.button['state'] = "disabled"
                self.getAPI().radar.burst(callback=self.save_latest_burst, wait=False)
            except Exception as e:
                tkmsg.showerror(title=type(e).__name__, message=str(e))
                self.button['state'] = "normal"

    def save_latest_burst(self, results):
        """Save file and rename
        """
        try:
            saved_to = self.getAPI().data.download(results.filename, self.pathVar.get());

            saved_path = pathlib.Path(saved_to)

            self.fileView.insert("", 0, values=(
                saved_path.name,
                datetime.datetime.now(),
                saved_path.stat().st_size
            ))

            # Reset button
            self.button['state'] = "normal"

            self.load_data(str(saved_path))

        except NotFoundException as e:
            tkmsg.showerror(title=type(e).__name__, message="File not found.  Check you have installed an SD card?")
            self.button['state'] = "normal"

    def load_from_fieldview(self, event):
        item = self.fileView.selection()[0]
        filename = pathlib.Path(self.pathVar.get()) / self.fileView.item(item)['values'][0]
        self.load_data(filename)

    def load_data(self, filename):
        
        # Load data
        burst_data = apyres.read(filename, skip_burst=False)
        # Clear figures
        self.dataFigureChirpAx.clear()
        self.dataFigureFFTAx.clear()

        # Plot chirp data
        self.dataFigureChirpAx.plot(
            burst_data.chirp_time(), 
            burst_data.chirp_voltage.transpose()
        )

        # Calculate range profile
        rp = apyres.RangeProfile.calculate_from_chirp([], burst_data.chirp_voltage, burst_data.fmcw_parameters)
        dR = 3e8/(2*burst_data.fmcw_parameters.B*2*np.sqrt(self.chirpDataControls.erIceValue.get()))
        self.dataFigureFFTAx.plot(
            np.arange(0, dR*(rp.shape[1]), dR),
            20*np.log10(np.abs(rp.transpose()))
        )

        # Set title
        self.dataFigureChirpAx.set_title('Raw Chirp Data')
        self.dataFigureChirpAx.set_xlim([
            self.chirpDataControls.timeMin.get(),
            self.chirpDataControls.timeMax.get()
        ])
        self.dataFigureChirpAx.set_xlabel("Time (s)")
        self.dataFigureChirpAx.set_ylabel("Voltage (V)")

        self.dataFigureFFTAx.set_title('Chirp Range Data')
        self.dataFigureFFTAx.set_xlim([
            self.chirpDataControls.rangeMin.get(),
            self.chirpDataControls.rangeMax.get()
        ])
        self.dataFigureFFTAx.set_xlabel("Range (m)")
        self.dataFigureFFTAx.set_ylabel("Voltage (dBV)")

        self.dataFigureCanvas.draw()

class ApRESSurveyApplication(tk.Tk):
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.title("ApRES Survey Tool")
        self.geometry("1200x800")
        self.api = None

        self.systemFrame = ApRESSystemFrame(self, app=self)
        # self.systemFrame.pack(expand=1, fill=tk.BOTH)
        self.systemFrame.grid(row=0, column=0, sticky=(tk.W + tk.N + tk.S))
        
        self.resultsBook = ttk.Notebook(self)
        self.resultsBook.grid(row=0, column=1, sticky=(tk.W + tk.N + tk.E + tk.S))
        
        # Trial burst frame
        self.trialBurstFrame = ApRESTrialBurstFrame(self.resultsBook, app=self)
        self.singleBurstFrame = ApRESSingleBurstFrame(self.resultsBook, app=self)
        
        self.resultsBook.add(self.trialBurstFrame, text="Trial Burst")
        self.resultsBook.add(self.singleBurstFrame, text="Single Burst")

        self.columnconfigure(0, weight=0, minsize=200)
        self.columnconfigure(1, weight=4)
        self.rowconfigure(0, weight=1)

        menubar = tk.Menu(self);
        self.config(menu=menubar)
        file_menu = tk.Menu(menubar)
        file_menu.add_command(
            label="Set API Key...", 
            command=self.setAPIKey
        )
        file_menu.add_command(
            label="Exit",
            command=self.destroy
        )

        menubar.add_cascade(label="File",menu=file_menu)

    def setAPIKey(self, *args):
        key = tkdlg.askstring(title="Set API Key", prompt="Enter API Key:")
        if key != None or len(key) > 0:
            self.api.setKey(key)
        else:
            self.api.setKey("")
            tkmsg.showwarning(title="Empty API Key", message="No API key entered.  Some functionality may not work.")

if __name__ == "__main__":
    app = ApRESSurveyApplication()
    app.mainloop()