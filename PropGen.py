"""
Helix, propellor, thread design toolbox
Developed by Minh Quan NGUYEN
Mailto: nguyen.ensma@gmail.com

"""

import FreeCAD
import DraftTools
import Part
import Draft
from math import *
import os
from numpy import interp

def extendData(x,y):
  xnew=[-1]+x+[2]
  ynew=[(y[0]-y[1])/float(x[0]-x[1])*(-1-x[1])+y[1]]\
       +y\
       +[(y[-1]-y[-2])/float(x[-1]-x[-2])*(2-x[-2])+y[-2]]
  return xnew,ynew 

def F_linear():
  x=[0.0,1.0]
  y=[0.0,1.0]
  return x,y

def F_disruptive():
  x=[0.0,0.1,0.2,0.3,0.4,0.45,0.5,0.55,0.6,0.7,0.8,0.9,1.0]
  y=[]
  for e in x:
    y.append(0.5+1/pi*atan(33*(e-0.5)))
  return x,y

def F_bell():
  x=[0.0,0.1,0.2,0.3,0.4,0.5,0.6,0.7,0.8,0.9,1.0]
  y=[]
  for e in x:
    y.append(sin(pi*e))
  return x,y

class PropDesignPanel:
  def __init__(self):
    # this will create a Qt widget from our ui file
    self.form = FreeCADGui.PySideUic.loadUi(os.path.join(os.path.dirname(__file__),"PropGen.ui"))
    #connect radio button event to fucntion
    self.form.RB_linear.toggled.connect(self.setShape)
    self.form.RB_disruptive.toggled.connect(self.setShape)
    self.form.RB_bell.toggled.connect(self.setShape)
    self.form.RB_custom.toggled.connect(self.setShape)

  def setShape(self):
    x=[]
    y=[]
    if self.form.RB_linear.isChecked():
      x,y=F_linear()
    if self.form.RB_disruptive.isChecked():
      x,y=F_disruptive()
    if self.form.RB_bell.isChecked():
      x,y=F_bell()
    if self.form.RB_custom.isChecked():
      self.form.Data.setReadOnly(False)
    else:
      self.form.Data.setReadOnly(True)
      tmp="#t ; S(t)"
      for i in range(len(x)):
        tmp+="\n%.2f ; %.3f"%(x[i],y[i])
      self.form.Data.setPlainText(tmp)
    
  def accept(self):
    # propellor parameter
    BladeNb=int(self.form.bladeNb.value())
    n=1
    h=self.form.h.value()
    r0=self.form.r0.value()
    drmin=self.form.drmin.value()
    drmax=self.form.drmax.value()
    thetamin=self.form.thetamin.value()
    thetamax=self.form.thetamax.value()
    e=self.form.e.value()
    
    #Estimate N
    N=max(5,int((thetamax-thetamin)/360.*8))*int(self.form.precision.value()+1)
    
    #dump to YYYYMMDD-HHMMSS.propgen propeller profile
    
    
    propellerName="Propeller"

    #conversion deg to rad
    thetamin=thetamin*(3.1415/180)
    thetamax=thetamax*(3.1415/180)
    e=e*1e-3

    pointInt=[]
    pointExt=[]
    t=[]

    #build parameter t
    #t.append(-4*e/float(h))
    for i in range(N):
      t.append(i/float(N-1))
    #t.append((h+4*e)/float(h))
    
    tt1,ff1=F_linear()
    t1,f1=extendData(tt1,ff1)

    #read from text field
    tt2=[]
    ff2=[]
    for line in self.form.Data.toPlainText().split('\n'):
      if line[0]=='#':
        pass
      else:
        tmp=line.split(';')
        tt2.append(float(tmp[0]))
        ff2.append(float(tmp[1]))
    #tt2,ff2=F_linear()
    #tt2,ff2=F_bell()
    #tt2,ff2=F_disruptive()
    t2,f2=extendData(tt2,ff2)

    for i in range(len(t)):
      z=interp(t[i],t1,f1)*(h-0)+0
      theta=interp(t[i],t1,f1)*(thetamax-thetamin)+thetamin
      r=r0+interp(t[i],t2,f2)*(drmax-drmin)+drmin
      x1=max(0,r0-e)*cos(theta)
      y1=max(0,r0-e)*sin(theta)
      x2=r*cos(theta)
      y2=r*sin(theta)
      pointInt.append(FreeCAD.Vector(x1,y1,z))
      pointExt.append(FreeCAD.Vector(x2,y2,z))


    splineInt=Draft.makeBSpline(pointInt,closed=False,face=True,support=None)
    Draft.autogroup(splineInt)
    splineExt=Draft.makeBSpline(pointExt,closed=False,face=True,support=None)
    Draft.autogroup(splineExt)

    App.ActiveDocument.addObject('Part::RuledSurface', 'Surface')
    App.ActiveDocument.Surface.Curve1=(splineInt,['Edge1'])
    App.ActiveDocument.Surface.Curve2=(splineExt,['Edge1'])
    App.ActiveDocument.Surface.Orientation = u"Forward"
    App.ActiveDocument.recompute()

    #create first blade
    App.ActiveDocument.addObject("Part::Offset","Blade")
    App.ActiveDocument.Blade.Source = App.ActiveDocument.Surface
    App.ActiveDocument.Blade.Value = e
    App.ActiveDocument.Blade.Fill=True
    App.ActiveDocument.recompute()

    #create main shaft
    App.ActiveDocument.addObject('PartDesign::Body','Body')
    App.ActiveDocument.Body.newObject('Sketcher::SketchObject','Sketch')
    App.ActiveDocument.Sketch.Support = (App.ActiveDocument.XY_Plane, [''])
    App.ActiveDocument.Sketch.MapMode = 'FlatFace'
    App.ActiveDocument.Sketch.addGeometry(Part.Circle(App.Vector(0.000000,0.000000,0),App.Vector(0,0,1),r0),False)
    App.ActiveDocument.Body.newObject("PartDesign::Pad","Pad")
    App.ActiveDocument.Pad.Profile = App.ActiveDocument.Sketch
    App.ActiveDocument.Pad.Length = h

    #App.ActiveDocument.getObject('Sketch004')

    #create other blades
    for i in range(BladeNb-1):
      bladename="Blade"+str(i+2)
      App.ActiveDocument.addObject('PartDesign::FeatureBase',bladename)
      App.ActiveDocument.getObject(bladename).BaseFeature=App.ActiveDocument.Blade
      App.ActiveDocument.getObject(bladename).Placement=App.Placement(App.Vector(0,0,0), App.Rotation(360/float(BladeNb)*(i+1),0,0), App.Vector(0,0,0))

    #union main shaft and blade1                                                 
    App.ActiveDocument.addObject("Part::Fuse","Fusion1")
    App.ActiveDocument.Fusion1.Base=App.ActiveDocument.Blade
    App.ActiveDocument.Fusion1.Tool=App.ActiveDocument.Body

    currentname="Fusion1"
    #union with other blades
    for i in range(BladeNb-1):
      prename="Fusion"+str(i+1)
      currentname="Fusion"+str(i+2)
      bladename="Blade"+str(i+2)
      App.ActiveDocument.addObject("Part::Fuse",currentname)
      App.ActiveDocument.getObject(currentname).Base=App.ActiveDocument.getObject(prename)
      App.ActiveDocument.getObject(currentname).Tool=App.ActiveDocument.getObject(bladename)

    # trim out the lower and upper of propeller
    App.ActiveDocument.addObject("Part::Box","Box")
    App.ActiveDocument.Box.Length=4*(r0+drmax)
    App.ActiveDocument.Box.Width=4*(r0+drmax)
    App.ActiveDocument.Box.Height=h
    App.ActiveDocument.Box.Placement=App.Placement(App.Vector(-2*(r0+drmax),-2*(r0+drmax),-h), App.Rotation(0,0,0), App.Vector(0,0,0))

    App.ActiveDocument.addObject("Part::Box","Box2")
    App.ActiveDocument.Box2.Length=4*(r0+drmax)
    App.ActiveDocument.Box2.Width=4*(r0+drmax)
    App.ActiveDocument.Box2.Height=h
    App.ActiveDocument.Box2.Placement=App.Placement(App.Vector(-2*(r0+drmax),-2*(r0+drmax),h), App.Rotation(0,0,0), App.Vector(0,0,0))

    App.ActiveDocument.addObject("Part::Cut","Cut1")
    App.ActiveDocument.Cut1.Base = App.ActiveDocument.getObject(currentname)
    App.ActiveDocument.Cut1.Tool = App.ActiveDocument.Box

    App.ActiveDocument.addObject("Part::Cut",propellerName)
    App.ActiveDocument.getObject(propellerName).Base = App.ActiveDocument.Cut1
    App.ActiveDocument.getObject(propellerName).Tool = App.ActiveDocument.Box2

    # hide some parts
    Gui.ActiveDocument.hide(App.ActiveDocument.Surface.Name)
    Gui.ActiveDocument.hide(App.ActiveDocument.Pad.Name)
    Gui.ActiveDocument.hide(App.ActiveDocument.Sketch.Name)
    Gui.ActiveDocument.hide('BSpline')
    Gui.ActiveDocument.hide('BSpline001')
    App.ActiveDocument.recompute()

    FreeCADGui.Control.closeDialog()

if __name__=="__main__":
  panel = PropDesignPanel()
  FreeCADGui.Control.showDialog(panel)

#App.Console.PrintMessage(os.path.join(os.path.dirname(__file__),"dialog.ui"))
#from PySide import QtGui
#w = FreeCADGui.PySideUic.loadUi("dialog.ui")
#w.show()
#test