import math
import pygame

import pymunk
import pymunk.pygame_util
from pymunk.vec2d import Vec2d

pygame.init()
screen = pygame.display.set_mode((1200, 600))
clock = pygame.time.Clock()
running = True
space = pymunk.Space()
pixel_scale = 20.0 # pixels per metre
space.gravity = (0.0, -9.8)
pymunk.pygame_util.positive_y_is_up = True
draw_options = pymunk.pygame_util.DrawOptions(screen)
font_height = 30
myfont = pygame.font.SysFont('Arial', font_height)

image_pixel_scale = 63.0 # there are about 63 pixels per metre in the pictures I have
image_scale = pixel_scale / image_pixel_scale

pilotImg = pygame.image.load('pilot.png')
wingImg = pygame.image.load('wing.png')

pilotImg = pygame.transform.scale(pilotImg, (int(pilotImg.get_width()*image_scale), int(pilotImg.get_height()*image_scale)))
wingImg = pygame.transform.scale(wingImg, (int(wingImg.get_width()*image_scale), int(wingImg.get_height()*image_scale)))

pilot_centre = Vec2d(49,64) * image_scale
thrust = False
wing_centre = Vec2d(93,56) * image_scale

w = screen.get_width()
h = screen.get_height()
draw_forces = True
force_draw_factor = 0.003
background_spacing = 10 # metres
camera = None
text_y = 0
winch_length = 10.0 # used if machine type is winch

machine_type = 'winch'
#machine_type = 'normal'

class Graph:
    def __init__(self, pts):
        # make sure pts is a list of (x,y) points always increasing in x
        self.pts = pts
        
    def get_y_at_x(self, x):
        y = None
        prev_p = None
        for pt in self.pts:
            y = pt[1]
            if x < pt[0]:
                if prev_p:
                    y = prev_p[1] + (x-prev_p[0])/(pt[0]-prev_p[0])*(pt[1]-prev_p[1])
                break
            prev_p = pt
        return y
    
class GameBody():
    def __init__(self, pos, v, mass, poly_pts):
        self.body = pymunk.Body()
        self.body.position = pos
        self.body.velocity = v
        self.shape = pymunk.Poly(self.body, poly_pts)
        self.shape.mass = mass
        self.shape.friction = 0.7
        space.add(self.body, self.shape)

    def draw_vector(self, pos, v, colour = (0,0,0)):
        wpos = self.body.local_to_world(Vec2d(pos[0], pos[1]))
        pygame.draw.line(screen, colour, world_to_screen(wpos), world_to_screen(wpos + v * force_draw_factor))

    def apply_parasitic_drag(self, coefficient):
        pass

class Wing(GameBody):
    def __init__(self):
        poly_pts = [(0.635, -2.667),(-0.048, -2.556),(-0.841, -1.619),(-1.317, 0.698),(-0.984, 0.841),(1.349, 0.254),(1.016, -1.381)]
        GameBody.__init__(self, (0,46),(-8,-0.8), 4, poly_pts)
        self.body.angle = 0.3
        self.airflow = Vec2d(0,0)
        self.wing_angle = Vec2d(0,0)
        self.lift = Vec2d(0,0)
        self.drag = Vec2d(0,0)
        self.pressure_pos = 0
        self.lift_coefficients = Graph([(-70, 0), (-30, -0.5), (-10, -0.5), (-8, -0.4), (-6, -0.2), (-4, 0), (-2, 0.2), (0, 0.42), (2, 0.66), (4, 0.82), (6, 1.1), (8, 1.2), (10, 1.4), (12, 1.45), (14, 1.52), (16, 1.5), (18, 1.45), (30, 1.4), (60, 0)])
        self.drag_coefficients = Graph([(-30,0.3),(-10, 0.1), (0, 0.07), (8, 0.1), (12, 0.14), (15, 0.25), (18, 0.45)])
        self.pressure_posns = Graph([(-10, 0), (0, 0.0)])
        self.angle_of_attack = None       
        self.angle_of_wing = None 
        self.brake = False
        self.let_up = False
        
    def get_lift_coefficient(self, angle):
        return self.lift_coefficients.get_y_at_x(angle)
        
    def get_drag_coefficient(self, angle):
        return self.drag_coefficients.get_y_at_x(angle)
        
    def get_pressure_pos(self, angle):
        return self.pressure_posns.get_y_at_x(angle)
        
    def draw_shape(self):
        s = None
        prev = None
        for v in self.shape.get_vertices():
            x,y = v.rotated(self.shape.body.angle) + self.shape.body.position
            if s == None:
                s = (x,y)
            else:
                p = (x,y)
                if prev != None:
                    draw_line(prev, p)
                prev = (x,y)
        if prev != None:
            draw_line(prev, s)
        
    def draw(self):
        draw_image(wingImg, wing_centre, self.body)
        
        #self.draw_shape()
        
        if draw_forces:
            # draw lift and drag
            self.draw_vector((self.pressure_pos, 0), self.lift, (0,0,255))
            self.draw_vector((self.pressure_pos, 0), self.drag, (255,0,0))
            self.draw_vector((0,0), Vec2d(1,0).rotated(self.angle_of_wing) * 500, (255,255,0))
            self.draw_vector((0,0), self.body.velocity * 300)
            self.draw_vector((0,0), self.body.velocity * (-300))
        
    def apply_force(self):
        self.angle_of_wing = self.body.angle - 3.1
        v, v_magn = self.body.velocity.normalized_and_length()
        
        angle_of_airflow = math.atan2(v.y, v.x)
        self.angle_of_attack = (angle_of_airflow - self.angle_of_wing) * 57
        if self.angle_of_attack > 180: self.angle_of_attack -= 360
        elif self.angle_of_attack < -180: self.angle_of_attack += 360
        
        # assuming lift is about 1000Nm ( 100kg ) at 10 m/s
        lift = 16.0 * v_magn * v_magn * self.get_lift_coefficient(self.angle_of_attack)
        drag = 16.0 * v_magn * v_magn * self.get_drag_coefficient(self.angle_of_attack)
        if lift < -2000:
            lift = -2000
        if lift > 2000:
            lift = 2000
        if drag > 2000:
            drag = 2000
            
        if self.brake:
            # increased lift and drag
            lift *= 1.5
            drag *= 1.6
            if rear_line != None:
                rear_line.max = 6.1
        elif self.let_up:
            # decreased lift and drag
            lift *= 0.6
            drag *= 0.8
            if rear_line != None:
                rear_line.max = 6.4
        else:
            if rear_line != None:
                rear_line.max = 6.2
            
            
        self.lift = -v.perpendicular() * lift
        self.drag = -v * drag
        
        self.pressure_pos = self.get_pressure_pos(self.angle_of_attack)
        
        world_pos = self.body.local_to_world((0,0))
        self.body.apply_force_at_world_point(self.lift + self.drag, world_pos)
        
class Centre(GameBody):
    def __init__(self):
        poly_pts = [(-0.3, -0.1), (-0.3, 0.1), (0.3, 0.1), (0.3, -0.1)]
        GameBody.__init__(self, (0,40), (-8,-0.9), 10, poly_pts)
        
    def draw(self):
        draw_image(pilotImg, pilot_centre, self.body)
        
    def apply_force(self):
        if thrust:
            # 20 kg to the left
            world_pos = self.body.local_to_world((0,0))
            self.body.apply_force_at_world_point(Vec2d(-20 * 9.8, 0), world_pos)
        self.apply_parasitic_drag(0.1)

class Pilot(GameBody):
    def __init__(self, starting_height):
        poly_pts = [(0.302, 0.619),(-0.556, -0.0317),(-0.603, -0.714),(0.063, -0.460),(0.429, 0.222)]
        GameBody.__init__(self, (0,starting_height), (-8,-0.9), 90, poly_pts)
        self.winch_up = False
        self.v_to_centre = None
        self.dline = 0.0
        
    def draw(self):
        draw_image(pilotImg, pilot_centre, self.body)
        if self.v_to_centre != None:
            self.draw_vector((-0.1, 0.2), self.v_to_centre * 100, (150,0,0))
        
    def apply_force(self):
        if thrust:
            # 20 kg to the left
            world_pos = self.body.local_to_world((0,0))
            self.body.apply_force_at_world_point(Vec2d(-20 * 9.8, 0), world_pos)

        # winch
        if drop_line != None:
            if self.winch_up:
                self.dline -= 0.001
                if self.dline < -0.2:
                    self.dline = -0.2
            else:
                self.dline += 0.001
                if self.dline > 0.2:
                    self.dline = 0.2
            drop_line.max += self.dline
            if drop_line.max < 0.5:
                drop_line.max = 0.5
                self.dline = 0
            if drop_line.max > winch_length:
                drop_line.max = winch_length
                self.dline = 0

            if rear_line != None:
                rear_line.max = 6.4 + self.dline * 2


#            self.v_to_centre = get_rope_vector(drop_line)
#            v, v_magn = self.v_to_centre.normalized_and_length()
#            world_pos = self.body.local_to_world((0,0))
#            self.body.apply_force_at_world_point(v  *force, world_pos)
#            world_pos = centre.body.local_to_world((0,0))
#            centre.body.apply_force_at_world_point(-v  *force, world_pos)
        
        self.apply_parasitic_drag(0.1)
            
    
def draw_line(s,e,col=(0,0,0)):
    pygame.draw.line(screen, col, world_to_screen(Vec2d(s[0], s[1])), world_to_screen(Vec2d(e[0], e[1])))
    
def draw_rect(minxy, maxxy, col=(0,0,0)):
    sminxy = world_to_screen(minxy)
    smaxxy = world_to_screen(maxxy)
    pygame.draw.rect(screen, col, pygame.Rect(sminxy.x, smaxxy.y, smaxxy.x - sminxy.x, sminxy.y - smaxxy.y))
    
def draw_text(s, col=(0,0,0)):
    global text_y
    screen.blit(myfont.render(s, False, col),(0,text_y))
    text_y += font_height * 1.2

def draw_background():
    # find min point
    minxy = Vec2d(0,h)
    maxxy = Vec2d(w,0)
    wmin = screen_to_world(minxy)
    wmax = screen_to_world(maxxy)
    space = background_spacing
    minx = int(wmin.x/space - 1) * space
    miny = int(wmin.y/space - 1) * space
    miny_above_ground = miny
    draw_ground = False
    if miny_above_ground < 0:
        miny_above_ground = 0
        draw_ground = True        
    maxx = int(wmax.x/space + 1) * space
    maxy = int(wmax.y/space + 1) * space
    
    x = minx
    while x < maxx:
        draw_line((x, miny_above_ground), (x, maxy), (128,128,128))
        x += space
    
    y = miny_above_ground
    while y < maxy:
        draw_line((minx, y), (maxx, y), (128,128,128))
        y += space
        
    if draw_ground:
        draw_rect(Vec2d(minx, miny), Vec2d(maxx, 0), (35,100,40))    

    if wing.angle_of_attack != None: draw_text('Angle of attack = ' + '%.1f' % wing.angle_of_attack + ' degrees')
    draw_text('Height = ' + '%.1f' %(pilot.body.position.y) + 'm')
    draw_text('Thrust = ' + ('ON' if thrust else 'off'))
    draw_text('Airspeed = ' + '%.1f' % abs(wing.body.velocity) + 'm/s')
    draw_text('Distance = ' + '%.1f' % math.fabs(pilot.body.position.x) + 'm')
    draw_text('Winch = ' + ('ON' if pilot.winch_up else 'off'))
    
        

def add_wall(space, start, end):
    seg = pymunk.Segment(space.static_body, start, end, 0.05)
    seg.friction = 1
    seg.elasticity = 1
    space.add(seg)
    
def y_flipped(pos):
    return Vec2d(pos.x, h-pos.y)
    
def camera_adjusted(pos):
    new_pos = (pos - camera) * pixel_scale + Vec2d(w * 0.5, h * 0.5)
    return new_pos

def world_to_screen(pos):
    return y_flipped(camera_adjusted(pos))
    
def screen_to_world(pos):
    new_pos = y_flipped(pos)
    return (new_pos - Vec2d(w * 0.5, h * 0.5))/pixel_scale + camera
    
def draw_image(img, centre, body):
    # centre is in pixels
    rect = img.get_rect()
    rect_center_to_img_center = Vec2d(centre.x - rect.centerx, rect.centery - centre.y)
    if body.angle > 1000:
        return
    if body.angle < -1000:
        return
    rot_img = pygame.transform.rotate(img, body.angle * 57)
    rect_center_to_img_center = rect_center_to_img_center.rotated(body.angle)
    rot_rect = rot_img.get_rect()
    v_centre = Vec2d(rot_rect.centerx, rot_rect.centery)
    rot_pos = rect_center_to_img_center + v_centre
    screen.blit(rot_img, world_to_screen(body.position) + Vec2d(-rot_pos.x, rot_pos.y - rot_rect.h))
    
def get_rope_vector(rope):
    return rope.a.local_to_world(rope.anchor_a) - rope.b.local_to_world(rope.anchor_b)

def draw_rope(rope):
    # draw a slide joint
    if rope == None:
        return
    
    draw_line(rope.a.local_to_world(rope.anchor_a), rope.b.local_to_world(rope.anchor_b), (128, 128, 160))
    
def update_camera_pos():
    global camera
    camera = pilot.body.position + (0,5)

# container
add_wall(space, (-2000, 0), (2000, 0))


wing = Wing()
drop_line = None
if machine_type == 'normal':
    pilot = Pilot(40)
    line_attacher = pilot
else:
    pilot = Pilot(40-winch_length)
    centre = Centre()
    line_attacher = centre
    drop_line = pymunk.SlideJoint(centre.body, pilot.body, (0, 0), (-0.1, 0.2), 0.05, winch_length)
    space.add(drop_line)
        
front_line = pymunk.SlideJoint(wing.body, line_attacher.body, (-1.3 , 0), (0.0, 0.2), 0.05, 6.3)
space.add(front_line)
rear_line = pymunk.SlideJoint(wing.body, line_attacher.body, (1.4, 0), (0.0, 0.2), 0.05, 6.2)
space.add(rear_line)


while True:
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            exit()
        elif event.type == pygame.KEYDOWN:
            if event.key == pygame.K_SPACE:
                running = not running
            if event.key == pygame.K_ESCAPE:
                exit()
            if event.key == pygame.K_a:
                space.remove(front_line)
                front_line = None
            if event.key == pygame.K_b:
                space.remove(rear_line)
                rear_line = None
            if event.key == pygame.K_c:
                thrust = not thrust
            if event.key == pygame.K_d:
                wing.brake = True
            if event.key == pygame.K_e:
                pilot.winch_up = True
            if event.key == pygame.K_f:
                wing.let_up = True
        elif event.type == pygame.KEYUP:
            if event.key == pygame.K_d:
                wing.brake = False
            if event.key == pygame.K_e:
                pilot.winch_up = False
            if event.key == pygame.K_f:
                wing.let_up = False

    screen.fill(pygame.Color(10,101,178))

    if running:
        wing.apply_force()
        pilot.apply_force()
        space.step(1.0 / 60)
        
    update_camera_pos()
    
    text_y = 0

    draw_background()
    pilot.draw()
    wing.draw()
    draw_rope(front_line)
    draw_rope(rear_line)
    draw_rope(drop_line)
    
    pygame.display.flip()

    clock.tick(60)
    pygame.display.set_caption(f"fps: {clock.get_fps()}")
    
