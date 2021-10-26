import datetime 
import tkinter as tk
from tkinter import ttk

class DatetimeVar(tk.StringVar):

    DATETIME_FORMAT = "%y-%m-%d %H:%M:%S"

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




class StatusFrame(tk.LabelFrame):
    
    def __init__(self, parent, *args, **kwargs):

        super().__init__(parent, text="Status", *args, **kwargs)

        # Create test treeview component
        statusTree = ttk.Treeview(self, columns=('field','value'), show='headings')
        statusTree.heading('field', text='Field')
        statusTree.heading('value', text='Value')

        self.timeVAB = DatetimeVar(datetime.datetime.now())

        statusTree.insert('', tk.END, values=('Time VAB', self.timeVAB))
        statusTree.insert('', tk.END, values=('Battery Voltage', '0V'))
        statusTree.insert('', tk.END, values=('Latitude', '0.0'))
        statusTree.insert('', tk.END, values=('Longitude', '0.0'))
        
        self.updateValue = tk.StringVar(value="Not updated")
        statusUpdateLabel = ttk.Label(self, textvariable=self.updateValue)

        statusTree.grid(row=0, column=0, sticky=(tk.E + tk.N + tk.S + tk.W))
        statusUpdateLabel.grid(row=1, column=0, sticky=(tk.E + tk.S + tk.W))
        
        self.rowconfigure(0, weight=1)
        self.rowconfigure(1, weight=0)
        self.columnconfigure(0, weight=1)

class ApRESSurveyApplication(tk.Tk):
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.title("ApRES Survey Tool")
        self.geometry("1200x800")

        statusFrame = StatusFrame(self)
        statusFrame.pack(expand=1, fill=tk.BOTH)
        # statusFrame.grid(row=0, column=0, sticky=(tk.W + tk.N + tk.S))

if __name__ == "__main__":
    app = ApRESSurveyApplication()
    app.mainloop()