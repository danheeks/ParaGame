import cad
import math
import geom
from Object import Object
import os

points_dir = os.path.dirname(os.path.realpath(__file__))

type = 0
y_scale = 10.0
rear_render_x_offset = 0.2

class Points(Object):
    def __init__(self):
        Object.__init__(self, 0)
        
        self.points = []  # list of (front line length, rear line length)   
        self.box = None  # if box is None, then the curves need reloading
        
    def GetType(self):
        return type

    def TypeName(self):
        return "Points"
    
    def GetTypeString(self):
        return self.TypeName()
    
    def HasColor(self):
        return False
    
    def GetIconFilePath(self):
        return points_dir + '/points.png'
        
    def OnGlCommands(self, select, marked, no_color):
        i = 0
        global y_scale
        # draw front lines blue
        cad.BeginLines()
        cad.DrawColor(cad.Color(0,0,255))
        for point in self.points:
            cad.GlVertex(geom.Point3D(i, point[0] * y_scale, 0.0))
            i += 1
        cad.EndLinesOrTriangles()
        
        # draw rear lines red
        cad.BeginLines()
        cad.DrawColor(cad.Color(255,0,0))
        i = 0
        global rear_render_x_offset
        for point in self.points:
            cad.GlVertex(geom.Point3D(i + rear_render_x_offset, point[1] * y_scale, 0.0))
            i += 1
        cad.EndLinesOrTriangles()
        
    def GetGrippers(self, just_for_endof):
        i = 0
        global y_scale
        
        for point in self.points:
            cad.AddGripper(cad.GripData(geom.Point3D(i, point[0] * y_scale, 0.0), cad.GripperType.Stretch, 0))
            i += 1

        i = 0
        global rear_render_x_offset
        for point in self.points:
            cad.AddGripper(cad.GripData(geom.Point3D(i + rear_render_x_offset, point[1] * y_scale, 0.0), cad.GripperType.Stretch, 0))
            i += 1

    def Stretch(self):
        p = cad.GetStretchPoint()
        shift = cad.GetStretchShift()
        global y_scale
        global rear_render_x_offset
        i = 0
        for point in self.points:
            if p == geom.Point3D(i, point[0] * y_scale, 0.0):
                point[0] += (shift.y / y_scale)
                return
            if p == geom.Point3D( + rear_render_x_offset, point[1] * y_scale, 0.0):
                point[1] += (shift.y / y_scale)
                return
            i += 1
         
    def GetBox(self):
        box = geom.Box3D()
        box.InsertPoint(0,0,0)
        box.InsertPoint(240,100,0)
        return box
