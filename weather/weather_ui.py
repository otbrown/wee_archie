# -*- coding: utf-8 -*-
import client
import wx
from wx.lib.masked import *
import vtk

import numpy as np

import matplotlib
matplotlib.use("WXAgg")

from matplotlib.backends.backend_wxagg import FigureCanvasWxAgg as FigureCanvas
from matplotlib.backends.backend_wx import NavigationToolbar2Wx
from matplotlib.figure import Figure
from time import strftime

# New module to import the live weather forcast
from weather_live import LiveWeather

# select the UI abstract superclass to derive from
UI = client.AbstractvtkUI

imageFile = 'uk.jpg'
rain = 'resizedrain.jpg'
cloud = 'resizedcloud.jpg'
sun = 'resizedsun.jpg'

edinburgh = []
london = []
cornwall = []
highlands = []

# Derive the demo-specific GUI class from the AbstractUI class
class WeatherWindow(UI):
    def __init__(self, parent, title, demo, servercomm):

        # call superclass' __init__
        UI.__init__(self, parent, title, demo, servercomm)

        # panel=wx.Panel(self)
        wx.Frame.CenterOnScreen(self)

        self.fullscreen = False
        self.playing = False
        self.decompositiongrid = True
        self.timeofyear = None
        self.rainmass = 0
        self.cropslevel = 0
        self.waterlevel = 0
        self.numberofcores = 0
        self.columnsinX = 1
        self.columnsinY = 1
        self.mappers = {}
        self.actors = {}
        self.filters = {}
        self.widgets = {}
        self.views = {}

        self.demo = demo
        self.servercomm = servercomm
        self.title = title

        self.mode = 0

        menubar = wx.MenuBar()
        playbackMenu = wx.Menu()
        self.playpauseitem = playbackMenu.Append(wx.ID_ANY, 'Play', 'Pause playback')
        cease = playbackMenu.Append(wx.ID_ANY, 'Stop', 'Stop simulation')

        fileMenu = wx.Menu()
        settings = fileMenu.Append(wx.ID_ANY, 'Settings', 'Open settings window')
        playbackAdded = fileMenu.AppendSubMenu(playbackMenu, 'Playback', 'Playback control')
        fitem = fileMenu.Append(wx.ID_EXIT, 'Quit', 'Quit application')

        viewMenu = wx.Menu()
        temp = viewMenu.Append(wx.ID_ANY, 'Temperature', 'Change to temp view')
        press = viewMenu.Append(wx.ID_ANY, 'Pressure', 'Change to press view')
        real = viewMenu.Append(wx.ID_ANY, 'Real World', 'Change to real view')

        gridCheckItem=viewMenu.AppendCheckItem(wx.ID_ANY, 'Show grid', 'Show decomposition grid')

        menubar.Append(fileMenu, '&File')
        menubar.Append(viewMenu, '&Views')
        self.SetMenuBar(menubar)

        self.Bind(wx.EVT_MENU, self.OnQuit, fitem)
        self.Bind(wx.EVT_MENU, self.OpenWindow, settings)
        self.Bind(wx.EVT_MENU, self.temp_view, temp)
        self.Bind(wx.EVT_MENU, self.press_view, press)
        self.Bind(wx.EVT_MENU, self.real_view, real)

        self.Bind(wx.EVT_MENU, self.pauseResult, self.playpauseitem)
        self.Bind(wx.EVT_MENU, self.onStopSim, cease)
        self.Bind(wx.EVT_MENU, self.togglegrid, gridCheckItem)

        # add another renderer for the bottom part
        self.bottomrenderer = vtk.vtkRenderer()
        self.bottomrenderer.SetViewport(0, 0, 1, 0.3)

        # set up sizers that allow you to position window elements easily
        # main sizer - arrange items horizontally on screen (controls on left, vtk interactor on right)
        self.mainsizer = wx.BoxSizer(wx.HORIZONTAL)

        # text at bottom that displays the current frame number
        #self.logger = wx.TextCtrl(self, style=wx.TE_READONLY)

        # This is where the demo is attached to the window.
        self.mainsizer.Add(self.vtkwidget, 2, wx.EXPAND)

        # attach main sizer to the window
        self.SetSizer(self.mainsizer)
        self.SetAutoLayout(1)
        self.mainsizer.Fit(self)

        # create mapper
        # self.mapper=vtk.vtkPolyDataMapper()

        self.StartInteractor()

        # show window
        self.Show()

        self.OpenWindow()

    # Function to call NewWindow class to allow a button to open it.
    def OpenWindow(self, event=None):
        self.new = NewWindow(None, -1, self.title, self.demo, self.servercomm, self)
        self.new.Show()

    def temp_view(self, e):
        self.mode = 1

    def press_view(self, e):
        self.mode = 2

    def real_view(self, e):
        self.mode = 0

    def OnQuit(self, e):
        self.Close()

    def StartInteractor(self):
        UI.StartInteractor(self)

    def StartSim(self, config):
        UI.StartSim(self, config)

    def onStopSim(self, e):
        self.StopSim()

    def togglegrid(self, e):
        if self.decompositiongrid is True:
            self.decompositiongrid = False
        else:
            self.decompositiongrid = True

        if self.timer.IsRunning():
            self.timer.Stop()
            self.timer.Start()

    def pauseResult(self, e):
        if not self.playing:  # play
            self.getdata.value = True
            self.playpauseitem.SetText("Pause")
            self.playing = True

        else:  # pause
            self.getdata.value = False
            self.playpauseitem.SetText("Resume")
            self.playing = False

    def StopSim(self):
        UI.StopSim(self)

    def TimerCallback(self, e):
        UI.TimerCallback(self, e)

        #self.logger.SetValue("Frame %d of %d" % (self.CurrentFrame, self.nfiles.value - 1))

    def OnClose(self, e):
        UI.OnClose(self, e)

    # ----------------------------------------------------------------------
    # ------------- New methods specific to demo go here -------------------
    # ----------------------------------------------------------------------

########----------------------------------------Sam's new classes---------------------------


# Class to create a new window for the "settings".
class NewWindow(wx.Frame):
    def __init__(self, parent, id, title, demo, servercomm, mainWeatherWindow):
        W,H= wx.GetDisplaySize()
        height=0.9*H
        width=height*(9./14.)
        wx.Frame.__init__(self, parent, id, 'Settings', size=(width, height))
        wx.Frame.CenterOnScreen(self)

        self.weatherLocationCode=3166
        self.mainWeatherWindow=mainWeatherWindow

        self.demo = demo
        self.servercomm = servercomm
        self.title = title

        # Create a panel and notebook (tabs holder)
        p = wx.Panel(self)
        nb = wx.Notebook(p)

        #we want to draw the window on screen first to make sure everything is sized coreectly
        sizer = wx.BoxSizer()
        sizer.Add(nb, 1, wx.EXPAND)

        p.SetSizer(sizer)

        self.Show()
        self.Fit()

        # Create the tab windows
        #self.tab3 = TabAdvanced(nb, self.title, self.demo, self.servercomm, mainWeatherWindow)
        self.tab2 = TabSetup(nb, self)
        self.tab3= TabWeather(nb, self)
        self.tab1 = TabLocation(nb, self.tab3, self.tab2, width, height, self)

        # Add the windows to tabs and name them.
        nb.AddPage(self.tab1, "Location")

        #make sure layout of the tab2 is correct
        self.tab2.Layout()
        self.tab3.Layout()

        #redraw the chip image and the pie chart to make sure they display correctly
        self.tab2.UpdateChip()
        self.tab3.UpdatePie()

    def StartStopSim(self, e):
        # if simulation is not started then start a new simulation
        if not self.servercomm.IsStarted():
            self.writeConfig()
            config = "config.mcf"
            self.mainWeatherWindow.StartSim(config)
            self.mainWeatherWindow.playing = True
            # load the first data file
            self.mainWeatherWindow.getdata.value = True
            self.Close()

        # if simulation is started then stop simulation
        else:
            dlg = wx.MessageDialog(self, "Are you sure?", "This will stop the current simulation.", wx.OK | wx.CANCEL)
            if dlg.ShowModal() == wx.ID_OK:
                self.mainWeatherWindow.StopSim()
                try:
                    for actor in self.mainWeatherWindow.renderer.GetActors():
                        self.mainWeatherWindow.renderer.RemoveActor(actor)
                    self.mainWeatherWindow.actors.clear()
                except:
                    pass
                self.mainWeatherWindow.vtkwidget.GetRenderWindow().Render()

    def writeConfig(self):
        # because the events or something does not work for setting there values, set them here

        weatherInstance=LiveWeather(self.weatherLocationCode)

        self.demo.setBaseHour(weatherInstance.target_time())

        f = open('config.mcf', 'w+')

        f.write('global_configuration=outreach_config')

        # pressure settings
        f.write('\nsurface_pressure='+str(weatherInstance.pressure())+'00')
        f.write('\nsurface_reference_pressure='+str(weatherInstance.pressure())+'00')
        f.write('\nfixed_cloud_number=1.0e9')

        # switch sef.timeofyear

        f.write('\nf_force_pl_q=-1.2e-8, -1.2e-8, 0.0, 0.0')

        f.write('\nsurface_latent_heat_flux=200.052')
        f.write('\nsurface_sensible_heat_flux=16.04')

        # amount of water
        f.write('\nz_init_pl_q=0.0, 520.0, 1480., 2000., 3000.')
        f.write('\nf_init_pl_q=17.0e-3, 16.3e-3, 10.7e-3, 4.2e-3, 3.0e-3')

        # wind config

        wind_direction=weatherInstance.wind_direction()[0]
        winforce = weatherInstance.wind_speed() # TODO - negative and direction

        if (wind_direction == "N" or wind_direction == "S"):
            prognotic_wind_field="u"
        else:
            prognotic_wind_field="v"

        if (wind_direction == "S" or wind_direction == "W"): winforce=-winforce
        f.write('\nz_init_pl_'+prognotic_wind_field+'=0.0, 700.0, 3000.')
        f.write('\nf_init_pl_'+prognotic_wind_field+'=' + str(round(winforce*-1.7,2)) + ', ' + str(round(winforce*-1.6,2)) + ', ' + str(winforce*-0.8))

        # temperature settings
        temperature = 273.15 + weatherInstance.temperature()
        tempstr = str(temperature)

        f.write('\nthref0 = ' + tempstr)

        f.write('\nz_init_pl_theta=0.0, 520.0, 1480., 2000., 3000.')

        f.write('\nf_init_pl_theta=' + tempstr + ', ' + tempstr + ', ' + str(temperature+2) + ', ' + str(temperature+5) + ', ' + str(temperature+7))

        # core number and decomposition
        f.write('\ncores_per_pi=' + str(self.tab2.coresRadio.GetSelection()+1))
        f.write('\nnum_nodes=' + str(self.tab2.NodesSlider.GetValue()))

        if (self.tab3.A < 0.2):
            f.write('\nfftsolver_enabled=.false.\niterativesolver_enabled=.true.\ntolerance=1.e-1')
        elif (self.tab3.A > 0.2 and self.tab3.A < 0.3):
            f.write('\nfftsolver_enabled=.false.\niterativesolver_enabled=.true.\ntolerance=1.e-2')
        elif (self.tab3.A > 0.3 and self.tab3.A < 0.4):
            f.write('\nfftsolver_enabled=.false.\niterativesolver_enabled=.true.\ntolerance=1.e-3')
        elif (self.tab3.A > 0.4 and self.tab3.A < 0.5):
            f.write('\nfftsolver_enabled=.false.\niterativesolver_enabled=.true.\ntolerance=1.e-5')
        elif (self.tab3.A > 0.5 and self.tab3.A < 0.6):
            f.write('\nfftsolver_enabled=.true.\niterativesolver_enabled=.false.')
        else:
            f.write('\nfftsolver_enabled=.false.\niterativesolver_enabled=.true.\ntolerance=1.e-8')

        if (self.tab3.B < 0.2):
             f.write('\nadvection_flow_fields=pw\nadvection_theta_field=pw\nadvection_q_fields=pw')
        elif (self.tab3.B > 0.2 and self.tab3.B < 0.3):
            f.write('\nadvection_flow_fields=pw\nadvection_theta_field=tvd\nadvection_q_fields=pw')
        elif (self.tab3.B > 0.3 and self.tab3.B < 0.4):
            f.write('\nadvection_flow_fields=pw\nadvection_theta_field=tvd\nadvection_q_fields=tvd')
        else:
            f.write('\nadvection_flow_fields=tvd\nadvection_theta_field=tvd\nadvection_q_fields=tvd')

        if (self.tab3.C < 0.3):
            f.write('\ncasim_enabled=.false.\nsimplecloud_enabled=.false.')
        elif (self.tab3.C > 0.2 and self.tab3.C < 0.3):
            f.write('\ncasim_enabled=.false.\nsimplecloud_enabled=.true.')
        else:
            f.write('\ncasim_enabled=.true.\nsimplecloud_enabled=.false.')

        f.close()

class TabWeather(wx.Panel):
    def __init__(self, parent, setupWindow):
        wx.Panel.__init__(self, parent)

        self.WinSizer=wx.BoxSizer(wx.VERTICAL)
         #Bottom panel, which will contain the sliders and piechart panels
        self.PhysicsPanel=wx.Panel(self,style=wx.BORDER_SUNKEN)

        #Add this to the window's sizer
        self.WinSizer.Add(self.PhysicsPanel,2,wx.EXPAND| wx.ALL, border=5)

        #sizer for the bottom row of controls
        self.BottomSizer=wx.BoxSizer(wx.VERTICAL)

        #assign this sizer to the PhysicsPanel
        self.PhysicsPanel.SetSizer(self.BottomSizer)

        #the bottom panels
        self.SlidersPanel=wx.Panel(self.PhysicsPanel,size=(200,100))
        self.PiePanel=wx.Panel(self.PhysicsPanel,size=(200,100))

        #Add the bottom panels to the BottomSizer
        self.BottomSizer.Add(self.SlidersPanel,1,wx.EXPAND| wx.ALL, border=5)
        self.BottomSizer.Add(self.PiePanel,1,wx.EXPAND| wx.ALL, border=5)

        #sliders panel

        #set up main sizer
        slidersSizer=wx.BoxSizer(wx.VERTICAL)
        self.SlidersPanel.SetSizer(slidersSizer)

        #label for this panel
        t3=wx.StaticText(self.SlidersPanel,label="Weather")
        slidersSizer.Add(t3,0,wx.CENTRE,border=5)

        #set up the sliders
        self.sliders=[]
        for i in range(3):
            self.sliders.append(wx.Slider(self.SlidersPanel,minValue=0,maxValue=100,value=33))

        #s1=wx.StaticText(self.SlidersPanel,label="Pressure")
        #s1.SetForegroundColour((255,0,0))
        slidersSizer.Add(wx.StaticText(self.SlidersPanel,label="Pressure"),0,wx.LEFT)
        slidersSizer.Add(self.sliders[0],1,wx.EXPAND)

        slidersSizer.Add(wx.StaticText(self.SlidersPanel,label="Wind"),0,wx.LEFT)
        slidersSizer.Add(self.sliders[1],1,wx.EXPAND)

        slidersSizer.Add(wx.StaticText(self.SlidersPanel,label="Cloud"),0,wx.LEFT)
        slidersSizer.Add(self.sliders[2],1,wx.EXPAND)

        #set up the reset button and bind pressing it to the ResetSliders method
        self.SliderResetButton=wx.Button(self.SlidersPanel,label="Reset")
        slidersSizer.Add(self.SliderResetButton,0,wx.EXPAND)
        self.Bind(wx.EVT_BUTTON,self.ResetSliders,self.SliderResetButton)

        #define the initial values of A, B and C (A+B+C=1)
        self.A=1./3.
        self.B=1./3.
        self.C=1./3.

        #call the method to set the sliders to the appropriate places to reflect the values of A, B, C
        self.setSliders()

        #bind moving the sliders to the relevant methods to update the values of the others
        self.Bind(wx.EVT_SLIDER,self.UpdateA,self.sliders[0])
        self.Bind(wx.EVT_SLIDER,self.UpdateB,self.sliders[1])
        self.Bind(wx.EVT_SLIDER,self.UpdateC,self.sliders[2])

        #pie chart panel

        #set up the main sizer
        pieSizer=wx.BoxSizer(wx.VERTICAL)
        self.PiePanel.SetSizer(pieSizer)

        #t4=wx.StaticText(self.PiePanel,label="pie chart")
        #pieSizer.Add(t4,0,wx.LEFT)

        #setup the pie chart figure (transparent background  - facecolor=none)
        self.figure=Figure(facecolor="none")
        self.canvas = FigureCanvas(self.PiePanel, -1, self.figure)
        pieSizer.Add(self.canvas,1,wx.GROW)

        self.GoButton=wx.Button(self,label="Start Simulation")
        self.Bind(wx.EVT_BUTTON,setupWindow.StartStopSim,self.GoButton)
        self.WinSizer.Add(self.GoButton,0,wx.EXPAND)

        self.SetSizer(self.WinSizer)

        #fit all the graphical elements to the window then display the window


        #update the pie chart and the chip graphic (window must be drawn first to get everything positioned properly)

        self.Show()
        self.Layout()

        self.UpdatePie()

         #(re)draws the pie chart
    def UpdatePie(self,e=None):
        #get the values of A, B, C
        self.Layout()

        a=self.A
        b=self.B
        c=self.C

        values=[a,b,c]
        labels=["Pressure","Wind","Cloud"]
        colors=["red","green","blue"]
        #clear existing figure
        self.figure.clf()

        #redraw figure
        self.axes=self.figure.add_subplot(111)
        self.axes.pie(values,labels=labels,colors=colors)
        self.axes.axis("equal")
        self.canvas.draw()
        self.canvas.Refresh()

    #resets the sliders to the default values
    def ResetSliders(self,e=None):
        self.A=1./3.
        self.B=1./3.
        self.C=1./3.

        self.setSliders()

        #redraw the pie chart
        self.UpdatePie()


    #methods called when the pie chart sliders are adjusted
    def UpdateA(self,e=None):
        self.UpdateABC(0,self.sliders[0].GetValue())

    def UpdateB(self,e=None):
        self.UpdateABC(1,self.sliders[1].GetValue())

    def UpdateC(self,e=None):
        self.UpdateABC(2,self.sliders[2].GetValue())


    #sets the sliders to the values of a, b, c
    def setSliders(self):
        a=int(self.A*100)
        b=int(self.B*100)
        c=int(self.C*100)

        self.sliders[0].SetValue(a)
        self.sliders[1].SetValue(b)
        self.sliders[2].SetValue(c)

    #given an updated slider (number i, value a), will alter the other two sliders (b and c) to ensure a+b+c=1
    def UpdateABC(self,i,a):

        a=float(a)/100.001+0.000005

        #control how a,b,c map to A,B,C (the actual sliders)
        if (i == 0):
            b=self.B
            c=self.C
        elif (i == 1):
            b=self.C
            c=self.A
        else:
            b=self.A
            c=self.B

        #A+B+C should equal 1, but it won't as 'a' has been updated
        new1 = a+b+c
        #print("new1=",1)

        #find the amount we need to adjust b and c by to get back to a+b+c=1
        diff = 1.0-new1

        #divide this amount up proportionately between b and c
        db = diff * b/(b+c)
        dc = diff * c/(b+c)

        #update b and c
        b=b+db
        c=c+dc


        #assign new values
        if (i == 0):
            self.A=a
            self.B=b
            self.C=c
        elif (i == 1):
            self.B=a
            self.C=b
            self.A=c
        else:
            self.A=b
            self.B=c
            self.C=a

        #move sliders as required and update the pie chart
        self.setSliders()
        self.UpdatePie()


class TabSetup(wx.Panel):
    def __init__(self, parent, setupWindow):
        wx.Panel.__init__(self, parent)
		#The window's sizer - for the rows of control panels and the go button
        self.WinSizer=wx.BoxSizer(wx.VERTICAL)

        self.setupWindow=setupWindow

        #sizer for the top row of controls
        self.TopSizer=wx.BoxSizer(wx.HORIZONTAL)

        self.LocationPanel=wx.Panel(self,style=wx.BORDER_SUNKEN)
        #self.TopLeftSizer=wx.BoxSizer(wx.VERTICAL)

        #Add this to the window's sizer
        self.WinSizer.Add(self.LocationPanel,0,wx.EXPAND | wx.ALL,border=5)
        self.WinSizer.Add(self.TopSizer,1,wx.EXPAND)

        # Top row of control panels

        self.CoresPanel=wx.Panel(self,style=wx.BORDER_SUNKEN,size=(200,100))
        self.NodesPanel=wx.Panel(self,style=wx.BORDER_SUNKEN,size=(200,100))


        #self.TopLeftSizer.Add(self.LocationPanel, 1,wx.EXPAND | wx.ALL,border=5)
        #self.TopLeftSizer.Add(self.CoresPanel, 1,wx.EXPAND | wx.ALL,border=5)

        #Add these panels to their sizer
        self.TopSizer.Add(self.CoresPanel,1,wx.EXPAND | wx.ALL,border=5)
        self.TopSizer.Add(self.NodesPanel,1,wx.EXPAND| wx.ALL,border=5)

        locationSizer=wx.BoxSizer(wx.VERTICAL)
        self.LocationPanel.SetSizer(locationSizer)

        self.text_Location=wx.StaticText(self.LocationPanel,label="Location: Edinburgh")
        self.time_Location=wx.StaticText(self.LocationPanel,label="Time: 0600 Z")
        self.weather_Location=wx.StaticText(self.LocationPanel,label="Weather: Cloudy")

        locationSizer.Add(self.text_Location,0,wx.LEFT| wx.TOP,border=5)
        locationSizer.Add(self.time_Location,0,wx.LEFT| wx.ALL,border=5)
        locationSizer.Add(self.weather_Location,0,wx.LEFT | wx.BOTTOM,border=5)

        # Cores Panel

        #set up main sizer for the panel
        coresSizer=wx.BoxSizer(wx.VERTICAL)
        self.CoresPanel.SetSizer(coresSizer)

        #label for the panel
        t1=wx.StaticText(self.CoresPanel,label="Number of Cores per Node")


        #load initial image - this will be reloaded, but we need something there to workout the dimensions of the panel
        file="chip1.png"
        bmp=wx.Image(file, wx.BITMAP_TYPE_ANY).Scale(300,300).ConvertToBitmap()
        self.bitmap1 = wx.StaticBitmap(self.CoresPanel,bitmap=bmp, size=(300, 300))

        #Radiobox to select the number of cores
        self.coresRadio=wx.RadioBox(self.CoresPanel,choices=["1","2","3","4"])
        self.coresRadio.SetSelection(0)

        #bind changing the selection to the UpdateChip method (which redraws the image of the chip)
        self.Bind(wx.EVT_RADIOBOX,self.UpdateChip,self.coresRadio)

        #Add these to their sizer
        coresSizer.Add(t1,0,wx.CENTRE,border=5)
        coresSizer.Add(self.bitmap1,1,wx.ALIGN_CENTRE)
        coresSizer.Add(self.coresRadio,0,wx.ALIGN_CENTRE)

        # Nodes Panel

        #set up main sizer
        nodesSizer=wx.BoxSizer(wx.VERTICAL)
        self.NodesPanel.SetSizer(nodesSizer)

        #label for the panel
        t2=wx.StaticText(self.NodesPanel,label="Number of Nodes")

        #create a grid of panels corresponding to each pi in Wee Archie.
        nodesGrid=wx.GridSizer(rows=4,cols=4)

        self.nodes=[]
        for i in range(16):
            self.nodes.append(wx.Panel(self.NodesPanel,style=wx.BORDER_SUNKEN))

        #place them in the sizer (filling up rows then columns)
        for row in range(4):
            for col in range(4):
                i=col*4+row
                nodesGrid.Add(self.nodes[i],1,wx.EXPAND)

        #slider to select the number of nodes
        self.NodesSlider=wx.Slider(self.NodesPanel,minValue=1,maxValue=16,value=1,name="nodes")
        self.SetNodes()

        #bind moving the sliders to the method SetNodes (which colours the node panels according to your selection)
        self.Bind(wx.EVT_SLIDER,self.SetNodes,self.NodesSlider)

        #add these to their sizer
        nodesSizer.Add(t2,0,wx.CENTRE,border=5)
        nodesSizer.Add(nodesGrid,1,wx.EXPAND|wx.ALL,border=10)
        nodesSizer.Add(self.NodesSlider,0,wx.EXPAND)

        #simulation start button

        self.GoButton=wx.Button(self,label="Start Simulation")
        self.Bind(wx.EVT_BUTTON,setupWindow.StartStopSim,self.GoButton)
        self.WinSizer.Add(self.GoButton,0,wx.EXPAND)


        #assign the main windows's sizer
        self.SetSizer(self.WinSizer)

        #fit all the graphical elements to the window then display the window


        #update the pie chart and the chip graphic (window must be drawn first to get everything positioned properly)

        self.Show()
        self.Layout()
        self.UpdateChip()


    def UpdateLocationText(self, locationText, weatherText):
        self.text_Location.SetLabel("Location: "+locationText)
        self.weather_Location.SetLabel("Weather: "+weatherText)
        time = int(strftime("%H")) - 3
        self.time_Location.SetLabel("Time: "+("0" if time < 10 else "") +str(time)+"00Z")

    #called when the number of cores is altered. This redraws the graphic
    def UpdateChip(self,e=None):
        #get the size of the part of the window that contains the graphic
        (w,h) = self.bitmap1.Size
        print("w,h=",w,h)
        if (w ==0 or h==0):
            w=300
            h=300
        #set the width ahd height of the image to be the same (i.e. square)
        if (w>h):
            w=h
        else:
            h=w

        #get the number of cores selected
        cores=self.coresRadio.GetSelection()

        #assign the correct image file to be loaded
        if cores == 0:
            file="chip1.png"
        elif cores == 1:
            file="chip2.png"
        elif cores == 2:
            file="chip3.png"
        else:
            file="chip4.png"

        #load and scale the image, assign it to the bitmap object
        bmp=wx.Image(file, wx.BITMAP_TYPE_ANY).Scale(w,h).ConvertToBitmap()
        self.bitmap1.SetBitmap(bmp)

        #force a redraw of the window to make sure the new image gets positioned correctly
        self.Layout()

    #colours node blocks when the node selecting slider is moved
    def SetNodes(self,e=None):
        #get the number of nodes selected
        a=self.NodesSlider.GetValue()

        #colour nodes appropriately
        for i in range(16):
            if i < a:
                self.nodes[i].SetBackgroundColour("Green")
            else:
                self.nodes[i].SetBackgroundColour(wx.NullColour)
        self.Refresh()

class TabLocation(wx.Panel):
    def __init__(self, parent, weatherConfigTab, parallelismConfigTab, setWidth, setHeight, setupWindow):
        wx.Panel.__init__(self, parent)

        self.weatherConfigTab = weatherConfigTab
        self.parallelismConfigTab=parallelismConfigTab
        self.parent=parent

        self.setupWindow=setupWindow

        maxWidth, maxHeight= wx.GetDisplaySize()
        print("maxwidth,maxheight=",maxWidth,maxHeight)
        W,H=parent.GetClientSize()
        print(W,H)

        heightCorrector=100
        maxHeight-=heightCorrector
        # Set up background image of the UK:
        self.MaxImageSize = 2400
        self.Image = wx.StaticBitmap(self, bitmap=wx.EmptyBitmap(self.MaxImageSize, self.MaxImageSize))
        Img = wx.Image(imageFile, wx.BITMAP_TYPE_JPEG)
        #Img = Img.Scale(maxHeight/1.4, maxHeight)
        Img = Img.Scale(setHeight/1.4*0.9,setHeight*0.9)
        # convert it to a wx.Bitmap, and put it on the wx.StaticBitmap
        self.Image.SetBitmap(wx.BitmapFromImage(Img))

        # Using a Sizer to handle the layout: I never like to use absolute postioning
        box = wx.BoxSizer(wx.VERTICAL)
        box.Add(self.Image, 0, wx.ALIGN_CENTER_HORIZONTAL | wx.ALL | wx.ADJUST_MINSIZE, 10)
        self.SetSizerAndFit(box)

        # Get the size of the image.....attempting to reposition the buttons depending on the window size.
        W, H = self.Image.GetSize()

        print maxWidth

        weatherBtnSizes=40

        # Set up image button for Edinburgh(city):
        bmp = wx.Bitmap(self.weather_data(edinburgh, 3166)[0], wx.BITMAP_TYPE_ANY)
        image = wx.ImageFromBitmap(bmp)
        image = image.Scale(weatherBtnSizes-10, weatherBtnSizes-10, wx.IMAGE_QUALITY_HIGH)
        bmp = wx.BitmapFromImage(image)
        self.button1 = wx.BitmapButton(self, -1, bmp, size = (weatherBtnSizes, weatherBtnSizes), pos=((W/1.96) + ((setWidth-W)/2), (H/3.4 + heightCorrector)))
        self.Bind(wx.EVT_BUTTON, self.go, self.button1)
        self.button1.Bind(wx.EVT_ENTER_WINDOW, self.changeCursor)
        self.button1.Bind(wx.EVT_ENTER_WINDOW, self.changeCursorBack)
        self.button1.SetDefault()

        # Set up image button for Highlands(mountains):
        bmp = wx.Bitmap(self.weather_data(highlands, 3047)[0], wx.BITMAP_TYPE_ANY)
        image = wx.ImageFromBitmap(bmp)
        image = image.Scale(weatherBtnSizes-10, weatherBtnSizes-10, wx.IMAGE_QUALITY_HIGH)
        bmp = wx.BitmapFromImage(image)
        self.button2 = wx.BitmapButton(self, -1, bmp, size=(weatherBtnSizes, weatherBtnSizes), pos=((W / 2.3) + ((setWidth-W)/2), (H / 6.7 + heightCorrector)))
        self.Bind(wx.EVT_BUTTON, self.go, self.button2)
        self.button2.Bind(wx.EVT_ENTER_WINDOW, self.changeCursor)
        self.button2.Bind(wx.EVT_ENTER_WINDOW, self.changeCursorBack)
        self.button2.SetDefault()

        # Set up image button for London(city+river):
        bmp = wx.Bitmap(self.weather_data(london, 3772)[0], wx.BITMAP_TYPE_ANY)
        image = wx.ImageFromBitmap(bmp)
        image = image.Scale(weatherBtnSizes-10, weatherBtnSizes-10, wx.IMAGE_QUALITY_HIGH)
        bmp = wx.BitmapFromImage(image)
        self.button3 = wx.BitmapButton(self, -1, bmp, size=(weatherBtnSizes, weatherBtnSizes), pos=((W / 1.4) + ((setWidth-W)/2), (H / 1.55 + heightCorrector)))
        self.Bind(wx.EVT_BUTTON, self.go, self.button3)
        self.button3.Bind(wx.EVT_ENTER_WINDOW, self.changeCursor)
        self.button3.Bind(wx.EVT_ENTER_WINDOW, self.changeCursorBack)
        self.button3.SetDefault()

        # Set up image button for Cornwall(seaside):
        bmp = wx.Bitmap(self.weather_data(cornwall, 3808)[0], wx.BITMAP_TYPE_ANY)
        image = wx.ImageFromBitmap(bmp)
        image = image.Scale(weatherBtnSizes-10, weatherBtnSizes-10, wx.IMAGE_QUALITY_HIGH)
        bmp = wx.BitmapFromImage(image)
        self.button4 = wx.BitmapButton(self, -1, bmp, size=(weatherBtnSizes, weatherBtnSizes), pos=((W / 2.52) + ((setWidth-W)/2), (H / 1.33 + heightCorrector)))
        self.Bind(wx.EVT_BUTTON, self.go, self.button4)
        self.button4.Bind(wx.EVT_ENTER_WINDOW, self.changeCursor)
        self.button4.Bind(wx.EVT_ENTER_WINDOW, self.changeCursorBack)
        self.button4.SetDefault()

    def go(self, event):
        if (event.GetEventObject() == self.button1):
            self.parallelismConfigTab.UpdateLocationText("Edinburgh", self.generateWeatherText(3166))
            self.setupWindow.weatherLocationCode=3166
        elif (event.GetEventObject() == self.button2):
            self.parallelismConfigTab.UpdateLocationText("Highlands", self.generateWeatherText(3047))
            self.setupWindow.weatherLocationCode=3047
        elif (event.GetEventObject() == self.button3):
            self.parallelismConfigTab.UpdateLocationText("London", self.generateWeatherText(3772))
            self.setupWindow.weatherLocationCode=3772
        elif (event.GetEventObject() == self.button4):
            self.parallelismConfigTab.UpdateLocationText("Cornwall", self.generateWeatherText(3808))
            self.setupWindow.weatherLocationCode=3808

        if (self.parent.GetPageCount() == 1):
            self.parent.AddPage(self.parallelismConfigTab, "Parallelism")
            self.parent.AddPage(self.weatherConfigTab, "Weather")
        self.parent.SetSelection(1)

    def generateWeatherText(self, numb):
        weatherInstance=LiveWeather(numb)
        weatherString=""
        live=weatherInstance.hour_weather()
        if live <= 1:
            weatherString+="Sunny"
        elif 9 > live > 1:
            weatherString+="Cloudy"
        else:
            weatherString+="Raining"
        weatherString+=" "+str(weatherInstance.wind_speed())+"m/s "+weatherInstance.wind_direction()+" "+str(weatherInstance.pressure())+"hpa "+str(weatherInstance.temperature())+"C "+str(weatherInstance.visibility())+"m"
        return weatherString


    def weather_data(self, place, numb):
        live = LiveWeather(numb).hour_weather()
        place = place
        if live <= 1:
            place.append(sun)
        elif 9 > live > 1:
            place.append(cloud)
        else:
            place.append(rain)
        return place

    # Change the cursor to a hand every time the cursor goes over a button
    def changeCursor(self, event):
        myCursor = wx.StockCursor(wx.CURSOR_HAND)
        self.button1.SetCursor(myCursor)
        self.button2.SetCursor(myCursor)
        self.button3.SetCursor(myCursor)
        self.button4.SetCursor(myCursor)
        event.Skip()

    # Change the cursor back to the arrow every time the cursor leaves a button
    def changeCursorBack(self, event):
        myCursor = wx.StockCursor(wx.CURSOR_ARROW)
        self.button1.SetCursor(myCursor)
        self.button2.SetCursor(myCursor)
        self.button3.SetCursor(myCursor)
        self.button4.SetCursor(myCursor)
        event.Skip()
