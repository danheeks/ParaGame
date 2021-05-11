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
            cad.GlVertex(geom.Point3D(i, point[1] * y_scale, 0.0))
            i += 1
        cad.EndLinesOrTriangles()
        
    def GetGrippers(self, just_for_endof):
        global y_scale
        global rear_render_x_offset
        i = 0
        for point in self.points:
            #cad.AddGripper(cad.GripData(geom.Point3D(i, point[0] * y_scale, 0.0), cad.GripperType.Stretch, 0))
            cad.AddGripper(cad.GripData(geom.Point3D(i, point[1] * y_scale, 0.0), cad.GripperType.Stretch, 0))
            i += 1

    def Stretch(self):
        global y_scale
        global rear_render_x_offset
        p = cad.GetStretchPoint()
        shift = cad.GetStretchShift()
        i = 0
        for point in self.points:
            if p == geom.Point3D(i, point[0] * y_scale, 0.0):
                point[0] += (shift.y / y_scale)
                return
            if p == geom.Point3D(i, point[1] * y_scale, 0.0):
                point[1] += (shift.y / y_scale)
                return
            i += 1
            
    def ModifyAtPoint(self, p, front):
        global y_scale
        global rear_render_x_offset
        index = 0 if front else 1
        extra_x = 0.0 if front else rear_render_x_offset
        i = int(p.x + 0.5 + extra_x)
        if i < 0 or i >= len(self.points):
            return
        self.points[i][index] = p.y / y_scale
        
         
    def GetBox(self):
        box = geom.Box3D()
        box.InsertPoint(0,0,0)
        box.InsertPoint(240,100,0)
        return box
