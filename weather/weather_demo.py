from __future__ import print_function
import client
import vtk
import random
import time
import math
import numpy

class vtkTimerCallback():
    def __init__(self, parent, win):
        self.timer_count = 0
        self.starttime=int(time.time())
        self.lasttime=self.starttime
        self.win=win
        self.parent=parent

    def execute(self,obj,event):
        if (not self.win.playing): return
        ctime=int(time.time())
        if (ctime > self.lasttime):
            elapsedTick=(self.lasttime+1)-self.starttime
            if (elapsedTick > 60):
                self.win.vtkwidget.RemoveObserver(self.win.timer_observer)
                self.win.vtkwidget.DestroyTimer(self.win.timer_id, None)
                self.win.StopSim()
                self.win.playing = False
                self.win.getdata.value = False
                self.win.showScoreBoard(self.parent.achievedtime, self.parent.accuracy_achieved / self.parent.accuracy_ticks)
            else:
                #if (elapsedTick == 25): self.win.mode=1
                #if (elapsedTick == 35): self.win.mode=2
                #if (elapsedTick == 45): self.win.mode=0
                updateStopWatchHand(self.win, (self.lasttime-self.starttime) + 1)
                self.lasttime+=1

#Data transfer object
class DTO(client.AbstractDTO):
    def SetData(self, data):
        self.Data=data

    def GetData(self):
        return self.Data

#class containing demo-specific functions
class WeatherDemo(client.AbstractDemo):
    def __init__(self):
        self.init_scene=False
        self.accuracy_achieved=0.0
        self.accuracy_ticks=0

    # read in data and convert it to a data transfer object
    def GetVTKData(self, root): # root=netcdf handle
        t1=time.time()
        q = root.variables['q']

        pres = root.variables['p'][:]
        p = numpy.array(pres)
        p = ((p + 1000)/1000) - 0.2


        theta = root.variables['th'][:]
        th = numpy.array(theta)
        th = th/4

        #th_ref = root.variables['th_ref'][:]

        rm = root.variables['ground_rain'][:]

        coords = root.variables['q'].shape[1:]

        vapor = (q[0] / 0.018) - 0.08  # return normalized vapor field data

        clouds = (q[1] - 0.00004)/ q[1].max()  # return normalized cloud data
        rain = (q[2]/q[2].max())

        timepersec = root.variables['time_per_sec'][0]
        modeltime = root.variables['model_time'][0]

        wind_u = root.variables['wind_u'][0]
        wind_v = root.variables['wind_v'][0]

        overalltime = root.variables['overall_time'][:]
        communicationtime =root.variables['communication_time'][:]

        x, y, z = coords

        avg_temp=numpy.sum(th[:,:,2])/(x*y)
        avg_pressure=numpy.sum(p[:,:,2])/(x*y)

        data = [vapor, clouds, rain, coords, rm, timepersec, overalltime, communicationtime, th, p, modeltime, wind_u, wind_v, avg_temp, avg_pressure]

        # create data transfer object and put the array into it
        dto = DTO()
        dto.SetData(data)

        print("Data successfully DTO'd")
        t2=time.time()
        print("DTO extraction took",t2-t1,"s")

        return dto

    def setSubmittedParameters(self, basehour, obs_wind_dir, obs_wind_strength, obs_pressure, obs_temp):
        self.basehour=basehour
        self.obs_wind_dir=obs_wind_dir
        self.obs_wind_strength=obs_wind_strength
        self.obs_pressure=obs_pressure
        self.obs_temp=obs_temp

    def updateCurrentAccuracyScore(self, avg_temp, avg_pressure):
        self.accuracy_achieved+=50
        self.accuracy_ticks+=1

    # Renders a frame with data contained within the data transfer object, data
    def RenderFrame(self, win, dto):
        t1=time.time()
        #unpack  data transfer object
        data = dto.GetData()
        vapor, clouds, rain, coords, rm, timepersec, overalltime, commtime, th, p, modeltime, wind_u, wind_v, avg_temp, avg_pressure = data

        win.renderer.SetBackground(0.22,.67,.87)
        win.renderer.SetViewport(0, 0.3, 1, 1)
        win.bottomrenderer.SetViewport(0,0,1,0.3)
        x, y, z = coords

        self.mode = win.mode

        self.achievedtime=modeltime*4

        self.updateCurrentAccuracyScore(avg_temp, avg_pressure)

        # The actors need to be created only once, that is why we have a actors dictionary in the win. This way we
        # will only add each actor once to the renderer. The other things like data structures, filters and mappers are
        # created and destroyed in each function.

        # To switch between the temperature, pressure and 'real' world views.
        if self.mode == 0:
            ### Clouds rendering
            # We create the actor if it does not exist, call the rendering function and give it the actor.
            # The function then gives new input for the actor, which we then add to the renderer.
            try:
                win.actors['CloudActor']
            except:
                win.actors['CloudActor'] = vtk.vtkVolume()
                #win.renderer.AddVolume(win.actors['CloudActor'])

            RenderCloud(clouds, coords, win.actors['CloudActor'])
            win.renderer.AddVolume(win.actors['CloudActor'])

            ### Rain
            try:
                win.actors['RainActor']
            except:
                win.actors['RainActor'] = vtk.vtkActor()

            RenderRain(rain, coords, win.actors['RainActor'])
            win.renderer.AddActor(win.actors['RainActor'])

            ### Remove actors
            try:
                win.renderer.RemoveActor(win.actors['TempActor'])
                win.renderer.RemoveActor(win.actors['PressActor'])
            except:
                pass
        elif self.mode == 1:
            ### Temperature
            try:
                win.actors['TempActor']
            except:
                win.actors['TempActor'] = vtk.vtkActor()

            RenderTemp(th, coords, win.actors['TempActor'])
            win.renderer.AddActor(win.actors['TempActor'])

            ### Remove actors
            try:
                win.renderer.RemoveActor(win.actors['RainActor'])
                win.renderer.RemoveActor(win.actors['CloudActor'])
                win.renderer.RemoveActor(win.actors['PressActor'])
            except:
                pass

        elif self.mode == 2:
            ### Pressure
            try:
                win.actors['PressActor']
            except:
                win.actors['PressActor'] = vtk.vtkActor()

            RenderPress(p, coords, win.actors['PressActor'])
            win.renderer.AddActor(win.actors['PressActor'])

            ### Remove actors
            try:
                win.renderer.RemoveActor(win.actors['RainActor'])
                win.renderer.RemoveActor(win.actors['CloudActor'])
                win.renderer.RemoveActor(win.actors['TempActor'])
            except:
                passvtkTimerCallback

        ### Sea
        # try:
        #     win.actors['SeaActor']
        # except:
        #     win.actors['SeaActor'] = vtk.vtkActor()
        #
        # if win.frameno.value ==0:
        #     RenderSea(win.waterlevel, coords, win.renderer, win.actors['SeaActor'])
        #
        # win.renderer.AddActor(win.actors['SeaActor'])

        ### Land
        if (not self.init_scene):
            #TODO landactor try
            RenderLand(coords, win.renderer)

        ### Decomposition grid redering, TODO
        if win.decompositiongrid is True:
            try:  # does the actor exist? if not, create one
                win.actors['DGridActor']
            except:
                win.actors['DGridActor'] = vtk.vtkPropCollection()

            win.actors['DGridActor'].RemoveAllItems()
            RenderDecompGrid(coords, win.actors['DGridActor'], win.columnsinX, win.columnsinY)
            #print("Adding actors")
            for i in range(win.actors['DGridActor'].GetNumberOfItems()):
                win.renderer.AddActor(win.actors['DGridActor'].GetItemAsObject(i))

        elif win.decompositiongrid is False:
            try:
                for i in range(win.actors['DGridActor'].GetNumberOfItems()):
                    win.renderer.RemoveActor(win.actors['DGridActor'].GetItemAsObject(i))
            except:
                pass

        # ### Crops
        # try:  # does the actor exist? if not, create one
        #     win.actors['CropsActor']
        # except:
        #     win.actors['CropsActor'] = vtk.vtkActor()
        #
        # win.rainmass += sum(sum(rm))
        # if win.rainmass < 1.5:
        #     win.cropslevel = int(win.rainmass * 3) + 2
        # else:
        #     if win.cropslevel > 4:
        #         win.cropslevel -= 1
        #     else:
        #         win.cropslevel = 4
        #
        # RenderCrops(win.cropslevel, coords, win.actors['CropsActor'])
        #
        # if win.rainmass > 1.5:
        #     win.actors['CropsActor'].GetProperty().SetColor(0, 0, 0)
        #
        # win.renderer.AddActor(win.actors['CropsActor'])

        ### Camera settings

        try:
            win.camera
        except:
            win.camera = win.renderer.GetActiveCamera()
            win.camera.SetFocalPoint(int(x/2),int(y/2),int(z/2))
            win.camera.Roll(80)
            win.camera.Dolly(0.35)
            win.camera.Elevation(70)
            win.camera.Roll(50)
            win.camera.Azimuth(180)
            win.camera.Elevation(-30)

        # Uncomment if you want to get a screenshot of every frame, see function description
        #Screenshot(win.vtkwidget.GetRenderWindow())

        #win.vtkwidget.GetRenderWindow.SetFullScreen(False)
        #win.vtkwidget.GetRenderWindow().FullScreenOn()

        ### Render the barplot
        try:
            win.views['BarPlot']
        except:
            win.views['BarPlot'] = vtk.vtkContextView()

        try:
            win.views['BarPlot'].GetScene().RemoveItem(0)
        except:
            pass

        ratio = commtime / overalltime
        chart = RenderPlot(ratio)

        win.views['BarPlot'].GetScene().AddItem(chart)
        win.views['BarPlot'].GetRenderer().SetViewport(0,0,1,0.3)

        win.vtkwidget.GetRenderWindow().AddRenderer(win.views['BarPlot'].GetRenderer())

        try:
            win.views['StatusLine']
        except:
            win.views['StatusLine'] = vtk.vtkContextView()

        win.views['StatusLine'].GetRenderer().SetBackground(0.22,.67,.87)
        win.views['StatusLine'].GetRenderer().SetViewport(0.85,0.3,1,1)

        win.vtkwidget.GetRenderWindow().AddRenderer(win.views['StatusLine'].GetRenderer())
        win.views['StatusLine'].GetRenderer().Render()

        generateStatusBar(self, win, win.views['StatusLine'].GetRenderer(), modeltime, wind_u, wind_v)

        if (not self.init_scene):
            timecallback=vtkTimerCallback(self, win)
            win.timer_observer=win.vtkwidget.AddObserver(vtk.vtkCommand.TimerEvent, timecallback.execute) # 'TimerEvent', timecallback.execute)
            win.timer_id=win.vtkwidget.CreateRepeatingTimer(1000)

        #print(str(win.views['StatusLine'].GetScene().GetSceneWidth()) + " "+str(win.views['StatusLine'].GetScene().GetSceneHeight()))

        win.vtkwidget.GetRenderWindow().Render()
        if (not self.init_scene): self.init_scene=True

        t2=time.time()
        print("Total frame rendering time=",t2-t1)

def updateStopWatchHand(win, seconds_remaining):
    win.views['StatusLine'].GetScene().RemoveItem(win.stopWatchHand)
    win.stopWatchHand=generateStopWatchHand(seconds_remaining)
    win.views['StatusLine'].GetScene().AddItem(win.stopWatchHand)
    win.vtkwidget.GetRenderWindow().Render()

def generateStatusBar(self, win, renderer, modeltime, wind_u, wind_v):
    if (not self.init_scene):
        imageReader = vtk.vtkPNGReader()
        imageReader.SetFileName("clockface.png")
        imageReader.Update()

        imageResizer=vtk.vtkImageResize()
        imageResizer.SetInputData(imageReader.GetOutput())
        imageResizer.SetResizeMethod(imageResizer.MAGNIFICATION_FACTORS)
        imageResizer.SetMagnificationFactors(0.3,0.3,0.3)
        imageResizer.Update()

        imgItem=vtk.vtkImageItem()
        imgItem.SetImage(imageResizer.GetOutput())
        imgItem.SetPosition(80, 580)
        win.views['StatusLine'].GetScene().AddItem(imgItem)

        imageReader2 = vtk.vtkPNGReader()
        imageReader2.SetFileName("stopwatch.png")
        imageReader2.Update()

        imageResizer2=vtk.vtkImageResize()
        imageResizer2.SetInputData(imageReader2.GetOutput())
        imageResizer2.SetResizeMethod(imageResizer2.MAGNIFICATION_FACTORS)
        imageResizer2.SetMagnificationFactors(0.4,0.4,0.4)
        imageResizer2.Update()

        imgItem2=vtk.vtkImageItem()
        imgItem2.SetImage(imageResizer2.GetOutput())
        imgItem2.SetPosition(80, 350)
        win.views['StatusLine'].GetScene().AddItem(imgItem2)
        win.stopWatchHand=generateStopWatchHand(60)
        win.views['StatusLine'].GetScene().AddItem(win.stopWatchHand)

        win.views['StatusLine'].GetScene().AddItem(generateCompassRose(115,210))
        win.views['StatusLine'].GetScene().AddItem(generateCompassRose(115,70))
        win.compass2_hand=generateWindDirectionHand(120,70, self.obs_wind_dir)
        win.compass2_strength=generateCompassStength(167, 120, self.obs_wind_strength)
        win.views['StatusLine'].GetScene().AddItem(win.compass2_hand)
        win.views['StatusLine'].GetScene().AddItem(win.compass2_strength)
    else:
        win.views['StatusLine'].GetScene().RemoveItem(win.timeOfDayHourHand)
        win.views['StatusLine'].GetScene().RemoveItem(win.timeOfDayMinuteHand)
        win.views['StatusLine'].GetScene().RemoveItem(win.compass1_hand)
        win.views['StatusLine'].GetScene().RemoveItem(win.compass1_strength)

    rebased_modeltime=modeltime*4
    currenthour_angle=((self.basehour - 12 if self.basehour > 12 else self.basehour) * 30) + ((rebased_modeltime/3600) *30)
    currentminute_angle=((rebased_modeltime%3600)/3600) * 360

    win.timeOfDayHourHand=generateTimeOfDayHand("hourhand.png", currenthour_angle, 106, 605)
    win.timeOfDayMinuteHand=generateTimeOfDayHand("minutehand.png", currentminute_angle, 90, 590)
    win.views['StatusLine'].GetScene().AddItem(win.timeOfDayMinuteHand)
    win.views['StatusLine'].GetScene().AddItem(win.timeOfDayHourHand)

    win_strength, win_direction=calcWindStrenghDirection(wind_u, wind_v)
    win.compass1_hand=generateWindDirectionHand(120, 210, win_direction)
    win.compass1_strength=generateCompassStength(167, 260, win_strength)
    win.views['StatusLine'].GetScene().AddItem(win.compass1_hand)
    win.views['StatusLine'].GetScene().AddItem(win.compass1_strength)

def calcWindStrenghDirection(wind_u, wind_v):
    angle=math.degrees(90)
    x_u=abs(wind_u) * math.cos(angle)
    y_u=abs(wind_u) * math.sin(angle)

    x_v=abs(wind_v) * math.cos(-angle)
    y_v=abs(wind_v) * math.sin(-angle)

    tot_x=x_u+x_v
    tot_y=y_u+y_v

    strength=math.sqrt(tot_x**2 + tot_y**2)
    direction_angle=90 - math.degrees(math.atan(tot_y/tot_x))

    if (wind_u < 0.0 and wind_v < 0.0):
        direction=180 + direction_angle
    elif (wind_u < 0.0):
        direction=180 - direction_angle
    elif (wind_v < 0.0):
        direction=360 - direction_angle
    else:
        direction=direction_angle

    return strength, direction

def generateCompassStength(xpos, ypos, strength):
    tooltip=vtk.vtkTooltipItem()
    tooltip.SetText("{:.1f}".format(strength))
    tooltip.SetPosition(xpos, ypos)
    tooltip.GetTextProperties().SetBackgroundOpacity(0.0)
    tooltip.GetPen().SetOpacityF(0.0)
    tooltip.GetBrush().SetOpacityF(0.0)
    return tooltip

def generateCompassRose(xpos, ypos):
    imageReader = vtk.vtkPNGReader()
    imageReader.SetFileName("wind_compass.png")
    imageReader.Update()

    imageResizer=vtk.vtkImageResize()
    imageResizer.SetInputData(imageReader.GetOutput())
    imageResizer.SetResizeMethod(imageResizer.MAGNIFICATION_FACTORS)
    imageResizer.SetMagnificationFactors(0.15,0.15,0.15)
    imageResizer.Update()

    imgItem=vtk.vtkImageItem()
    imgItem.SetImage(imageResizer.GetOutput())
    imgItem.SetPosition(xpos, ypos)
    return imgItem

def generateWindDirectionHand(xpos, ypos, wind_angle):
    imageReader = vtk.vtkPNGReader()
    imageReader.SetFileName("wind_compass_hand.png")
    imageReader.Update()

    imageResizer=vtk.vtkImageResize()
    imageResizer.SetInputData(imageReader.GetOutput())
    imageResizer.SetResizeMethod(imageResizer.MAGNIFICATION_FACTORS)
    imageResizer.SetMagnificationFactors(0.15,0.15,0.15)
    imageResizer.Update()

    bounds=[0.0]*6
    imageResizer.GetOutput().GetBounds(bounds)

    center=[0.0]*3
    center[0] = (bounds[1] + bounds[0]) / 2.0
    center[1] = (bounds[3] + bounds[2]) / 2.0
    center[2] = (bounds[5] + bounds[4]) / 2.0

    transformer=vtk.vtkTransform()
    transformer.Translate(center[0], center[1], center[2])
    transformer.RotateZ(wind_angle)
    transformer.Translate(-center[0], -center[1], -center[2])

    imageReslicer=vtk.vtkImageReslice()
    imageReslicer.SetInputData(imageResizer.GetOutput())
    imageReslicer.SetResliceTransform(transformer)
    imageReslicer.SetInterpolationModeToLinear()
    imageReslicer.Update()

    imgItem=vtk.vtkImageItem()
    imgItem.SetImage(imageReslicer.GetOutput())
    imgItem.SetPosition(xpos, ypos)
    return imgItem

def generateStopWatchHand(seconds_remaining):
    if (seconds_remaining == 60):
        angle=0.0
    else:
        angle=(60-seconds_remaining) * 6
    return generateClockHand("stopwatch_hand.png", angle, 117, 387, 0.15)

def generateTimeOfDayHand(filename, angle, xpos, ypos):
    return generateClockHand(filename, angle, xpos, ypos, 0.3)

def generateClockHand(filename, angle, xpos, ypos, mag):
    imageReader = vtk.vtkPNGReader()
    imageReader.SetFileName(filename)
    imageReader.Update()
    imageResizer=vtk.vtkImageResize()
    imageResizer.SetInputData(imageReader.GetOutput())
    imageResizer.SetResizeMethod(imageResizer.MAGNIFICATION_FACTORS)
    imageResizer.SetMagnificationFactors(mag,mag,mag)
    imageResizer.Update()

    bounds=[0.0]*6
    imageResizer.GetOutput().GetBounds(bounds)

    center=[0.0]*3
    center[0] = (bounds[1] + bounds[0]) / 2.0
    center[1] = (bounds[3] + bounds[2]) / 2.0
    center[2] = (bounds[5] + bounds[4]) / 2.0

    transformer=vtk.vtkTransform()
    transformer.Translate(center[0], center[1], center[2])
    transformer.RotateZ(angle)
    transformer.Translate(-center[0], -center[1], -center[2])

    imageReslicer=vtk.vtkImageReslice()
    imageReslicer.SetInputData(imageResizer.GetOutput())
    imageReslicer.SetResliceTransform(transformer)
    imageReslicer.SetInterpolationModeToLinear()
    imageReslicer.Update()

    imgItem=vtk.vtkImageItem()
    imgItem.SetImage(imageReslicer.GetOutput())
    imgItem.SetPosition(xpos, ypos)
    return imgItem


def Screenshot(rw):
    # Outputs a .png for every frame, input is a renderwindow
    # You can then combine the .pngs into a animated gif using the linux tool 'convert'
    w2if = vtk.vtkWindowToImageFilter()
    w2if.SetInput(rw)
    w2if.Update()

    writer = vtk.vtkPNGWriter()
    savename = str(time.time()) + '.png'
    writer.SetFileName(savename)
    writer.SetInputData(w2if.GetOutput())
    writer.Write()

def RenderPlot(ratio):
    chart = vtk.vtkChartXY()
    chart.SetShowLegend(True)

    table = vtk.vtkTable()

    arrX = vtk.vtkFloatArray()
    arrX.SetName('Core')

    arrC = vtk.vtkFloatArray()
    arrC.SetName('Computation')

    arrS = vtk.vtkFloatArray()
    arrS.SetName('Communication')

    table.AddColumn(arrX)
    table.AddColumn(arrC)
    table.AddColumn(arrS)

    numberofbars = len(ratio)

    table.SetNumberOfRows(numberofbars)

    for i in range(numberofbars):
        table.SetValue(i, 0, i)
        table.SetValue(i, 1, 1 - ratio[i])
        table.SetValue(i, 2, ratio[i])

    bar = chart.AddPlot(vtk.vtkChart.BAR)
    bar.SetInputData(table, 0, 1)
    bar.SetColor(0, 255, 0, 255)
    bar.SetWidth(1.5)

    bar = chart.AddPlot(vtk.vtkChart.BAR)
    bar.SetInputData(table, 0, 2)
    bar.SetColor(255, 0, 0, 255)
    bar.SetWidth(1.5)

    chart.GetAxis(vtk.vtkAxis.LEFT).SetRange(0., 1.0)
    chart.GetAxis(vtk.vtkAxis.LEFT).SetNotation(2)
    chart.GetAxis(vtk.vtkAxis.LEFT).SetPrecision(1)
    chart.GetAxis(vtk.vtkAxis.LEFT).SetBehavior(vtk.vtkAxis.FIXED)
    chart.GetAxis(vtk.vtkAxis.LEFT).SetTitle("% of overall time")
    chart.GetAxis(vtk.vtkAxis.BOTTOM).SetTitle("Core number")

    return chart


def RenderDecompGrid(coords, collection, px, py):
    x, y, z = coords

    localsizey = int(y/py)
    localsizex = int(x/px)
    overflowy = int(y-(localsizey*py))
    overflowx = x-(localsizex*px)
    localsizey+=1
    #localsizex+=1
    # the first few bigger chunks
    for i in range(1, int(overflowy)+1):
        localsizex += 1
        for j in range(1, int(overflowx) + 1):
            points = vtk.vtkPoints()
            ### for the outline, don't ask
            points.InsertNextPoint(0, 0, 0)
            points.InsertNextPoint(0, localsizey * i-1, 0)
            points.InsertNextPoint(int(localsizex * j)-1, localsizey * i-1, 0)
            points.InsertNextPoint(int(localsizex * j)-1, 0, 0)
            points.InsertNextPoint(0, 0, z)
            if i==1:
                print(overflowy, localsizey, localsizey*i)

            grid = vtk.vtkUnstructuredGrid()
            grid.SetPoints(points)

            sphere = vtk.vtkSphereSource()

            glyph3D = vtk.vtkGlyph3D()

            glyph3D.SetSourceConnection(sphere.GetOutputPort())
            glyph3D.SetInputData(grid)
            glyph3D.Update()

            filter = vtk.vtkOutlineFilter()

            filter.SetInputData(glyph3D.GetOutput())

            outlineMapper = vtk.vtkPolyDataMapper()
            outlineMapper.SetInputConnection(filter.GetOutputPort())

            outlineActor = vtk.vtkActor()
            outlineActor.SetMapper(outlineMapper)
            outlineActor.GetProperty().SetColor(1, 1, 1)

            collection.AddItem(outlineActor)
        localsizex -= 1
        for j in range(int(overflowx) + 1, px + 1):
            points = vtk.vtkPoints()
            ### for the outline, don't ask
            points.InsertNextPoint(0, 0, 0)
            points.InsertNextPoint(0, int(localsizey * i)-1, 0)
            points.InsertNextPoint(int(localsizex * j + overflowx)-1, int(localsizey * i)-1, 0)
            points.InsertNextPoint(int(localsizex * j + overflowx)-1, 0, 0)
            points.InsertNextPoint(0, 0, z)

            grid = vtk.vtkUnstructuredGrid()
            grid.SetPoints(points)
            sphere = vtk.vtkSphereSource()
            glyph3D = vtk.vtkGlyph3D()
            glyph3D.SetSourceConnection(sphere.GetOutputPort())
            glyph3D.SetInputData(grid)
            glyph3D.Update()

            filter = vtk.vtkOutlineFilter()
            filter.SetInputData(glyph3D.GetOutput())
            outlineMapper = vtk.vtkPolyDataMapper()
            outlineMapper.SetInputConnection(filter.GetOutputPort())

            outlineActor = vtk.vtkActor()
            outlineActor.SetMapper(outlineMapper)
            outlineActor.GetProperty().SetColor(1, 1, 1)

            collection.AddItem(outlineActor)
    # the next regular ones
    localsizey -=1

    for i in range(int(overflowy)+1, py+1):
        localsizex += 1
        for j in range(1, int(overflowx) + 1):
            points = vtk.vtkPoints()
            ### for the outline, don't ask
            print("Localsize and j, ", localsizex, j)
            points.InsertNextPoint(0, 0, 0)
            points.InsertNextPoint(0, int(localsizey * i)+overflowy-1, 0)
            points.InsertNextPoint(int(localsizex * j)-1, int(localsizey * i)+overflowy-1, 0)
            points.InsertNextPoint(int(localsizex * j)-1, 0, 0)
            points.InsertNextPoint(0, 0, z)

            grid = vtk.vtkUnstructuredGrid()
            grid.SetPoints(points)

            sphere = vtk.vtkSphereSource()

            glyph3D = vtk.vtkGlyph3D()

            glyph3D.SetSourceConnection(sphere.GetOutputPort())
            glyph3D.SetInputData(grid)
            glyph3D.Update()

            filter = vtk.vtkOutlineFilter()

            filter.SetInputData(glyph3D.GetOutput())

            outlineMapper = vtk.vtkPolyDataMapper()
            outlineMapper.SetInputConnection(filter.GetOutputPort())

            outlineActor = vtk.vtkActor()
            outlineActor.SetMapper(outlineMapper)
            outlineActor.GetProperty().SetColor(1, 1, 1)

            collection.AddItem(outlineActor)
        localsizex -= 1
        for j in range(int(overflowx) + 1, px + 1):
            points = vtk.vtkPoints()
            ### for the outline, don't ask
            points.InsertNextPoint(0, 0, 0)
            points.InsertNextPoint(0, int(localsizey * i)+overflowy-1, 0)
            points.InsertNextPoint(int(localsizex * j + overflowx)-1, int(localsizey * i)+overflowy-1, 0)
            points.InsertNextPoint(int(localsizex * j + overflowx)-1, 0, 0)
            points.InsertNextPoint(0, 0, z)

            grid = vtk.vtkUnstructuredGrid()
            grid.SetPoints(points)
            sphere = vtk.vtkSphereSource()
            glyph3D = vtk.vtkGlyph3D()
            glyph3D.SetSourceConnection(sphere.GetOutputPort())
            glyph3D.SetInputData(grid)
            glyph3D.Update()

            filter = vtk.vtkOutlineFilter()
            filter.SetInputData(glyph3D.GetOutput())
            outlineMapper = vtk.vtkPolyDataMapper()
            outlineMapper.SetInputConnection(filter.GetOutputPort())

            outlineActor = vtk.vtkActor()
            outlineActor.SetMapper(outlineMapper)
            outlineActor.GetProperty().SetColor(1, 1, 1)

            collection.AddItem(outlineActor)




def RenderOutline(coords, renderer):

    x,y,z = coords
    points = vtk.vtkPoints()

    cols = vtk.vtkFloatArray()
    cols.SetName("cols")

    colors = vtk.vtkLookupTable()
    colors.SetNumberOfTableValues(1)
    colors.SetTableValue(0, 1.0, 1.0, 1.0, 0.0)  # black

    ### for the outline, don't ask
    points.InsertNextPoint(0, 0, 0)
    points.InsertNextPoint(0, 0, x)
    points.InsertNextPoint(0, y, 0)
    points.InsertNextPoint(0, y, 9)
    points.InsertNextPoint(z, 0, 0)
    points.InsertNextPoint(z, 0, x)
    points.InsertNextPoint(z, y, 0)
    points.InsertNextPoint(z, y, x)

    cols.InsertNextValue(0)
    cols.InsertNextValue(0)
    cols.InsertNextValue(0)
    cols.InsertNextValue(0)
    cols.InsertNextValue(0)
    cols.InsertNextValue(0)
    cols.InsertNextValue(0)
    cols.InsertNextValue(0)

    grid = vtk.vtkUnstructuredGrid()
    grid.SetPoints(points)
    grid.GetPointData().AddArray(cols)

    sphere = vtk.vtkSphereSource()

    glyph3D = vtk.vtkGlyph3D()

    glyph3D.SetSourceConnection(sphere.GetOutputPort())
    glyph3D.SetInputData(grid)
    glyph3D.Update()

    outlinefilter =  vtk.vtkOutlineFilter()
        # win.filters['Outline'].SetInputData(outlineglyph3D.GetOutput())

    outlineMapper = vtk.vtkPolyDataMapper()
    outlineMapper.SetInputConnection(outlinefilter.GetOutputPort())
    outlineMapper.SetScalarModeToUsePointFieldData()
    outlineMapper.SetScalarRange(0, 3)
    outlineMapper.SelectColorArray("cols")
    # outlineMapper.SetLookupTable(outlinecolors)

    outlineActor = vtk.vtkActor()
    outlineActor.SetMapper(outlineMapper)
    outlineActor.GetProperty().SetColor(1, 1, 1)
    renderer.AddActor(outlineActor)

    return glyph3D, colors, cols

def RenderCloud(cloud, coords, cloudactor):

    x,y,z = coords

    t1=time.time()
    cloudarray=cloud
    mn=cloud.min()
    mx=cloud.max()

    #scale between 0 and 255
    cloudarray=(cloudarray)/(mx)*255

    #cast to uint


    data=cloudarray.astype(numpy.uint8)


    data=numpy.ascontiguousarray(data)


    #Apparently VTK is rubbish at hacving people manually making VTK data structures, so we write this array to a string, which is then read into a VTK reader... inefficient I know... :/
    dataImporter = vtk.vtkImageImport()

    #make string (want it in Fortran order (column major) else everything is transposed
    data_string = data.tostring(order="F")

    #read in string
    dataImporter.CopyImportVoidPointer(data_string, len(data_string))

    # The type of the newly imported data is set to unsigned char (uint8)
    dataImporter.SetDataScalarTypeToUnsignedChar()

    # Because the data that is imported only contains an intensity value (it isnt RGB-coded or someting similar), the importer must be told this is the case (only one data value by gridpoint)
    dataImporter.SetNumberOfScalarComponents(1)

    # The following two functions describe how the data is stored and the dimensions of the array it is stored in. For this
    # simple case, all axes are of length 75 and begins with the first element. For other data, this is probably not the case.
    # I have to admit however, that I honestly dont know the difference between SetDataExtent() and SetWholeExtent() although
    # VTK complains if not both are used.
    dataImporter.SetDataExtent(0,x-1, 0, y-1, 0, z-1) #fun fact, for data[x,y,z] this uses z,y,x
    dataImporter.SetWholeExtent(0,x-1, 0, y-1, 0, z-1)

    #create alpha and colour functions (map values 0-255 to colour and transparency)
    alpha=vtk.vtkPiecewiseFunction()
    colour=vtk.vtkColorTransferFunction()

    for i in range(256):
        #alpha.AddPoint(i,i/1024.)
        alpha.AddPoint(i,i/256.*0.2)

        r=0.5
        g=0.5
        b=0.5
        colour.AddRGBPoint(i,r,g,b)

    # The preavious two classes stored properties. Because we want to apply these properties to the volume we want to render,
    # we have to store them in a class that stores volume prpoperties.
    volumeProperty = vtk.vtkVolumeProperty()
    volumeProperty.SetColor(colour)
    volumeProperty.SetScalarOpacity(alpha)


    # This class describes how the volume is rendered (through ray tracing).
    #compositeFunction = vtk.vtkVolumeRayCastCompositeFunction()
    # We can finally create our volume. We also have to specify the data for it, as well as how the data will be rendered.
    volumeMapper = vtk.vtkFixedPointVolumeRayCastMapper()
    #volumeMapper.SetVolumeRayCastFunction(compositeFunction)
    volumeMapper.SetInputConnection(dataImporter.GetOutputPort())

    cloudactor.SetMapper(volumeMapper)
    cloudactor.SetProperty(volumeProperty)

    t2=time.time()

    print("Time to draw clouds = ",t2-t1)

    # points = vtk.vtkPoints()
    #
    # scales = vtk.vtkFloatArray()
    # scales.SetName("scales")
    #
    # col = vtk.vtkUnsignedCharArray()
    # col.SetName('Ccol')  # Any name will work here.
    # col.SetNumberOfComponents(3)
    #
    # nc = vtk.vtkNamedColors()
    #
    # tableSize = x * y * z
    # lut = vtk.vtkLookupTable()
    # lut.SetNumberOfTableValues(tableSize)
    # lut.Build()
    #
    # # Fill in a few known colors, the rest will be generated if needed
    # lut.SetTableValue(0, nc.GetColor4d("Black"))
    # lut.SetTableValue(1, nc.GetColor4d("Banana"))
    # lut.SetTableValue(2, nc.GetColor4d("Tomato"))
    # lut.SetTableValue(3, nc.GetColor4d("Wheat"))
    # lut.SetTableValue(4, nc.GetColor4d("Lavender"))
    # lut.SetTableValue(5, nc.GetColor4d("Flesh"))
    # lut.SetTableValue(6, nc.GetColor4d("Raspberry"))
    # lut.SetTableValue(7, nc.GetColor4d("Salmon"))
    # lut.SetTableValue(8, nc.GetColor4d("Mint"))
    # lut.SetTableValue(9, nc.GetColor4d("Peacock"))
    #
    #
    # for i in range(0,z,2):
    #     for j in range(0,y,2):
    #         for k in range(0,x,2):
    #             if cloud[k][j][i] > 0:
    #                 #print(i,j,k)
    #                 points.InsertNextPoint(k, j, i)
    #                 scales.InsertNextValue(1)  # random radius between 0 and 0.99
    #                 rgb = [0.0, 0.0, 0.0]
    #                 lut.GetColor(cloud[k][j][i], rgb)
    #                 ucrgb = list(map(int, [xx * 255 for xx in rgb]))
    #                 col.InsertNextTuple3(255,0,0)#ucrgb[0], ucrgb[1], ucrgb[2])
    #                 #print (" "+str(ucrgb)+" : "+str(rgb))
    #
    # #grid = vtk.vtkUnstructuredGrid()
    # #grid.SetPoints(points)
    # #grid.GetPointData().AddArray(scales)
    # #grid.GetPointData().SetActiveScalars("scales")
    # #sr = grid.GetScalarRange()# // !!!to set radius first
    # #grid.GetPointData().AddArray(col)
    #
    # #sphere = vtk.vtkSphereSource()
    #
    # #glyph3D = vtk.vtkGlyph3D()
    # #glyph3D.SetSourceConnection(sphere.GetOutputPort())
    # #glyph3D.SetInputData(grid)
    # #glyph3D.Update()
    #
    # polydata = vtk.vtkPolyData()
    #
    # polydata.SetPoints(points)
    # #polydata.GetPointData().SetScalars(col)
    # #polydata.GetPointData().SetScalars(col)
    #
    # splatter = vtk.vtkGaussianSplatter()
    #
    # splatter.SetInputData(polydata)
    # splatter.SetRadius(0.07)
    #
    # cf = vtk.vtkContourFilter()
    #
    # if points.GetNumberOfPoints() > 0:
    #     cf.SetInputConnection(splatter.GetOutputPort())
    # else: #weird things happen if you give him a splatter with no points
    #     cf.SetInputData(polydata)
    #
    # cf.SetValue(0, 0.01)
    # cf.GetOutput().GetPointData().SetScalars(col)
    #
    # reverse = vtk.vtkReverseSense()
    # reverse.SetInputConnection(cf.GetOutputPort())
    # reverse.ReverseCellsOn()
    # reverse.ReverseNormalsOn()
    #
    # cloudmapper = vtk.vtkPolyDataMapper()
    # cloudmapper.SetInputConnection(cf.GetOutputPort())
    # cloudmapper.SetScalarModeToUseCellFieldData()
    # #cloudmapper.SetScalarRange(sr)
    # cloudmapper.SelectColorArray("Ccol")  # // !!!to set color (nevertheless you will have nothing)
    # cloudmapper.SetLookupTable(lut)
    #
    # cloudactor.GetProperty().SetOpacity(1.0)
    # cloudactor.SetMapper(cloudmapper)


def RenderVapor(vapor, coords):
    print("Vapour?")
    x, y, z = coords
    points = vtk.vtkPoints()

    scales = vtk.vtkFloatArray()
    scales.SetName("Vscales")

    col = vtk.vtkUnsignedCharArray()
    col.SetName('Vcol')  # Any name will work here.
    col.SetNumberOfComponents(3)

    nc = vtk.vtkNamedColors()

    tableSize = x * y * z
    lut = vtk.vtkLookupTable()
    lut.SetNumberOfTableValues(tableSize)
    lut.Build()

    # Fill in a few known colors, the rest will be generated if needed
    lut.SetTableValue(0, nc.GetColor4d("Black"))
    lut.SetTableValue(1, nc.GetColor4d("Banana"))
    lut.SetTableValue(2, nc.GetColor4d("Tomato"))
    lut.SetTableValue(3, nc.GetColor4d("Wheat"))
    lut.SetTableValue(4, nc.GetColor4d("Lavender"))
    lut.SetTableValue(5, nc.GetColor4d("Flesh"))
    lut.SetTableValue(6, nc.GetColor4d("Raspberry"))
    lut.SetTableValue(7, nc.GetColor4d("Salmon"))
    lut.SetTableValue(8, nc.GetColor4d("Mint"))
    lut.SetTableValue(9, nc.GetColor4d("Peacock"))

    for k in range(x):
        for j in range(y):
            for i in range(z):
                if vapor[k][j][i] > 0.85:
                    points.InsertNextPoint(j, i, k)
                    scales.InsertNextValue(1)
                    rgb = [0.0, 0.0, 0.0]
                    lut.GetColor(vapor[k][j][i], rgb)
                    ucrgb = list(map(int, [x * 255 for x in rgb]))
                    col.InsertNextTuple3(ucrgb[0], ucrgb[1], ucrgb[2])

    grid = vtk.vtkUnstructuredGrid()
    grid.SetPoints(points)
    grid.GetPointData().AddArray(scales)
    grid.GetPointData().SetActiveScalars("Vscales")  # // !!!to set radius first
    grid.GetPointData().AddArray(col)

    sphere = vtk.vtkSphereSource()

    glyph3D = vtk.vtkGlyph3D()

    glyph3D.SetSourceConnection(sphere.GetOutputPort())
    glyph3D.SetInputData(grid)
    glyph3D.Update()

    # update mapper
    vapormapper = vtk.vtkPolyDataMapper()

    vapormapper.SetInputConnection(glyph3D.GetOutputPort())
    vapormapper.SetScalarModeToUsePointFieldData()
    vapormapper.SetScalarRange(0, 3)
    vapormapper.SelectColorArray("Vcol")  # // !!!to set color (nevertheless you will have nothing)
    vapormapper.SetLookupTable(lut)


def RenderRain(rain, coords, rainactor):

    x, y, z = coords
    points = vtk.vtkPoints()

    t1=time.time()

    scales = vtk.vtkFloatArray()
    scales.SetName("Rscales")

    col = vtk.vtkUnsignedCharArray()
    col.SetName('Rcol')  # Any name will work here.
    col.SetNumberOfComponents(3)

    nc = vtk.vtkNamedColors()

    tableSize = x * y * z
    lut = vtk.vtkLookupTable()
    lut.SetNumberOfTableValues(200)
    lut.SetHueRange(0.65, 0.53)
    #lut.SetAlphaRange(0.6,0.7)
    lut.Build()

    mx=rain.max()

    for k in range(0,x,1):
        for j in range(0,y,1):
            for i in range(0,z,1):
                if rain[k][j][i] > 0.001:
                    points.InsertNextPoint(k, j, i-0.25)
                    points.InsertNextPoint(k,j,i+0.25) #comment if doing glyphs
                    #scales.InsertNextValue(1)
                    #rgb = [0.0, 0.0, 0.0]
                    #lut.GetColor(rain[k][j][i], rgb)
                    #ucrgb = list(map(int, [x2 * 255 for x2 in rgb]))
                    #col.InsertNextTuple3(ucrgb[0], ucrgb[1], ucrgb[2])

#     grid = vtk.vtkUnstructuredGrid()
#     grid.SetPoints(points)
#     grid.GetPointData().AddArray(scales)
#     grid.GetPointData().SetActiveScalars("Rscales")  # // !!!to set radius first
#     grid.GetPointData().AddArray(col)
#
#     sphere = vtk.vtkSphereSource()
#     sphere.SetThetaResolution(3)
#     sphere.SetPhiResolution(3)
#
#     glyph3D = vtk.vtkGlyph3D()
#
#     glyph3D.SetSourceConnection(sphere.GetOutputPort())
#     glyph3D.SetInputData(grid)
#     glyph3D.Update()
#
# # update mapper
#     rainmapper = vtk.vtkPolyDataMapper()
#     rainmapper.SetInputConnection(glyph3D.GetOutputPort())
#     rainmapper.SetScalarRange(0, 3)
#
#     rainmapper.SetScalarModeToUsePointFieldData()
#     rainmapper.SelectColorArray("Rcol")  # // !!!to set color (nevertheless you will have nothing)
#     rainmapper.SetLookupTable(lut)
#
#     rainactor.GetProperty().SetOpacity(0.1)
#     rainactor.SetMapper(rainmapper)

    linesPolyData = vtk.vtkPolyData()
    linesPolyData.Allocate()

    for i in range(0, points.GetNumberOfPoints(),2 ):
        linesPolyData.InsertNextCell(vtk.VTK_LINE, 2, [i, i+1])

    # Add the points to the dataset
    linesPolyData.SetPoints(points)

    # update mapper
    rainmapper = vtk.vtkPolyDataMapper()
    rainmapper.SetInputData(linesPolyData)


    rainactor.GetProperty().SetOpacity(0.2)
    rainactor.GetProperty().SetLineWidth(5)
    rainactor.GetProperty().SetColor(0.1, 0.1, 0.8)
    rainactor.SetMapper(rainmapper)

    t2=time.time()

    print("Rain time=",t2-t1)

def RenderTemp(th, coords, rainactor):

    x, y, z = coords
    points = vtk.vtkPoints()

    scales = vtk.vtkFloatArray()
    scales.SetName("Tscales")

    col = vtk.vtkUnsignedCharArray()
    col.SetName('Tcol')  # Any name will work here.
    col.SetNumberOfComponents(3)

    nc = vtk.vtkNamedColors()

    tableSize = x * y * z
    lut = vtk.vtkLookupTable()
    lut.SetNumberOfTableValues(200)
    lut.SetHueRange(0.6, 0.0)
    #lut.SetAlphaRange(0.6,0.7)
    lut.Build()

    for k in range(x):
        for j in range(y):
            for i in range(z):
                if th[k][j][i] > 0.0000001:
                    points.InsertNextPoint(k, j, i)
                    scales.InsertNextValue(1.5)
                    rgb = [0.0, 0.0, 0.0]
                    lut.GetColor(th[k][j][i], rgb)
                    ucrgb = list(map(int, [x * 255 for x in rgb]))
                    col.InsertNextTuple3(ucrgb[0], ucrgb[1], ucrgb[2])

    grid = vtk.vtkUnstructuredGrid()
    grid.SetPoints(points)
    grid.GetPointData().AddArray(scales)
    grid.GetPointData().SetActiveScalars("Tscales")  # // !!!to set radius first
    grid.GetPointData().AddArray(col)

    sphere = vtk.vtkSphereSource()

    glyph3D = vtk.vtkGlyph3D()

    glyph3D.SetSourceConnection(sphere.GetOutputPort())
    glyph3D.SetInputData(grid)
    glyph3D.Update()

# update mapper
    rainmapper = vtk.vtkPolyDataMapper()
    rainmapper.SetInputConnection(glyph3D.GetOutputPort())
    rainmapper.SetScalarRange(0, 3)

    rainmapper.SetScalarModeToUsePointFieldData()
    rainmapper.SelectColorArray("Tcol")  # // !!!to set color (nevertheless you will have nothing)
    rainmapper.SetLookupTable(lut)

    rainactor.GetProperty().SetOpacity(0.1)
    rainactor.SetMapper(rainmapper)

def RenderPress(p, coords, pressactor):

    x, y, z = coords
    points = vtk.vtkPoints()

    scales = vtk.vtkFloatArray()
    scales.SetName("Pscales")

    col = vtk.vtkUnsignedCharArray()
    col.SetName('Pcol')  # Any name will work here.
    col.SetNumberOfComponents(3)

    nc = vtk.vtkNamedColors()

    tableSize = x * y * z
    lut = vtk.vtkLookupTable()
    lut.SetNumberOfTableValues(200)
    lut.SetHueRange(0.6, 0.0)
    #lut.SetAlphaRange(0.6,0.7)
    lut.Build()

    for k in range(x):
        for j in range(y):
            for i in range(z):
                if p[k][j][i] > 0.000000000001:
                    points.InsertNextPoint(k, j, i)
                    scales.InsertNextValue(1)
                    rgb = [0.0, 0.0, 0.0]
                    lut.GetColor(p[k][j][i], rgb)
                    ucrgb = list(map(int, [x * 255 for x in rgb]))
                    col.InsertNextTuple3(ucrgb[0], ucrgb[1], ucrgb[2])

    grid = vtk.vtkUnstructuredGrid()
    grid.SetPoints(points)
    grid.GetPointData().AddArray(scales)
    grid.GetPointData().SetActiveScalars("Pscales")  # // !!!to set radius first
    grid.GetPointData().AddArray(col)

    sphere = vtk.vtkSphereSource()

    glyph3D = vtk.vtkGlyph3D()

    glyph3D.SetSourceConnection(sphere.GetOutputPort())
    glyph3D.SetInputData(grid)
    glyph3D.Update()


    #for k in range(x):
    #    for j in range(y-int((y*0.4)), y+20):
    #        points.InsertNextPoint(k, j, 2)
#            points.InsertNextPoint(k, j, level)

    # Create a polydata to store everything in
    # linesPolyData = vtk.vtkPolyData()
    # linesPolyData.Allocate()
    #
    # for i in range(0, points.GetNumberOfPoints(),2 ):
    #     linesPolyData.InsertNextCell(vtk.VTK_LINE, 2, [i, i+1])
    #
    # # Add the points to the dataset
    # linesPolyData.SetPoints(points)
    #
    # # update mapper
    # rainmapper = vtk.vtkPolyDataMapper()
    # rainmapper.SetInputData(linesPolyData)
    #
    #
    # rainactor.GetProperty().SetOpacity(0.4)
    # rainactor.GetProperty().SetLineWidth(10)
    # rainactor.GetProperty().SetColor(0.1, 0.1, 0.8)
    # rainactor.SetMapper(rainmapper)


# update mapper
    rainmapper = vtk.vtkPolyDataMapper()
    rainmapper.SetInputConnection(glyph3D.GetOutputPort())
    rainmapper.SetScalarRange(0, 3)

    rainmapper.SetScalarModeToUsePointFieldData()
    rainmapper.SelectColorArray("Pcol")  # // !!!to set color (nevertheless you will have nothing)
    rainmapper.SetLookupTable(lut)

    pressactor.GetProperty().SetOpacity(0.1)
    pressactor.SetMapper(rainmapper)

def RenderSea(sealevel, coords, renderer, seaactor):

    x,y,z = coords

    points = vtk.vtkPoints()
    level = 0

    #sealevel = -5 #(-5 ,1)
    if sealevel == 1:
        level = -2
    elif sealevel == 3:
        level = 3

    for k in range(x):
        for j in range(-20, int((y*0.6))):
            for i in range(-5,level):
                points.InsertNextPoint(k, j, i)

    for k in range(x):
        for j in range(-20, int((y*0.6))):
            for i in range(level,level+1):
                if random.random()>0.85:
                    points.InsertNextPoint(k, j, i)

    #grid = vtk.vtkUnstructuredGrid()
    #grid.SetPoints(points)

    #sphere = vtk.vtkSphereSource()

    #glyph3D = vtk.vtkGlyph3D()

    #glyph3D.SetSourceConnection(sphere.GetOutputPort())
    #glyph3D.SetInputData(grid)
    #glyph3D.Update()

    polydata = vtk.vtkPolyData()

    polydata.SetPoints(points)

    splatter = vtk.vtkGaussianSplatter()

    splatter.SetInputData(polydata)
    splatter.SetRadius(0.08)

    cf = vtk.vtkContourFilter()
    cf.SetInputConnection(splatter.GetOutputPort())
    cf.SetValue(0, 0.1)

    reverse = vtk.vtkReverseSense()
    reverse.SetInputConnection(cf.GetOutputPort())
    reverse.ReverseCellsOn()
    reverse.ReverseNormalsOn()

    # update mapper
    seamapper = vtk.vtkPolyDataMapper()

    seamapper.SetInputConnection(reverse.GetOutputPort())
    seamapper.SetScalarModeToUsePointFieldData()
    seamapper.SetScalarRange(0, 3)

    seaactor.GetProperty().SetOpacity(1.)
    seaactor.GetProperty().SetColor(0., 0.412, 0.58)
    seaactor.SetMapper(seamapper)


def RenderLand(coords, renderer):

    # x,y,z = coords
    #
    # points = vtk.vtkPoints()
    #
    # for k in range(x):
    #     for j in range(y-int((y*0.4)), y+20):
    #         for i in range(-5,3):
    #             points.InsertNextPoint(k, j, i)
    #
    # for k in range(x):
    #     for j in range(y-int((y*0.4)), y+20):
    #         for i in range(3,4):
    #             if random.random()>0.9:
    #                 points.InsertNextPoint(k, j, i)
    #
    # #grid = vtk.vtkUnstructuredGrid()
    # #grid.SetPoints(points)
    #
    # #sphere = vtk.vtkSphereSource()
    #
    # #glyph3D = vtk.vtkGlyph3D()
    #
    # #glyph3D.SetSourceConnection(sphere.GetOutputPort())
    # #glyph3D.SetInputData(grid)
    # #glyph3D.Update()
    #
    # polydata = vtk.vtkPolyData()
    #
    # polydata.SetPoints(points)
    #
    # splatter = vtk.vtkGaussianSplatter()
    #
    # splatter.SetInputData(polydata)
    # splatter.SetRadius(0.06)
    #
    # cf = vtk.vtkContourFilter()
    # cf.SetInputConnection(splatter.GetOutputPort())
    # cf.SetValue(0, 0.05)
    #
    # reverse = vtk.vtkReverseSense()
    # reverse.SetInputConnection(cf.GetOutputPort())
    # reverse.ReverseCellsOn()
    # reverse.ReverseNormalsOn()
    #
    #
    # landmapper = vtk.vtkPolyDataMapper()
    #
    # landmapper.SetInputConnection(reverse.GetOutputPort())
    # landmapper.SetScalarModeToUsePointFieldData()
    # landmapper.SetScalarRange(0, 3)

    file1="Edinburgh2.obj"
    img1='Edinburgh.png'

    #read in 3d surface
    objreader1=vtk.vtkOBJReader()
    objreader1.SetFileName(file1)
    objreader1.Update()


    #read in image
    imgreader1=vtk.vtkPNGReader()
    imgreader1.SetFileName(img1)
    imgreader1.Update()

    #Convert the image to a texture
    texture1=vtk.vtkTexture()
    texture1.SetInputConnection(imgreader1.GetOutputPort())


    #get polydata output from OBJ reader
    polydata1=objreader1.GetOutput()


    #create mapper for the polydata
    mapper1=vtk.vtkPolyDataMapper()
    mapper1.SetInputData(polydata1)


    #create actor. attach mapper and texture
    landactor=vtk.vtkActor()
    landactor.SetMapper(mapper1)
    landactor.SetTexture(texture1)
    landactor.GetProperty().SetAmbient(1.0) #improve lighting
    landactor.RotateX(90) #flip round by 180 degrees (else it's upside down)
    landactor.RotateY(-90) #flip round by 180 degrees (else it's upside down)
    landactor.SetPosition(0,0,-2)

    #axes = vtk.vtkAxesActor()
    #renderer.AddActor(axes)
    renderer.AddActor(landactor)


def RenderCrops(level, coords, cropsactor):

    x, y, z = coords
    points = vtk.vtkPoints()


    for k in range(x):
        for j in range(y-int((y*0.4)), y+20):
            points.InsertNextPoint(k, j, 2)
            points.InsertNextPoint(k, j, level)

    # Create a polydata to store everything in
    linesPolyData = vtk.vtkPolyData()
    linesPolyData.Allocate()

    for i in range(0, points.GetNumberOfPoints(),2 ):
        linesPolyData.InsertNextCell(vtk.VTK_LINE, 2, [i, i+1])

    # Add the points to the dataset
    linesPolyData.SetPoints(points)

    # update mapper
    cropsmapper = vtk.vtkPolyDataMapper()
    cropsmapper.SetInputData(linesPolyData)


    cropsactor.GetProperty().SetOpacity(1.0)
    cropsactor.GetProperty().SetLineWidth(10)
    cropsactor.GetProperty().SetColor(0.39, 0.65, 0.04)
    cropsactor.SetMapper(cropsmapper)
