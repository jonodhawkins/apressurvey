import apreshttp
import datetime
import matplotlib.pyplot as plt 
from matplotlib.figure import Figure
from matplotlib.backends.backend_tkagg import (FigureCanvasTkAgg, NavigationToolbar2Tk)
import numpy as np
import os
import tkinter as tk
import tkinter.messagebox as tkmsg
import tkinter.simpledialog as tkdlg
import tkinter.filedialog as tkfiledlg
from tkinter import ttk

class ApplicationReference:

    def __init__(self, app=None): 
        self.application = app
    
    def setApplication(self, ref):
        self.application = ref

    def getApplication(self):
        return self.application

    def getAPI(self):
        return self.application.api

class DatetimeVar(tk.StringVar):

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
        if self.datetime == None:
            return datetime.datetime.now().strftime(self.DATETIME_FORMAT)
        else:
            return self.datetime.strftime(self.DATETIME_FORMAT)

    def set(self, value):
        if isinstance(value, datetime.datetime):
            self.datetime = datetime
            super().set(value.strftime(self.DATETIME_FORMAT))
        elif isinstance(value, str):
            self.datetime = datetime.datetime.strptime(value, self.DATETIME_FORMAT)
            super().set(value)
        else:
            raise ValueError("Input to set should be a datetime object.")

class StatusFrame(tk.LabelFrame, ApplicationReference):

    BATTERY_LOG_SIZE = 1024
    BATTERY_LOG_INTERVAL = 5000
    
    def __init__(self, parent, app=None, *args, **kwargs):

        ApplicationReference.__init__(self, app=app)
        tk.LabelFrame.__init__(self, parent, text="Status", *args, **kwargs)

        # Create test treeview component
        self.statusTree = ttk.Treeview(self, columns=('field','value'), show='headings')
        self.statusTree.heading('field', text='Field')
        self.statusTree.heading('value', text='Value')

        self.batteryLog = np.zeros(self.BATTERY_LOG_SIZE)

        now = datetime.datetime.now().strftime(DatetimeVar.DATETIME_FORMAT)

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

        self.batteryFigure = Figure(figsize=(4,2))
        self.batteryFigureAx = self.batteryFigure.add_subplot(111)
        self.batteryFigureCanvas = FigureCanvasTkAgg(self.batteryFigure, master=self)
        self.batteryFigureCanvas.draw()
        self.batteryFigureCanvas.get_tk_widget().grid(padx=8, pady=8, row=1, column=0, sticky=(tk.E + tk.N + tk.W + tk.S))
        self.batteryFigure.patch.set_facecolor("#F0F0F0")

        self.statusLabel = tk.StringVar(value="Not updated.")
        statusUpdateLabel = ttk.Label(self, textvariable=self.statusLabel)

        self.statusTree.grid(padx=8, pady=8, row=0, column=0, sticky=(tk.E + tk.N + tk.S + tk.W))
        statusUpdateLabel.grid(row=2, column=0, sticky=(tk.E + tk.S + tk.W))
        
        self.rowconfigure(0, weight=1)
        self.rowconfigure(1, weight=0)
        self.columnconfigure(0, weight=1)

        self.update()

        self.batteryLogUpdate()

    def batteryLogUpdate(self):

        print("Doing battery log update {:f}".format(self.status.batteryVoltage))
        # Shift array back 1
        self.batteryLog = np.roll(self.batteryLog, -1)
        self.batteryLog[-1] = self.status.batteryVoltage
        
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

        self.after(self.BATTERY_LOG_INTERVAL, self.batteryLogUpdate)


    def update(self):
        
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

    def __init__(self, parent, app=None, *args, **kwargs):
        ApplicationReference.__init__(self, app=app)
        tk.LabelFrame.__init__(self, parent, text="Config", *args, **kwargs)

        downloadConfigBttn = ttk.Button(self, text="Download...", command=self.downloadConfig)
        uploadConfigBttn = ttk.Button(self, text="Upload...", command=self.uploadConfig)
        resetBttn = ttk.Button(self, text="Reset", command=self.reset)

        downloadConfigBttn.grid(padx=8, pady=8, ipadx=4, ipady=4, column=0, row=0, sticky=(tk.E + tk.N + tk.S + tk.W))
        uploadConfigBttn.grid(padx=8, pady=8, ipadx=4, ipady=4, column=1, row=0, sticky=(tk.E + tk.N + tk.S + tk.W))
        resetBttn.grid(padx=8, pady=8, ipadx=4, ipady=4, column=2, row=0, sticky=(tk.E + tk.N + tk.S + tk.W))

        self.columnconfigure(0, weight=1)
        self.columnconfigure(1, weight=1)
        self.columnconfigure(2, weight=1)

    def downloadConfig(self, *args):
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

class BurstConfigFrame(tk.LabelFrame, ApplicationReference):

    def __init__(self, parent, app=None, *args, **kwargs):
        ApplicationReference.__init__(self, app=app)
        tk.LabelFrame.__init__(self, parent, title="Burst Config", *args, **kwargs)


        
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

        radarConnectBttn = ttk.Button(self, text="Connect", command=self.connectToRadar)

        radarAddressCombo.grid(padx=8, pady=8, row=0, column=0, sticky=(tk.E + tk.N + tk.W + tk.S))
        radarConnectBttn.grid(padx=8, pady=8, ipadx=4, ipady=4, row=0, column=1, sticky=tk.W)

        self.configFrame = ConfigFrame(self, app=app)
        self.configFrame.grid(padx=8, pady=8, row=1, column=0, columnspan=2, sticky=(tk.N + tk.E + tk.S + tk.W))

        self.statusFrame = StatusFrame(self, app=app)
        self.statusFrame.grid(padx=8, pady=8, row=2, column=0, columnspan=2, sticky=(tk.N + tk.E + tk.S + tk.W))

        self.columnconfigure(0,weight=3)
        self.columnconfigure(1,weight=0)
        self.rowconfigure(0,weight=0)
        self.rowconfigure(1,weight=0)
        self.rowconfigure(2,weight=1)

    def connectToRadar(self, *args):
        try:
            self.application.api = apreshttp.API(self.radarAddress.get())
            self.application.api.setKey("18052021")
            self.updateStatus()
        except Exception as e:
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
            tkmsg.showerror(title=type(e).__name__, message=str(e))

class ApRESSurveyApplication(tk.Tk):
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.title("ApRES Survey Tool")
        self.geometry("1200x800")
        self.api = None

        self.systemFrame = ApRESSystemFrame(self, app=self)
        # self.systemFrame.pack(expand=1, fill=tk.BOTH)
        self.systemFrame.grid(row=0, column=0, sticky=(tk.W + tk.N + tk.S))
        ttk.Frame(self).grid(row=0, column=1)

        self.columnconfigure(0, weight=1)
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